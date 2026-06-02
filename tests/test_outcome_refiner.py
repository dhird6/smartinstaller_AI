"""Tests for outcome refinement after error aggregation."""

from smartinstall.agent.detection.failure_detector import FailureDetectionOutcome
from smartinstall.agent.detection.outcome_refiner import refine_outcome
from smartinstall.core.models.unified_report import ReportErrorEntry


def test_upgrades_partial_to_success_when_only_benign_warnings() -> None:
    detection = FailureDetectionOutcome(
        status="PARTIAL",
        failure_reason=None,
        error_details=None,
        detection_signals=["PARTIAL_EVIDENCE"],
    )
    errors = [
        ReportErrorEntry(
            category="collection",
            code="COLLECTOR_ERROR",
            message="minor",
            source="test",
            severity="warning",
        )
    ]
    refined = refine_outcome(detection, errors, failure_timestamp="2026-06-01T00:00:00.000Z")
    assert refined.status == "SUCCESS"


def test_upgrades_to_failed_on_critical_errors() -> None:
    detection = FailureDetectionOutcome(
        status="SUCCESS",
        failure_reason=None,
        error_details=None,
        detection_signals=[],
    )
    errors = [
        ReportErrorEntry(
            category="network",
            code="NETWORK_ERROR",
            message="Connection timed out",
            source="stderr",
            severity="error",
        )
    ]
    refined = refine_outcome(detection, errors, failure_timestamp="2026-06-01T00:00:00.000Z")
    assert refined.status == "FAILED"
