"""Session lifecycle manager (functional-spec §1, api-contracts §2)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

import structlog

from smartinstall.agent.infrastructure.event_bus import AgentEvent, EventBus
from smartinstall.agent.infrastructure.input_validator import (
    detect_installer_type,
    validate_caller_tag,
    validate_installer_path,
    validate_optional_output_root,
)
from smartinstall.agent.infrastructure.machine_context import capture_machine_context
from smartinstall.agent.infrastructure.output_directory_manager import OutputDirectoryManager
from smartinstall.agent.session.report_writer import ReportWriter
from smartinstall.agent.session.session_state_validator import SessionStateValidator
from smartinstall.core.enums.installation import InstallationOutcome
from smartinstall.core.enums.session import SessionStatus
from smartinstall.core.exceptions.base import SmartInstallError
from smartinstall.core.exceptions.session import (
    InstallerNotFoundError,
    InvalidStateTransitionError,
    SessionAlreadyActiveError,
    SessionNotFoundError,
)
from smartinstall.core.models.installation_session import InstallationSession
from smartinstall.core.models.requests import StartSessionRequest
from smartinstall.core.results.api_error import ApiError
from smartinstall.core.results.result import Result

logger = structlog.get_logger(__name__)


class SessionManager:
    """Creates, tracks, and finalizes installation sessions (ISessionManager)."""

    def __init__(
        self,
        output_manager: OutputDirectoryManager,
        event_bus: EventBus,
        report_writer: ReportWriter,
    ) -> None:
        self._output_manager = output_manager
        self._event_bus = event_bus
        self._report_writer = report_writer
        self._registry: dict[str, InstallationSession] = {}
        self._active_session_id: str | None = None

    def create_session(self, request: StartSessionRequest) -> Result[InstallationSession]:
        try:
            if self._active_session_id is not None:
                raise SessionAlreadyActiveError(self._active_session_id)

            validate_caller_tag(request.caller_tag)
            installer_path = validate_installer_path(request.installer_path)
            if not installer_path.is_file():
                raise InstallerNotFoundError(str(installer_path))

            override_root = validate_optional_output_root(request.output_directory)
            output_root = self._output_manager.ensure_output_root(override_root)

            installer_type = detect_installer_type(installer_path, request.installer_type)
            machine = capture_machine_context()
            session_id = uuid.uuid4()
            start_ts = _utc_now_iso()
            session_dir = self._output_manager.create_session_directory(session_id, output_root)

            session = InstallationSession(
                sessionId=str(session_id),
                startTimestamp=start_ts,
                sessionStatus=SessionStatus.INITIALIZING,
                machineName=machine.machine_name,
                osVersion=machine.os_version,
                osBuild=machine.os_build,
                architecture=machine.architecture,
                currentUser=machine.current_user,
                installerPath=str(installer_path),
                installerType=installer_type,
                productName=request.product_name,
                productVersion=request.product_version,
                callerTag=request.caller_tag,
                outputDirectory=str(session_dir),
            )

            self._output_manager.write_session_manifest(session)
            self._registry[session.session_id] = session
            self._active_session_id = session.session_id

            self._event_bus.publish(
                AgentEvent.SESSION_STARTED,
                {"sessionId": session.session_id, "outputDirectory": session.output_directory},
            )
            logger.info("session_created", session_id=session.session_id)
            return Result.ok(session)
        except SmartInstallError as exc:
            logger.warning("session_create_failed", error_code=exc.error_code)
            return Result.fail(ApiError.from_exception(exc))
        except Exception as exc:  # noqa: BLE001 — boundary converts to ApiError
            api_error = ApiError.create(
                error_code="SESSION_INTERNAL_ERROR",
                message=str(exc),
                component="SessionManager",
            )
            return Result.fail(api_error)

    def transition_state(
        self,
        session_id: str,
        target_state: SessionStatus,
        metadata: dict[str, object] | None = None,
    ) -> Result[bool]:
        try:
            session = self._get_session_or_raise(session_id)
            if not SessionStateValidator.can_transition(session.session_status, target_state):
                raise InvalidStateTransitionError(
                    session_id,
                    session.session_status.value,
                    target_state.value,
                )

            updated = session.model_copy(update={"session_status": target_state})
            if metadata:
                updated = updated.model_copy(update=metadata)

            self._registry[session_id] = updated
            self._output_manager.write_session_manifest(updated)
            logger.info(
                "session_state_transition",
                session_id=session_id,
                from_state=session.session_status.value,
                to_state=target_state.value,
            )
            return Result.ok(True)
        except SmartInstallError as exc:
            return Result.fail(ApiError.from_exception(exc))

    def finalize_session(
        self,
        session_id: str,
        *,
        exit_code: int | None,
        outcome: InstallationOutcome,
        report_path: str | None,
    ) -> Result[InstallationSession]:
        try:
            session = self._get_session_or_raise(session_id)
            end_ts = _utc_now_iso()
            start_dt = datetime.fromisoformat(session.start_timestamp.replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(end_ts.replace("Z", "+00:00"))
            duration = int((end_dt - start_dt).total_seconds())

            final = session.model_copy(
                update={
                    "session_status": SessionStatus.COMPLETED,
                    "end_timestamp": end_ts,
                    "duration_seconds": max(duration, 0),
                    "exit_code": exit_code,
                    "installation_outcome": outcome,
                    "report_path": report_path,
                    "diagnostic_score": 0 if outcome == InstallationOutcome.SUCCESS else 10,
                }
            )

            self._registry[session_id] = final
            self._output_manager.write_session_manifest(final)
            self._output_manager.append_sessions_index(
                final,
                outcome=outcome.value,
                diagnostic_score=final.diagnostic_score or 0,
            )

            if self._active_session_id == session_id:
                self._active_session_id = None

            self._event_bus.publish(
                AgentEvent.SESSION_ENDED,
                {"sessionId": session_id, "outcome": outcome.value, "reportPath": report_path},
            )
            logger.info("session_finalized", session_id=session_id, outcome=outcome.value)
            return Result.ok(final)
        except SmartInstallError as exc:
            return Result.fail(ApiError.from_exception(exc))

    def get_session(self, session_id: str) -> Result[InstallationSession]:
        try:
            return Result.ok(self._get_session_or_raise(session_id))
        except SmartInstallError as exc:
            return Result.fail(ApiError.from_exception(exc))

    def recover_incomplete_sessions(self) -> int:
        """Mark interrupted sessions as Incomplete (functional-spec §1.3, REL-02)."""
        count = 0
        for session_dir in self._output_manager.discover_incomplete_session_dirs():
            manifest = session_dir / OutputDirectoryManager.SESSION_MANIFEST
            try:
                import json

                data = json.loads(manifest.read_text(encoding="utf-8"))
                session = InstallationSession.model_validate(data)
            except Exception:
                continue

            if session.session_status == SessionStatus.INCOMPLETE:
                continue

            updated = session.model_copy(update={"session_status": SessionStatus.INCOMPLETE})
            self._output_manager.write_session_manifest(updated)
            self._registry[session.session_id] = updated
            count += 1
            logger.warning("session_recovered_incomplete", session_id=session.session_id)
        return count

    def run_foundation_lifecycle(
        self,
        request: StartSessionRequest,
        *,
        simulate_exit_code: int = 0,
    ) -> Result[InstallationSession]:
        """Foundation demo: walk state machine without launching installers."""
        create_result = self.create_session(request)
        if not create_result.success or create_result.value is None:
            return create_result

        session = create_result.value
        transitions = [
            SessionStatus.PRE_SNAPSHOTTING,
            SessionStatus.INSTALLING,
            SessionStatus.POST_SNAPSHOTTING,
            SessionStatus.AGGREGATING,
        ]
        for state in transitions:
            tr = self.transition_state(session.session_id, state)
            if not tr.success:
                return Result.fail(tr.error)  # type: ignore[arg-type]

        outcome = (
            InstallationOutcome.SUCCESS
            if simulate_exit_code == 0
            else InstallationOutcome.FAILURE
        )
        report_path = self._report_writer.write_foundation_report(
            self._get_session_or_raise(session.session_id),
            exit_code=simulate_exit_code,
            outcome=outcome,
        )
        return self.finalize_session(
            session.session_id,
            exit_code=simulate_exit_code,
            outcome=outcome,
            report_path=str(report_path),
        )

    def _get_session_or_raise(self, session_id: str) -> InstallationSession:
        session = self._registry.get(session_id)
        if session is not None:
            return session
        raise SessionNotFoundError(session_id)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
