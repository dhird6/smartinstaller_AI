"""Application exit and pending-work checks for the desktop shell."""

from __future__ import annotations


def has_pending_installation_work(
    *,
    controller_busy: bool,
    active_session_id: str,
    active_installation_count: int,
) -> bool:
    """Return True when quitting would interrupt an in-flight monitored install."""
    if controller_busy:
        return True
    if active_session_id:
        return True
    return active_installation_count > 0


def should_confirm_exit(
    *,
    confirm_when_busy: bool,
    controller_busy: bool,
    active_session_id: str,
    active_installation_count: int,
) -> bool:
    """Return True when the user should be prompted before exiting."""
    if not confirm_when_busy:
        return False
    return has_pending_installation_work(
        controller_busy=controller_busy,
        active_session_id=active_session_id,
        active_installation_count=active_installation_count,
    )
