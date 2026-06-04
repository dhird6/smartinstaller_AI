"""Typed completion notifications (one per installation session)."""

from __future__ import annotations

from typing import Any

NOTIFICATION_TYPE_COMPLETE = "installation_complete"


def build_completion_notification(
    *,
    session_id: str,
    installer_name: str,
    outcome: str,
    report_path: str,
    has_errors: bool,
    mode: str,
    error_code: str = "",
    error_message: str = "",
    suggested_fix: str = "",
) -> dict[str, Any]:
    return {
        "type": NOTIFICATION_TYPE_COMPLETE,
        "sessionId": session_id,
        "installerName": installer_name,
        "outcome": outcome,
        "reportPath": report_path,
        "hasErrors": has_errors,
        "errorCode": error_code,
        "errorMessage": error_message,
        "suggestedFix": suggested_fix,
        "mode": mode,
    }


def is_completion_notification(payload: dict[str, Any]) -> bool:
    return payload.get("type") == NOTIFICATION_TYPE_COMPLETE
