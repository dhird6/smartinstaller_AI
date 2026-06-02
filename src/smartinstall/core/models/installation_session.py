"""InstallationSession model (data-model §1)."""

from __future__ import annotations

import re
from typing import Annotated

from pydantic import BaseModel, Field, field_validator

from smartinstall.core.enums.installation import InstallationOutcome, InstallerType
from smartinstall.core.enums.session import SessionStatus
from smartinstall.version import AGENT_VERSION, SCHEMA_VERSION

UUID_V4_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


class InstallationSession(BaseModel):
    session_id: str = Field(alias="sessionId")
    schema_version: str = Field(default=SCHEMA_VERSION, alias="schemaVersion")
    start_timestamp: str = Field(alias="startTimestamp")
    end_timestamp: str | None = Field(default=None, alias="endTimestamp")
    duration_seconds: int | None = Field(default=None, alias="durationSeconds", ge=0)
    session_status: SessionStatus = Field(alias="sessionStatus")
    machine_name: str = Field(alias="machineName", max_length=255)
    os_version: str = Field(alias="osVersion", max_length=100)
    os_build: str = Field(alias="osBuild", max_length=50)
    architecture: str = Field(pattern=r"^(x64|x86|ARM64)$")
    current_user: str = Field(alias="currentUser", max_length=255)
    installer_path: str = Field(alias="installerPath")
    installer_type: InstallerType = Field(alias="installerType")
    product_name: str | None = Field(default=None, alias="productName", max_length=255)
    product_version: str | None = Field(default=None, alias="productVersion", max_length=100)
    caller_tag: str | None = Field(default=None, alias="callerTag", max_length=500)
    output_directory: str = Field(alias="outputDirectory")
    exit_code: int | None = Field(default=None, alias="exitCode")
    installation_outcome: InstallationOutcome | None = Field(
        default=None, alias="installationOutcome"
    )
    diagnostic_score: Annotated[int | None, Field(ge=0, le=100)] = Field(
        default=None, alias="diagnosticScore"
    )
    report_path: str | None = Field(default=None, alias="reportPath")
    agent_version: str = Field(default=AGENT_VERSION, alias="agentVersion")

    model_config = {"populate_by_name": True}

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, value: str) -> str:
        if not UUID_V4_PATTERN.match(value):
            raise ValueError("sessionId must be a valid UUID v4")
        return value.lower()

    def to_session_json(self) -> dict[str, object]:
        return self.model_dump(by_alias=True, mode="json", exclude_none=False)
