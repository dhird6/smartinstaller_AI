"""Build AutomatedRunResult from a published unified report file."""

from __future__ import annotations

from pathlib import Path

from smartinstall.agent.intake.installer_discovery import DiscoveredInstaller
from smartinstall.agent.orchestration.automated_run_orchestrator import AutomatedRunResult
from smartinstall.agent.slm.rag_engine import load_report
from smartinstall.core.enums.installation import InstallerType
from smartinstall.core.enums.session import SessionStatus
from smartinstall.core.models.installation_session import InstallationSession


def load_run_result_from_report(report_path: Path) -> AutomatedRunResult | None:
    """Load report JSON and wrap it for Troubleshooting / Monitoring UI."""
    try:
        report = load_report(report_path.resolve())
    except (OSError, ValueError):
        return None

    inst = report.status.installer
    installer_path = Path(inst.installer_path) if inst.installer_path else Path(inst.installer_name)
    suffix = installer_path.suffix.lower()
    installer_type = InstallerType.MSI if suffix == ".msi" else InstallerType.EXE

    session = InstallationSession.model_construct(
        session_id=report.status.session_id,
        start_timestamp=report.status.start_timestamp or "",
        session_status=SessionStatus.COMPLETED,
        machine_name="localhost",
        os_version="Windows",
        os_build="0",
        architecture="x64",
        current_user="monitor",
        installer_path=str(installer_path),
        installer_type=installer_type,
        output_directory=report.status.artifact_directory,
    )
    discovered = DiscoveredInstaller(
        path=installer_path,
        file_name=inst.installer_name,
        installer_type=installer_type.value,
        size_bytes=0,
        modified_timestamp=report.status.start_timestamp or "",
    )
    return AutomatedRunResult(
        session=session,
        discovered=discovered,
        report=report,
        report_path=report_path.resolve(),
        workflow_status=report.status.workflow_status,
    )
