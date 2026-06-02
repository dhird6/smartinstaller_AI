"""Session-related exceptions (api-contracts §1–2, functional-spec §1)."""

from smartinstall.core.exceptions.base import SmartInstallError


class SessionError(SmartInstallError):
    """Base class for session lifecycle failures."""

    def __init__(
        self,
        message: str,
        *,
        error_code: str,
        detail: str | None = None,
    ) -> None:
        super().__init__(
            message,
            error_code=error_code,
            component="SessionManager",
            detail=detail,
        )


class InstallerNotFoundError(SessionError):
    def __init__(self, installer_path: str) -> None:
        super().__init__(
            f"Installer not found: {installer_path}",
            error_code="SESSION_INSTALLER_NOT_FOUND",
            detail=installer_path,
        )


class InsufficientDiskSpaceError(SessionError):
    def __init__(self, required_gb: float, available_gb: float) -> None:
        super().__init__(
            f"Insufficient disk space: {available_gb:.2f} GB free, {required_gb:.2f} GB required",
            error_code="SESSION_INSUFFICIENT_DISK_SPACE",
            detail=f"required={required_gb},available={available_gb}",
        )


class OutputDirectoryNotWritableError(SessionError):
    def __init__(self, path: str, reason: str | None = None) -> None:
        super().__init__(
            f"Output directory is not writable: {path}",
            error_code="SESSION_OUTPUT_DIR_NOT_WRITABLE",
            detail=reason,
        )


class InsufficientPrivilegesError(SessionError):
    def __init__(self, detail: str | None = None) -> None:
        super().__init__(
            "Required Windows privileges are not held",
            error_code="SESSION_INSUFFICIENT_PRIVILEGES",
            detail=detail,
        )


class SessionAlreadyActiveError(SessionError):
    def __init__(self, session_id: str) -> None:
        super().__init__(
            "A session is already in progress (Phase 1 allows one active session)",
            error_code="SESSION_ALREADY_ACTIVE",
            detail=session_id,
        )


class SessionNotFoundError(SessionError):
    def __init__(self, session_id: str) -> None:
        super().__init__(
            f"Session not found: {session_id}",
            error_code="SESSION_NOT_FOUND",
            detail=session_id,
        )


class InvalidStateTransitionError(SessionError):
    def __init__(self, session_id: str, current: str, target: str) -> None:
        super().__init__(
            f"Invalid state transition for session {session_id}: {current} -> {target}",
            error_code="SESSION_INVALID_STATE_TRANSITION",
            detail=f"current={current},target={target}",
        )
