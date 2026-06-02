"""Tests for failure detection logic."""

from smartinstall.agent.collectors.event_log_collector import EventLogCollectionResult
from smartinstall.agent.collectors.msi_log_collector import MsiLogCollectionResult
from smartinstall.agent.collectors.process_collector import ProcessCollectionResult
from smartinstall.agent.collectors.wer_collector import WerCollectionResult
from smartinstall.agent.detection.failure_detector import FailureDetector
from smartinstall.agent.runners.installer_runner import InstallerRunResult
from smartinstall.core.models.evidence import EventLogEvidence, MsiDiagnosticEvidence


def test_detects_non_zero_exit_code() -> None:
    detector = FailureDetector()
    run = InstallerRunResult(
        pid=100,
        parent_pid=1,
        command_line="setup.exe",
        start_timestamp="2026-06-01T00:00:00.000Z",
        end_timestamp="2026-06-01T00:01:00.000Z",
        exit_code=1603,
    )
    outcome = detector.analyze(
        run_result=run,
        event_logs=EventLogCollectionResult(),
        msi_logs=MsiLogCollectionResult(),
        wer=WerCollectionResult(),
        process=ProcessCollectionResult(),
        application_name="Test",
    )
    assert outcome.status == "FAILED"
    assert outcome.failure_reason is not None
    assert "1603" in outcome.failure_reason


def test_detects_msi_fatal() -> None:
    detector = FailureDetector()
    run = InstallerRunResult(
        pid=100,
        parent_pid=1,
        command_line="msiexec",
        start_timestamp="2026-06-01T00:00:00.000Z",
        end_timestamp="2026-06-01T00:01:00.000Z",
        exit_code=0,
    )
    msi = MsiLogCollectionResult(
        fatal_detected=True,
        diagnostics=[
            MsiDiagnosticEvidence(
                lineNumber=10,
                rawText="Return value 3",
                isFatal=True,
                isWarning=False,
                isRollback=False,
            )
        ],
    )
    outcome = detector.analyze(
        run_result=run,
        event_logs=EventLogCollectionResult(),
        msi_logs=msi,
        wer=WerCollectionResult(),
        process=ProcessCollectionResult(),
        application_name="Test",
    )
    assert outcome.status == "FAILED"


def test_success_when_clean() -> None:
    detector = FailureDetector()
    run = InstallerRunResult(
        pid=100,
        parent_pid=1,
        command_line="setup.exe",
        start_timestamp="2026-06-01T00:00:00.000Z",
        end_timestamp="2026-06-01T00:01:00.000Z",
        exit_code=0,
    )
    outcome = detector.analyze(
        run_result=run,
        event_logs=EventLogCollectionResult(),
        msi_logs=MsiLogCollectionResult(),
        wer=WerCollectionResult(),
        process=ProcessCollectionResult(),
        application_name="Test",
    )
    assert outcome.status == "SUCCESS"
