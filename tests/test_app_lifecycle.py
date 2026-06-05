"""Tests for desktop application exit policy."""

from smartinstall.ui.services.app_lifecycle import has_pending_installation_work, should_confirm_exit


def test_has_pending_installation_work_detects_busy_controller() -> None:
    assert has_pending_installation_work(
        controller_busy=True,
        active_session_id="",
        active_installation_count=0,
    )


def test_has_pending_installation_work_detects_active_session() -> None:
    assert has_pending_installation_work(
        controller_busy=False,
        active_session_id="sess-1",
        active_installation_count=0,
    )


def test_has_pending_installation_work_idle_when_nothing_active() -> None:
    assert not has_pending_installation_work(
        controller_busy=False,
        active_session_id="",
        active_installation_count=0,
    )


def test_should_confirm_exit_respects_config_flag() -> None:
    assert not should_confirm_exit(
        confirm_when_busy=False,
        controller_busy=True,
        active_session_id="sess-1",
        active_installation_count=1,
    )
    assert should_confirm_exit(
        confirm_when_busy=True,
        controller_busy=True,
        active_session_id="",
        active_installation_count=0,
    )
