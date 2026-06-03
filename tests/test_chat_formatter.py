"""Tests for desktop chat formatter."""

from smartinstall.core.models.evidence import InstallerDetails
from smartinstall.core.models.unified_report import (
    InstallationStatusSection,
    ReportErrorEntry,
    UnifiedInstallationReport,
)
from smartinstall.ui.services.chat_formatter import ChatFormatter


def _sample_report() -> UnifiedInstallationReport:
    installer = InstallerDetails(
        installerName="mingw-get-setup.exe",
        installerPath="C:\\installers\\mingw-get-setup.exe",
        installerType="EXE",
        exitCode=0,
    )
    status = InstallationStatusSection(
        sessionId="abc",
        application="mingw-get-setup",
        installationOutcome="Partial",
        workflowStatus="PARTIAL",
        installationCompleted=False,
        failureReason="GUI incomplete",
        sessionStatus="Completed",
        startTimestamp="2026-06-01T00:00:00.000Z",
        endTimestamp="2026-06-01T00:02:00.000Z",
        durationSeconds=120,
        installer=installer,
        artifactDirectory="C:\\sessions\\abc",
        logFiles={},
    )
    return UnifiedInstallationReport(
        reportGeneratedAt="2026-06-01T00:02:01.000Z",
        status=status,
        errors=[
            ReportErrorEntry(
                category="gui",
                code="GUI_INSTALL_INCOMPLETE",
                message="Installation likely incomplete",
                source="FailureDetector",
                timestamp="2026-06-01T00:02:00.000Z",
                severity="error",
            )
        ],
    )


def test_installation_summary_includes_error_code() -> None:
    message = ChatFormatter.installation_summary(_sample_report(), "reports\\sample.json")
    section_text = "\n".join(section.body for section in message.sections)
    assert "GUI_INSTALL_INCOMPLETE" in section_text
    assert "Partial" in section_text
