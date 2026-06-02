"""Build the errors[] section of the unified report from all sources."""

from __future__ import annotations

from pathlib import Path

from smartinstall.agent.collectors.event_log_collector import EventLogCollectionResult
from smartinstall.agent.collectors.installer_log_collector import InstallerLogCollectionResult
from smartinstall.agent.collectors.msi_log_collector import MsiLogCollectionResult
from smartinstall.agent.collectors.process_collector import ProcessCollectionResult
from smartinstall.agent.collectors.wer_collector import WerCollectionResult
from smartinstall.agent.detection.failure_detector import FailureDetectionOutcome
from smartinstall.agent.detection.stream_log_analyzer import analyze_stream_logs
from smartinstall.agent.runners.installer_runner import InstallerRunResult
from smartinstall.core.enums.installation import InstallerType
from smartinstall.core.models.evidence import ErrorDetails
from smartinstall.core.models.unified_report import ReportErrorEntry


def build_error_entries(
    *,
    detection: FailureDetectionOutcome,
    run_result: InstallerRunResult,
    event_logs: EventLogCollectionResult,
    msi_logs: MsiLogCollectionResult,
    wer: WerCollectionResult,
    installer_logs: InstallerLogCollectionResult,
    process: ProcessCollectionResult,
    collection_errors: list[str],
    installer_type: InstallerType,
    failure_timestamp: str,
    is_gui_installer: bool,
) -> list[ReportErrorEntry]:
    errors: list[ReportErrorEntry] = []

    if detection.error_details is not None:
        errors.append(_from_error_details(detection.error_details))

    if detection.failure_reason and detection.error_details is None:
        errors.append(
            ReportErrorEntry(
                category="installation",
                code="INSTALLATION_FAILURE",
                message=detection.failure_reason,
                source="FailureDetector",
                timestamp=failure_timestamp,
                severity="error",
            )
        )

    errors.extend(
        analyze_stream_logs(
            run_result.stdout_path,
            run_result.stderr_path,
            failure_timestamp=failure_timestamp,
        )
    )

    for entry in event_logs.entries:
        if entry.level not in {"Error", "Critical", "Warning"}:
            continue
        errors.append(
            ReportErrorEntry(
                category="event_log",
                code=f"EVENT_{entry.event_id}",
                message=entry.message or f"Event ID {entry.event_id} from {entry.source}",
                source=f"EventLog/{entry.log_name}",
                timestamp=entry.timestamp,
                severity="error" if entry.level in {"Error", "Critical"} else "warning",
            )
        )

    for diagnostic in msi_logs.diagnostics:
        if diagnostic.is_fatal or (not diagnostic.is_warning):
            errors.append(
                ReportErrorEntry(
                    category="msi",
                    code=diagnostic.error_code or "MSI_LOG_ERROR",
                    message=diagnostic.raw_text[:2000],
                    source="MSI_VERBOSE_LOG",
                    timestamp=failure_timestamp,
                    severity="error" if diagnostic.is_fatal else "warning",
                    rawExcerpt=diagnostic.raw_text[:4096],
                )
            )

    for crash in wer.reports:
        errors.append(
            ReportErrorEntry(
                category="crash",
                code=crash.exception_code or "PROCESS_CRASH",
                message=crash.friendly_event_name
                or f"Crash in {crash.faulting_application or 'unknown'}",
                source="WER",
                timestamp=crash.crash_timestamp or failure_timestamp,
                severity="error",
            )
        )

    errors.extend(installer_logs.extracted_errors)

    for log_file in installer_logs.discovered_logs:
        if log_file.extracted_error_count == 0 and log_file.preview_lines:
            preview = " ".join(log_file.preview_lines)[:500]
            if any(k in preview.lower() for k in ("error", "fail", "network")):
                errors.append(
                    ReportErrorEntry(
                        category="installer_log",
                        code="INSTALLER_LOG_HINT",
                        message=preview[:2000],
                        source=log_file.file_path,
                        timestamp=log_file.modified_timestamp,
                        severity="warning",
                    )
                )

    for child in process.child_processes:
        if child.exit_code is not None and child.exit_code != 0:
            errors.append(
                ReportErrorEntry(
                    category="installation",
                    code=f"CHILD_EXIT_{child.exit_code}",
                    message=(
                        f"Child process {child.process_name} (pid={child.process_id}) "
                        f"exited with code {child.exit_code}"
                    ),
                    source=child.executable_path or child.process_name,
                    timestamp=failure_timestamp,
                    severity="error",
                )
            )

    for message in collection_errors:
        if installer_type != InstallerType.MSI and "MSI verbose log not found" in message:
            continue
        errors.append(
            ReportErrorEntry(
                category="collection",
                code="COLLECTOR_ERROR",
                message=message,
                source="LogCollector",
                timestamp=failure_timestamp,
                severity="warning",
            )
        )

    if (
        is_gui_installer
        and run_result.exit_code == 0
        and not _has_category(errors, "network", "installation", "installer_log", "event_log")
        and _streams_empty(run_result)
        and not event_logs.entries
        and not installer_logs.discovered_logs
    ):
        errors.append(
            ReportErrorEntry(
                category="gui",
                code="GUI_INSTALL_INCOMPLETE",
                message=(
                    "GUI installer process ended with exit code 0 but no console errors were captured. "
                    "Installation is likely incomplete — common causes: network disabled during download, "
                    "user cancelled the wizard, or required components were not installed. "
                    "Check the installer window messages and logs in the artifact directory."
                ),
                source="FailureDetector",
                timestamp=failure_timestamp,
                severity="error",
            )
        )

    return _deduplicate(errors)


def _from_error_details(details: ErrorDetails) -> ReportErrorEntry:
    category = "installation"
    if details.error_source.startswith("EventLog"):
        category = "event_log"
    elif details.error_source == "WER":
        category = "crash"
    elif details.error_source == "MSI_VERBOSE_LOG":
        category = "msi"
    elif "network" in details.primary_error_message.lower():
        category = "network"

    return ReportErrorEntry(
        category=category,
        code=details.error_code or "INSTALLATION_ERROR",
        message=details.primary_error_message,
        source=details.error_source,
        timestamp=details.failure_timestamp,
        severity="error",
    )


def _streams_empty(run_result: InstallerRunResult) -> bool:
    for path in (run_result.stdout_path, run_result.stderr_path):
        if path is not None and path.is_file() and path.read_text(encoding="utf-8", errors="replace").strip():
            return False
    return True


def _has_category(errors: list[ReportErrorEntry], *categories: str) -> bool:
    return any(entry.category in categories for entry in errors)


def _deduplicate(errors: list[ReportErrorEntry]) -> list[ReportErrorEntry]:
    seen: set[tuple[str, str, str]] = set()
    unique: list[ReportErrorEntry] = []
    for entry in errors:
        key = (entry.category, entry.code, entry.message[:200])
        if key in seen:
            continue
        seen.add(key)
        unique.append(entry)
    return unique
