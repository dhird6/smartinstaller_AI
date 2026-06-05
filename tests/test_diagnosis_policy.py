"""Tests for SLM eligibility — avoid Ollama diagnosis on successful third-party installs."""

from smartinstall.agent.slm.diagnosis_policy import (
    actionable_install_errors,
    should_run_slm_diagnosis,
)
from smartinstall.core.models.evidence import InstallerDetails
from smartinstall.core.models.unified_report import (
    InstallationStatusSection,
    ReportErrorEntry,
    UnifiedInstallationReport,
)


def _report(
    *,
    outcome: str = "Success",
    errors: list[ReportErrorEntry] | None = None,
    installer_name: str = "mingw-get-setup.exe",
) -> UnifiedInstallationReport:
    return UnifiedInstallationReport(
        reportGeneratedAt="2026-06-04T00:01:00Z",
        status=InstallationStatusSection(
            sessionId="test-session",
            application="mingw-get-setup",
            installationOutcome=outcome,
            workflowStatus=outcome.upper(),
            installationCompleted=outcome.lower() in {"success", "completed"},
            failureReason=None,
            sessionStatus="Completed",
            startTimestamp="2026-06-04T00:00:00Z",
            endTimestamp="2026-06-04T00:01:00Z",
            durationSeconds=60.0,
            installer=InstallerDetails(
                installerName=installer_name,
                installerPath=r"C:\Downloads\mingw-get-setup.exe",
                installerType="EXE",
                processId=1,
                parentProcessId=2,
                exitCode=0,
                exitCodeDescription="ok",
                executionDurationSeconds=60.0,
                commandLine="mingw-get-setup.exe",
            ),
            artifactDirectory=r"C:\sessions\test",
        ),
        errors=errors or [],
    )


def test_success_with_collector_warning_does_not_trigger_slm() -> None:
    report = _report(
        errors=[
            ReportErrorEntry(
                category="collection",
                code="COLLECTOR_ERROR",
                message="'ProcessCollector' object has no attribute '_collect_tree_pids'",
                source="LogCollector",
                timestamp="2026-06-04T00:01:00Z",
                severity="warning",
            )
        ]
    )
    assert should_run_slm_diagnosis(report) is False
    assert actionable_install_errors(report.errors) == []


def test_failed_mingw_install_triggers_slm() -> None:
    report = _report(
        outcome="Failure",
        errors=[
            ReportErrorEntry(
                category="installation",
                code="INSTALL_LOG_ERROR",
                message="Download failed: connection timed out",
                source="installer_log",
                timestamp="2026-06-04T00:01:00Z",
                severity="error",
            )
        ],
    )
    assert should_run_slm_diagnosis(report) is True
    assert len(actionable_install_errors(report.errors)) == 1
