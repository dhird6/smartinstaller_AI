"""ISessionManager contract (api-contracts §2)."""

from __future__ import annotations

from typing import Protocol

from smartinstall.core.enums.installation import InstallationOutcome
from smartinstall.core.enums.session import SessionStatus
from smartinstall.core.models.installation_session import InstallationSession
from smartinstall.core.models.requests import StartSessionRequest
from smartinstall.core.results.result import Result


class ISessionManager(Protocol):
    def create_session(self, request: StartSessionRequest) -> Result[InstallationSession]: ...

    def transition_state(
        self,
        session_id: str,
        target_state: SessionStatus,
        metadata: dict[str, object] | None = None,
    ) -> Result[bool]: ...

    def finalize_session(
        self,
        session_id: str,
        *,
        exit_code: int | None,
        outcome: InstallationOutcome,
        report_path: str | None,
    ) -> Result[InstallationSession]: ...

    def get_session(self, session_id: str) -> Result[InstallationSession]: ...

    def recover_incomplete_sessions(self) -> int: ...
