"""Aggregates failure signals into a single detection outcome."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from smartinstall.agent.collectors.event_log_collector import EventLogCollectionResult
from smartinstall.agent.collectors.installer_log_collector import InstallerLogCollectionResult
from smartinstall.agent.collectors.msi_log_collector import MsiLogCollectionResult
from smartinstall.agent.collectors.process_collector import ProcessCollectionResult
from smartinstall.agent.collectors.wer_collector import WerCollectionResult
from smartinstall.agent.runners.exit_codes import describe_exit_code
from smartinstall.agent.runners.installer_runner import InstallerRunResult
from smartinstall.core.enums.installation import InstallerType
from smartinstall.core.models.evidence import ErrorDetails


@dataclass(frozen=True, slots=True)
class FailureDetectionOutcome:
    status: str  # SUCCESS | FAILED | CRASHED | TIMED_OUT | PARTIAL
    failure_reason: str | None
    error_details: ErrorDetails | None
    detection_signals: list[str]


class FailureDetector:
    """Combines exit codes, MSI, events, WER, and stderr signals."""

    def analyze(
        self,
        *,
        run_result: InstallerRunResult,
        event_logs: EventLogCollectionResult,
        msi_logs: MsiLogCollectionResult,
        wer: WerCollectionResult,
        process: ProcessCollectionResult,
        installer_logs: InstallerLogCollectionResult | None = None,
        application_name: str,
        installer_type: InstallerType = InstallerType.EXE,
    ) -> FailureDetectionOutcome:
        _ = application_name
        signals: list[str] = []
        failure_timestamp = run_result.end_timestamp or datetime.now(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%S.%f"
        )[:-3] + "Z"

        if run_result.timed_out:
            signals.append("INSTALLER_TIMEOUT")
            return FailureDetectionOutcome(
                status="TIMED_OUT",
                failure_reason="Installer exceeded configured timeout",
                error_details=ErrorDetails(
                    primaryErrorMessage="Installation timed out",
                    errorCode="TIMEOUT",
                    errorSource="InstallerRunner",
                    failureTimestamp=failure_timestamp,
                    detectionSignals=signals,
                ),
                detection_signals=signals,
            )

        if wer.crash_detected:
            signals.append("WER_CRASH_REPORT")
            primary = "Installer or child process crash detected (WER)"
            if wer.reports:
                first = wer.reports[0]
                if first.faulting_application:
                    primary = f"Crash: {first.faulting_application}"
                if first.exception_code:
                    primary += f" ({first.exception_code})"
            return FailureDetectionOutcome(
                status="CRASHED",
                failure_reason=primary,
                error_details=ErrorDetails(
                    primaryErrorMessage=primary,
                    errorCode=wer.reports[0].exception_code if wer.reports else "CRASH",
                    errorSource="WER",
                    failureTimestamp=wer.reports[0].crash_timestamp or failure_timestamp,
                    detectionSignals=signals,
                ),
                detection_signals=signals,
            )

        exit_code = run_result.exit_code
        if exit_code is not None and exit_code != 0:
            description, known = describe_exit_code(exit_code)
            signals.append("NON_ZERO_EXIT_CODE")
            return FailureDetectionOutcome(
                status="FAILED",
                failure_reason=f"Exit code {exit_code}: {description}",
                error_details=ErrorDetails(
                    primaryErrorMessage=description,
                    errorCode=str(exit_code),
                    errorSource="InstallerProcess",
                    failureTimestamp=failure_timestamp,
                    detectionSignals=signals,
                ),
                detection_signals=signals,
            )

        if msi_logs.fatal_detected:
            signals.append("MSI_FATAL_ERROR")
            fatal = next((d for d in msi_logs.diagnostics if d.is_fatal), None)
            msg = fatal.raw_text if fatal else "MSI fatal error (Return value 3)"
            return FailureDetectionOutcome(
                status="FAILED",
                failure_reason="MSI fatal installation error",
                error_details=ErrorDetails(
                    primaryErrorMessage=msg[:2000],
                    errorCode=fatal.error_code if fatal else "1603",
                    errorSource="MSI_VERBOSE_LOG",
                    failureTimestamp=failure_timestamp,
                    detectionSignals=signals,
                ),
                detection_signals=signals,
            )

        high_severity = [
            e for e in event_logs.entries if e.level in {"Error", "Critical"}
        ]
        if high_severity:
            signals.append("EVENT_LOG_ERROR")
            top = high_severity[-1]
            return FailureDetectionOutcome(
                status="FAILED",
                failure_reason=f"Event {top.event_id} ({top.source}): {top.message[:200]}",
                error_details=ErrorDetails(
                    primaryErrorMessage=top.message[:2000] or f"Event ID {top.event_id}",
                    errorCode=str(top.event_id),
                    errorSource=f"EventLog/{top.log_name}",
                    failureTimestamp=top.timestamp,
                    detectionSignals=signals,
                ),
                detection_signals=signals,
            )

        if installer_logs is not None:
            log_errors = [
                e for e in installer_logs.extracted_errors if e.severity == "error"
            ]
            if log_errors:
                signals.append("INSTALLER_LOG_ERROR")
                top = log_errors[0]
                return FailureDetectionOutcome(
                    status="FAILED",
                    failure_reason=top.message[:200],
                    error_details=ErrorDetails(
                        primaryErrorMessage=top.message[:2000],
                        errorCode=top.code,
                        errorSource=top.source or "InstallerLog",
                        failureTimestamp=top.timestamp,
                        detectionSignals=signals,
                    ),
                    detection_signals=signals,
                )

        failed_children = [
            c
            for c in process.child_processes
            if c.exit_code is not None and c.exit_code != 0
        ]
        if failed_children:
            child = failed_children[0]
            signals.append("CHILD_PROCESS_NON_ZERO_EXIT")
            msg = (
                f"Child process {child.process_name} exited with code {child.exit_code}"
            )
            return FailureDetectionOutcome(
                status="FAILED",
                failure_reason=msg,
                error_details=ErrorDetails(
                    primaryErrorMessage=msg,
                    errorCode=f"CHILD_EXIT_{child.exit_code}",
                    errorSource=child.executable_path or child.process_name,
                    failureTimestamp=failure_timestamp,
                    detectionSignals=signals,
                ),
                detection_signals=signals,
            )

        if run_result.stderr_high_priority_count > 0:
            signals.append("STDERR_HIGH_PRIORITY")
            return FailureDetectionOutcome(
                status="FAILED",
                failure_reason="Installer stderr contained error/failure keywords",
                error_details=ErrorDetails(
                    primaryErrorMessage="See stderr.log in session directory",
                    errorCode="STDERR_ERROR",
                    errorSource="InstallerStderr",
                    failureTimestamp=failure_timestamp,
                    detectionSignals=signals,
                ),
                detection_signals=signals,
            )

        msi_errors = [d for d in msi_logs.diagnostics if d.is_fatal or (not d.is_warning)]
        if msi_errors and not msi_logs.fatal_detected:
            signals.append("MSI_ERROR_LINES")
            top = msi_errors[0]
            return FailureDetectionOutcome(
                status="FAILED",
                failure_reason="MSI log contains error entries",
                error_details=ErrorDetails(
                    primaryErrorMessage=top.raw_text[:2000],
                    errorCode=top.error_code,
                    errorSource="MSI_VERBOSE_LOG",
                    failureTimestamp=failure_timestamp,
                    detectionSignals=signals,
                ),
                detection_signals=signals,
            )

        collector_issues = list(event_logs.errors) + list(wer.errors) + list(process.errors)
        if installer_type == InstallerType.MSI:
            collector_issues.extend(msi_logs.errors)
        partial = bool(collector_issues)
        if partial:
            signals.append("PARTIAL_EVIDENCE")
            return FailureDetectionOutcome(
                status="PARTIAL",
                failure_reason=None,
                error_details=None,
                detection_signals=signals,
            )

        return FailureDetectionOutcome(
            status="SUCCESS",
            failure_reason=None,
            error_details=None,
            detection_signals=signals,
        )
