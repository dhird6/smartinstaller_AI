"""Tests for per-session completion notifications."""

from __future__ import annotations

from pathlib import Path

from smartinstall.agent.monitoring.completion_notifications import (
    NOTIFICATION_TYPE_COMPLETE,
    build_completion_notification,
    is_completion_notification,
)
from smartinstall.agent.monitoring.monitoring_state_store import MonitoringStateStore


def test_build_completion_notification() -> None:
    payload = build_completion_notification(
        session_id="11111111-1111-4111-8111-111111111111",
        installer_name="setup.exe",
        outcome="Failure",
        report_path=r"C:\reports\smartinstall_report.json",
        has_errors=True,
        mode="automatic",
        error_code="E1",
        error_message="failed",
    )
    assert is_completion_notification(payload)
    assert payload["type"] == NOTIFICATION_TYPE_COMPLETE
    assert payload["hasErrors"] is True


def test_enqueue_replaces_duplicate_session(tmp_path: Path) -> None:
    store = MonitoringStateStore(tmp_path / "state.json")
    first = build_completion_notification(
        session_id="11111111-1111-4111-8111-111111111111",
        installer_name="a.exe",
        outcome="Failure",
        report_path="r1.json",
        has_errors=True,
        mode="automatic",
        error_message="first",
    )
    second = build_completion_notification(
        session_id="11111111-1111-4111-8111-111111111111",
        installer_name="a.exe",
        outcome="Failure",
        report_path="r1.json",
        has_errors=True,
        mode="automatic",
        error_message="second",
    )
    store.enqueue_notification(first)
    store.enqueue_notification(second)
    drained = store.drain_notifications()
    assert len(drained) == 1
    assert drained[0]["errorMessage"] == "second"
