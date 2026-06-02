"""Base exception hierarchy for enterprise error handling."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True, slots=True)
class ErrorContext:
    """Structured context attached to domain errors."""

    component: str
    error_code: str
    message: str
    detail: str | None = None
    timestamp: str | None = None

    def __post_init__(self) -> None:
        if self.timestamp is None:
            object.__setattr__(
                self,
                "timestamp",
                datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
            )


class SmartInstallError(Exception):
    """Root exception for all SmartInstall AI domain failures."""

    def __init__(
        self,
        message: str,
        *,
        error_code: str,
        component: str,
        detail: str | None = None,
    ) -> None:
        self.context = ErrorContext(
            component=component,
            error_code=error_code,
            message=message,
            detail=detail,
        )
        super().__init__(message)

    @property
    def error_code(self) -> str:
        return self.context.error_code

    def to_dict(self) -> dict[str, Any]:
        return {
            "errorCode": self.context.error_code,
            "message": self.context.message,
            "detail": self.context.detail,
            "timestamp": self.context.timestamp,
            "component": self.context.component,
        }
