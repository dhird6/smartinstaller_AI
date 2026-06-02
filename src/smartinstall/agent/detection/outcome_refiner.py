"""Refine detection outcome after aggregating all error sources."""

from __future__ import annotations

from smartinstall.agent.detection.failure_detector import FailureDetectionOutcome
from smartinstall.core.models.evidence import ErrorDetails
from smartinstall.core.models.unified_report import ReportErrorEntry


def refine_outcome(
    detection: FailureDetectionOutcome,
    errors: list[ReportErrorEntry],
    *,
    failure_timestamp: str,
) -> FailureDetectionOutcome:
    """Upgrade SUCCESS/PARTIAL to FAILED when real errors exist; downgrade benign PARTIAL."""
    critical = [e for e in errors if e.severity == "error"]
    if critical:
        primary = critical[0]
        signals = list(detection.detection_signals)
        if "AGGREGATED_ERRORS" not in signals:
            signals.append("AGGREGATED_ERRORS")
        return FailureDetectionOutcome(
            status="FAILED",
            failure_reason=primary.message[:500],
            error_details=ErrorDetails(
                primaryErrorMessage=primary.message[:2000],
                errorCode=primary.code,
                errorSource=primary.source,
                failureTimestamp=primary.timestamp or failure_timestamp,
                detectionSignals=signals,
            ),
            detection_signals=signals,
        )

    warnings_only = errors and all(e.severity == "warning" for e in errors)
    if detection.status == "PARTIAL" and (not errors or warnings_only):
        return FailureDetectionOutcome(
            status="SUCCESS",
            failure_reason=None,
            error_details=None,
            detection_signals=detection.detection_signals,
        )

    return detection
