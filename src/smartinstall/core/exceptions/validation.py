"""Input validation exceptions (SEC-08, api-contracts SESSION_INVALID_INPUT)."""

from smartinstall.core.exceptions.base import SmartInstallError


class InvalidInputError(SmartInstallError):
    def __init__(self, message: str, *, detail: str | None = None) -> None:
        super().__init__(
            message,
            error_code="SESSION_INVALID_INPUT",
            component="InputValidator",
            detail=detail,
        )
