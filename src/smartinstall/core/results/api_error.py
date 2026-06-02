"""ApiError model (api-contracts §12)."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field

from smartinstall.core.exceptions.base import SmartInstallError


class ApiError(BaseModel):
    error_code: str = Field(alias="errorCode")
    message: str
    detail: str | None = None
    timestamp: str
    component: str

    model_config = {"populate_by_name": True}

    @classmethod
    def from_exception(cls, exc: SmartInstallError) -> ApiError:
        ctx = exc.context
        return cls(
            errorCode=ctx.error_code,
            message=ctx.message,
            detail=ctx.detail,
            timestamp=ctx.timestamp or cls._utc_now(),
            component=ctx.component,
        )

    @classmethod
    def create(
        cls,
        *,
        error_code: str,
        message: str,
        component: str,
        detail: str | None = None,
    ) -> ApiError:
        return cls(
            errorCode=error_code,
            message=message,
            detail=detail,
            timestamp=cls._utc_now(),
            component=component,
        )

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
