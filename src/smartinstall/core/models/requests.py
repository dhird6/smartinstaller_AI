"""API request/response DTOs (api-contracts §1)."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from smartinstall.core.enums.installation import InstallerType
from smartinstall.core.results.api_error import ApiError


class StartSessionRequest(BaseModel):
    installer_path: str = Field(alias="installerPath")
    installer_type: InstallerType | None = Field(default=None, alias="installerType")
    product_name: str | None = Field(default=None, alias="productName", max_length=255)
    product_version: str | None = Field(default=None, alias="productVersion", max_length=100)
    caller_tag: str | None = Field(default=None, alias="callerTag", max_length=500)
    output_directory: str | None = Field(default=None, alias="outputDirectory")
    additional_args: str | None = Field(default=None, alias="additionalArgs")
    timeout_seconds: int | None = Field(default=None, alias="timeoutSeconds", ge=1)
    copy_dumps: bool | None = Field(default=None, alias="copyDumps")

    model_config = {"populate_by_name": True}

    @field_validator("installer_path")
    @classmethod
    def strip_installer_path(cls, value: str) -> str:
        return value.strip()


class StartSessionResponse(BaseModel):
    success: bool
    session_id: str | None = Field(default=None, alias="sessionId")
    session_directory: str | None = Field(default=None, alias="sessionDirectory")
    error: ApiError | None = None

    model_config = {"populate_by_name": True}
