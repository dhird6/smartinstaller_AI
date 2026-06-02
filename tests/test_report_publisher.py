"""Tests for unified report publishing."""

from pathlib import Path

from smartinstall.agent.intake.report_publisher import ReportPublisher
from smartinstall.core.models.evidence import InstallerDetails
from smartinstall.core.models.unified_report import (
    EvidenceSection,
    InstallationStatusSection,
    ReportErrorEntry,
    UnifiedInstallationReport,
)


def test_publish_writes_single_report(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports"
    report = UnifiedInstallationReport(
        reportGeneratedAt="2026-06-01T00:00:00.000Z",
        status=InstallationStatusSection(
            sessionId="a1b2c3d4-e5f6-4789-a012-3456789abcde",
            application="Notepad++",
            installationOutcome="Failure",
            workflowStatus="FAILED",
            installationCompleted=False,
            sessionStatus="Completed",
            startTimestamp="2026-06-01T00:00:00.000Z",
            installer=InstallerDetails(
                installerName="npp.exe",
                installerPath="C:\\installers\\npp.exe",
                installerType="EXE",
            ),
            artifactDirectory=str(tmp_path / "sessions" / "uuid"),
        ),
        errors=[
            ReportErrorEntry(
                category="network",
                code="NETWORK_ERROR",
                message="Connection failed",
                source="stderr:line10",
                severity="error",
            )
        ],
        evidence=EvidenceSection(),
    )

    path = ReportPublisher(reports_dir).publish(report, application_name="Notepad++")
    assert path.is_file()
    assert path.parent == reports_dir.resolve()
    assert "notepad" in path.name.lower()
    assert list(reports_dir.glob("*.json")) == [path]
