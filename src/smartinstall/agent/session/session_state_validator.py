"""Session state machine validation (api-contracts §2.2, functional-spec §1.3)."""

from __future__ import annotations

from smartinstall.core.enums.session import SessionStatus

_VALID_TRANSITIONS: dict[SessionStatus, frozenset[SessionStatus]] = {
    SessionStatus.INITIALIZING: frozenset({SessionStatus.PRE_SNAPSHOTTING, SessionStatus.FAILED}),
    SessionStatus.PRE_SNAPSHOTTING: frozenset(
        {SessionStatus.INSTALLING, SessionStatus.FAILED, SessionStatus.TIMED_OUT}
    ),
    SessionStatus.INSTALLING: frozenset(
        {SessionStatus.POST_SNAPSHOTTING, SessionStatus.FAILED, SessionStatus.TIMED_OUT}
    ),
    SessionStatus.POST_SNAPSHOTTING: frozenset(
        {SessionStatus.AGGREGATING, SessionStatus.FAILED, SessionStatus.TIMED_OUT}
    ),
    SessionStatus.AGGREGATING: frozenset(
        {SessionStatus.COMPLETED, SessionStatus.FAILED, SessionStatus.TIMED_OUT}
    ),
    SessionStatus.COMPLETED: frozenset(),
    SessionStatus.FAILED: frozenset(),
    SessionStatus.INCOMPLETE: frozenset(),
    SessionStatus.TIMED_OUT: frozenset(),
}

_ANY_STATE_TARGETS = frozenset(
    {SessionStatus.FAILED, SessionStatus.TIMED_OUT, SessionStatus.INCOMPLETE}
)


class SessionStateValidator:
    @staticmethod
    def can_transition(current: SessionStatus, target: SessionStatus) -> bool:
        if current == target:
            return True
        if target in _ANY_STATE_TARGETS:
            return True
        allowed = _VALID_TRANSITIONS.get(current, frozenset())
        return target in allowed

    @staticmethod
    def validate_transition(current: SessionStatus, target: SessionStatus) -> None:
        if SessionStateValidator.can_transition(current, target):
            return
        from smartinstall.core.exceptions.session import InvalidStateTransitionError

        raise InvalidStateTransitionError(
            session_id="",
            current=current.value,
            target=target.value,
        )
