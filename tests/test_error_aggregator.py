"""Tests for unified report error aggregation."""

from smartinstall.agent.collectors.event_log_collector import EventLogCollectionResult
from smartinstall.agent.collectors.installer_log_collector import InstallerLogCollectionResult
from smartinstall.agent.collectors.msi_log_collector import MsiLogCollectionResult
from smartinstall.agent.collectors.process_collector import ProcessCollectionResult
from smartinstall.agent.collectors.wer_collector import WerCollectionResult
from smartinstall.agent.detection.error_aggregator import build_error_entries
from smartinstall.agent.detection.failure_detector import FailureDetectionOutcome
from smartinstall.agent.runners.installer_runner import InstallerRunResult
from smartinstall.core.enums.installation import InstallerType
from smartinstall.core.models.evidence import ChildProcessEvidence, InstallerLogFileEvidence
from smartinstall.core.models.unified_report import ReportErrorEntry


def test_child_process_non_zero_exit_in_errors() -> None:
    run = InstallerRunResult(
        pid=1,
        parent_pid=0,
        command_line="setup.exe",
        start_timestamp="2026-06-01T00:00:00.000Z",
        end_timestamp="2026-06-01T00:01:00.000Z",
        exit_code=0,
    )
    process = ProcessCollectionResult(
        child_processes=[
            ChildProcessEvidence(
                processId=200,
                parentProcessId=1,
                processName="downloader.exe",
                executablePath="C:\\downloader.exe",
                exitCode=1,
            )
        ]
    )
    errors = build_error_entries(
        detection=FailureDetectionOutcome(
            status="SUCCESS",
            failure_reason=None,
            error_details=None,
            detection_signals=[],
        ),
        run_result=run,
        event_logs=EventLogCollectionResult(),
        msi_logs=MsiLogCollectionResult(),
        wer=WerCollectionResult(),
        installer_logs=InstallerLogCollectionResult(),
        process=process,
        collection_errors=[],
        installer_type=InstallerType.EXE,
        failure_timestamp="2026-06-01T00:01:00.000Z",
        is_gui_installer=True,
    )
    assert any(e.code == "CHILD_EXIT_1" for e in errors)


def test_gui_incomplete_suppressed_when_installer_log_found() -> None:
    run = InstallerRunResult(
        pid=1,
        parent_pid=0,
        command_line="setup.exe",
        start_timestamp="2026-06-01T00:00:00.000Z",
        end_timestamp="2026-06-01T00:01:00.000Z",
        exit_code=0,
    )
    installer_logs = InstallerLogCollectionResult(
        discovered_logs=[
            InstallerLogFileEvidence(
                filePath="C:\\Temp\\setup.log",
                copiedTo="C:\\session\\collected_logs\\setup.log",
                sizeBytes=100,
                modifiedTimestamp="2026-06-01T00:01:00.000Z",
                extractedErrorCount=0,
                previewLines=["network error"],
            )
        ],
        extracted_errors=[
            ReportErrorEntry(
                category="network",
                code="NETWORK_ERROR",
                message="network unreachable",
                source="installer_log:setup.log",
                timestamp="2026-06-01T00:01:00.000Z",
                severity="error",
            )
        ],
    )
    errors = build_error_entries(
        detection=FailureDetectionOutcome(
            status="SUCCESS",
            failure_reason=None,
            error_details=None,
            detection_signals=[],
        ),
        run_result=run,
        event_logs=EventLogCollectionResult(),
        msi_logs=MsiLogCollectionResult(),
        wer=WerCollectionResult(),
        installer_logs=installer_logs,
        process=ProcessCollectionResult(),
        collection_errors=[],
        installer_type=InstallerType.EXE,
        failure_timestamp="2026-06-01T00:01:00.000Z",
        is_gui_installer=True,
    )
    assert not any(e.code == "GUI_INSTALL_INCOMPLETE" for e in errors)
    assert any(e.category == "network" for e in errors)
