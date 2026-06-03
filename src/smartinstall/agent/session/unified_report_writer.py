"""Writes the single canonical smartinstall_report.json artifact."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from smartinstall.core.models.installation_session import InstallationSession
from smartinstall.core.models.unified_report import (
    UNIFIED_REPORT_FILENAME,
    EvidenceSection,
    InstallationStatusSection,
    UnifiedInstallationReport,
)
from smartinstall.core.models.evidence import InstallerDetails
from smartinstall.core.models.unified_report import ReportErrorEntry
from smartinstall.agent.collectors.event_log_collector import EventLogCollectionResult
from smartinstall.agent.collectors.filesystem_collector import FilesystemCollectionResult
from smartinstall.agent.collectors.installer_log_collector import InstallerLogCollectionResult
from smartinstall.agent.collectors.registry_collector import RegistryCollectionResult
from smartinstall.agent.collectors.msi_log_collector import MsiLogCollectionResult
from smartinstall.agent.collectors.process_collector import ProcessCollectionResult
from smartinstall.agent.collectors.wer_collector import WerCollectionResult
from smartinstall.agent.detection.failure_detector import FailureDetectionOutcome


class UnifiedReportWriter:
    @staticmethod
    def build(
        *,
        session: InstallationSession,
        application: str,
        detection: FailureDetectionOutcome,
        installer_details: InstallerDetails,
        errors: list[ReportErrorEntry],
        event_logs: EventLogCollectionResult,
        msi_logs: MsiLogCollectionResult,
        wer: WerCollectionResult,
        process: ProcessCollectionResult,
        installer_logs: InstallerLogCollectionResult,
        registry: RegistryCollectionResult,
        filesystem: FilesystemCollectionResult,
    ) -> UnifiedInstallationReport:
        outcome = _map_detection_to_outcome(detection.status)
        installation_completed = outcome in {"Success"} and not any(
            e.severity == "error"
            and e.category
            in {"installation", "network", "crash", "msi", "installer_log", "event_log", "gui"}
            for e in errors
        )

        return UnifiedInstallationReport(
            reportGeneratedAt=_utc_now(),
            status=InstallationStatusSection(
                sessionId=session.session_id,
                application=application,
                installationOutcome=outcome,
                workflowStatus=detection.status,
                installationCompleted=installation_completed,
                failureReason=detection.failure_reason,
                sessionStatus=session.session_status.value,
                startTimestamp=session.start_timestamp,
                endTimestamp=session.end_timestamp,
                durationSeconds=session.duration_seconds,
                installer=installer_details,
                artifactDirectory=session.output_directory,
                logFiles={
                    "stdout": installer_details.stdout_path,
                    "stderr": installer_details.stderr_path,
                    "msiVerbose": str(
                        Path(session.output_directory) / "msi_verbose.log"
                    )
                    if (Path(session.output_directory) / "msi_verbose.log").is_file()
                    else None,
                    "collectedLogs": str(Path(session.output_directory) / "collected_logs"),
                },
            ),
            errors=errors,
            evidence=EvidenceSection(
                eventLogs=event_logs.entries,
                eventLogCount=len(event_logs.entries),
                msiDiagnostics=msi_logs.diagnostics,
                crashReports=wer.reports,
                crashDetected=wer.crash_detected,
                processSnapshot=process.snapshots,
                childProcesses=process.child_processes,
                installerLogFiles=installer_logs.discovered_logs,
                registryChanges=registry.changes,
                filesystemChanges=filesystem.changes,
            ),
        )

    @staticmethod
    def write(report: UnifiedInstallationReport, destination: Path) -> Path:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            json.dumps(report.model_dump(by_alias=True, mode="json"), indent=2, ensure_ascii=False)
            + "\n",
            encoding="utf-8",
        )
        return destination


def publish_unified_report(
    report: UnifiedInstallationReport,
    *,
    reports_dir: Path,
    application_name: str,
) -> Path:
    """Write the only user-facing JSON to reports/."""
    slug = re.sub(r"[^a-zA-Z0-9]+", "", application_name.lower()) or "installer"
    date_stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    status_token = report.status.installation_outcome.lower()
    short_id = report.status.session_id[:8]
    filename = f"{slug}_{status_token}_{date_stamp}_{short_id}.json"
    path = reports_dir / filename
    UnifiedReportWriter.write(report, path)
    return path


def _map_detection_to_outcome(status: str) -> str:
    mapping = {
        "SUCCESS": "Success",
        "FAILED": "Failure",
        "CRASHED": "Crashed",
        "TIMED_OUT": "TimedOut",
        "PARTIAL": "Partial",
    }
    return mapping.get(status, "Unknown")


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
