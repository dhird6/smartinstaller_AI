"""Build desktop run results from published SmartInstall JSON reports."""

from __future__ import annotations

import json
from pathlib import Path

from smartinstall.agent.intake.installer_discovery import DiscoveredInstaller
from smartinstall.agent.orchestration.automated_run_orchestrator import AutomatedRunResult
from smartinstall.agent.slm.rag_engine import load_report
from smartinstall.core.enums.installation import InstallationOutcome, InstallerType
from smartinstall.core.enums.session import SessionStatus
from smartinstall.core.models.installation_session import InstallationSession
from smartinstall.core.models.unified_report import UnifiedInstallationReport


def load_run_result_from_report(report_path: Path) -> AutomatedRunResult | None:
    """Hydrate an AutomatedRunResult from a report file (manual or automatic runs)."""
    try:
        resolved = report_path.resolve()
        report = load_report(resolved)
    except (OSError, ValueError, json.JSONDecodeError):
        return None

    session = _load_session_for_report(report)
    installer = report.status.installer
    installer_path = Path(installer.installer_path)
    discovered = DiscoveredInstaller(
        path=installer_path,
        file_name=installer.installer_name,
        installer_type=installer.installer_type,
        size_bytes=installer_path.stat().st_size if installer_path.is_file() else 0,
        modified_timestamp=report.status.start_timestamp,
    )
    return AutomatedRunResult(
        session=session,
        discovered=discovered,
        report=report,
        report_path=resolved,
        workflow_status=report.status.installation_outcome,
    )


def _load_session_for_report(report: UnifiedInstallationReport) -> InstallationSession:
    artifact_dir = Path(report.status.artifact_directory)
    manifest = artifact_dir / "session.json"
    if manifest.is_file():
        try:
            raw = json.loads(manifest.read_text(encoding="utf-8"))
            return InstallationSession.model_validate(raw)
        except (OSError, json.JSONDecodeError, ValueError):
            pass
    return _minimal_session_from_report(report)


def _minimal_session_from_report(report: UnifiedInstallationReport) -> InstallationSession:
    status = report.status
    installer = status.installer
    session_status = SessionStatus.COMPLETED if status.installation_completed else SessionStatus.FAILED
    try:
        installer_type = InstallerType(installer.installer_type)
    except ValueError:
        installer_type = InstallerType.UNKNOWN

    try:
        outcome = InstallationOutcome(status.installation_outcome)
    except ValueError:
        outcome = InstallationOutcome.UNKNOWN

    return InstallationSession(
        sessionId=status.session_id,
        startTimestamp=status.start_timestamp,
        endTimestamp=status.end_timestamp,
        sessionStatus=session_status,
        machineName="localhost",
        osVersion="Windows",
        osBuild="0",
        architecture="x64",
        currentUser="user",
        installerPath=installer.installer_path,
        installerType=installer_type,
        productName=status.application,
        outputDirectory=status.artifact_directory,
        exitCode=installer.exit_code,
        installationOutcome=outcome,
        reportPath=str(status.artifact_directory),
    )
