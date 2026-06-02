"""Unit tests for session state machine (M1-AC-05)."""

from smartinstall.agent.session.session_state_validator import SessionStateValidator
from smartinstall.core.enums.session import SessionStatus


def test_valid_forward_transitions() -> None:
    assert SessionStateValidator.can_transition(
        SessionStatus.INITIALIZING, SessionStatus.PRE_SNAPSHOTTING
    )
    assert SessionStateValidator.can_transition(
        SessionStatus.PRE_SNAPSHOTTING, SessionStatus.INSTALLING
    )
    assert SessionStateValidator.can_transition(
        SessionStatus.AGGREGATING, SessionStatus.COMPLETED
    )


def test_invalid_skip_transition() -> None:
    assert not SessionStateValidator.can_transition(
        SessionStatus.INITIALIZING, SessionStatus.COMPLETED
    )


def test_any_state_can_fail() -> None:
    assert SessionStateValidator.can_transition(SessionStatus.INSTALLING, SessionStatus.FAILED)
