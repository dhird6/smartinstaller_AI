"""ConsolidatedInstallationReport scaffold (data-model §11 — foundation placeholder)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from smartinstall.core.enums.installation import InstallationOutcome
from smartinstall.core.models.collection_error import CollectionError
from smartinstall.core.models.installation_session import InstallationSession
from smartinstall.version import SCHEMA_VERSION


class InstallerResultStub(BaseModel):
    """Minimal installer result for foundation-phase reports."""

    session_id: str = Field(alias="sessionId")
    exit_code: int = Field(alias="exitCode", default=0)
    exit_code_description: str | None = Field(default=None, alias="exitCodeDescription")
    is_known_exit_code: bool = Field(default=False, alias="isKnownExitCode")
    installer_pid: int = Field(default=0, alias="installerPid")
    command_line: str = Field(default="", alias="commandLine")
    start_timestamp: str = Field(alias="startTimestamp")
    end_timestamp: str | None = Field(default=None, alias="endTimestamp")
    timed_out: bool = Field(default=False, alias="timedOut")
    stdout_path: str | None = Field(default=None, alias="stdoutPath")
    stderr_path: str | None = Field(default=None, alias="stderrPath")
    stdout_line_count: int = Field(default=0, alias="stdoutLineCount")
    stderr_line_count: int = Field(default=0, alias="stderrLineCount")
    stderr_high_priority_count: int = Field(default=0, alias="stderrHighPriorityCount")

    model_config = {"populate_by_name": True}


class ConsolidatedInstallationReport(BaseModel):
    schema_version: str = Field(default=SCHEMA_VERSION, alias="schemaVersion")
    report_generated_at: str = Field(alias="reportGeneratedAt")
    session: InstallationSession
    installer_result: InstallerResultStub = Field(alias="installerResult")
    event_log_delta: list[object] = Field(default_factory=list, alias="eventLogDelta")
    event_log_delta_count: int = Field(default=0, alias="eventLogDeltaCount")
    event_log_high_severity_count: int = Field(default=0, alias="eventLogHighSeverityCount")
    msi_errors: list[object] = Field(default_factory=list, alias="msiErrors")
    msi_warnings: list[object] = Field(default_factory=list, alias="msiWarnings")
    crash_reports: list[object] = Field(default_factory=list, alias="crashReports")
    crash_detected: bool = Field(default=False, alias="crashDetected")
    filesystem_events: list[object] = Field(default_factory=list, alias="filesystemEvents")
    filesystem_event_count: int = Field(default=0, alias="filesystemEventCount")
    filesystem_event_cap_reached: bool = Field(default=False, alias="filesystemEventCapReached")
    registry_changes: list[object] = Field(default_factory=list, alias="registryChanges")
    registry_change_count: int = Field(default=0, alias="registryChangeCount")
    process_tree: list[object] = Field(default_factory=list, alias="processTree")
    resource_samples: list[object] = Field(default_factory=list, alias="resourceSamples")
    resource_peak_cpu_percent: float | None = Field(default=None, alias="resourcePeakCpuPercent")
    resource_peak_memory_mb: float | None = Field(default=None, alias="resourcePeakMemoryMb")
    collection_errors: list[CollectionError] = Field(default_factory=list, alias="collectionErrors")
    installation_outcome: InstallationOutcome = Field(alias="installationOutcome")
    diagnostic_score: int = Field(default=0, alias="diagnosticScore", ge=0, le=100)

    model_config = {"populate_by_name": True}
