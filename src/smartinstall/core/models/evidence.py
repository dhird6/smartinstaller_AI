"""Evidence fragments for failure reports (RAG/SLM-ready flat structures)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class InstallerDetails(BaseModel):
    installer_name: str = Field(alias="installerName")
    installer_path: str = Field(alias="installerPath")
    installer_type: str = Field(alias="installerType")
    process_id: int | None = Field(default=None, alias="processId")
    parent_process_id: int | None = Field(default=None, alias="parentProcessId")
    exit_code: int | None = Field(default=None, alias="exitCode")
    exit_code_description: str | None = Field(default=None, alias="exitCodeDescription")
    execution_duration_seconds: float | None = Field(
        default=None, alias="executionDurationSeconds"
    )
    command_line: str | None = Field(default=None, alias="commandLine")
    stdout_path: str | None = Field(default=None, alias="stdoutPath")
    stderr_path: str | None = Field(default=None, alias="stderrPath")
    timed_out: bool = Field(default=False, alias="timedOut")

    model_config = {"populate_by_name": True}


class ErrorDetails(BaseModel):
    primary_error_message: str = Field(alias="primaryErrorMessage")
    error_code: str | None = Field(default=None, alias="errorCode")
    error_source: str = Field(alias="errorSource")
    failure_timestamp: str = Field(alias="failureTimestamp")
    detection_signals: list[str] = Field(default_factory=list, alias="detectionSignals")

    model_config = {"populate_by_name": True}


class EventLogEvidence(BaseModel):
    event_id: int = Field(alias="eventId")
    source: str
    level: str
    message: str
    timestamp: str
    log_name: str = Field(alias="logName")
    record_id: int | None = Field(default=None, alias="recordId")

    model_config = {"populate_by_name": True}


class MsiDiagnosticEvidence(BaseModel):
    line_number: int = Field(alias="lineNumber")
    raw_text: str = Field(alias="rawText")
    error_code: str | None = Field(default=None, alias="errorCode")
    action_name: str | None = Field(default=None, alias="actionName")
    is_fatal: bool = Field(default=False, alias="isFatal")
    is_warning: bool = Field(default=False, alias="isWarning")
    is_rollback: bool = Field(default=False, alias="isRollback")

    model_config = {"populate_by_name": True}


class CrashReportEvidence(BaseModel):
    faulting_application: str | None = Field(default=None, alias="faultingApplication")
    faulting_module: str | None = Field(default=None, alias="faultingModule")
    exception_code: str | None = Field(default=None, alias="exceptionCode")
    crash_timestamp: str | None = Field(default=None, alias="crashTimestamp")
    report_directory: str | None = Field(default=None, alias="reportDirectory")
    friendly_event_name: str | None = Field(default=None, alias="friendlyEventName")

    model_config = {"populate_by_name": True}


class ProcessSnapshotItem(BaseModel):
    process_id: int = Field(alias="processId")
    parent_process_id: int | None = Field(default=None, alias="parentProcessId")
    process_name: str = Field(alias="processName")
    executable_path: str | None = Field(default=None, alias="executablePath")
    cpu_percent: float | None = Field(default=None, alias="cpuPercent")
    memory_mb: float | None = Field(default=None, alias="memoryMb")
    is_installer_root: bool = Field(default=False, alias="isInstallerRoot")

    model_config = {"populate_by_name": True}


class ChildProcessEvidence(BaseModel):
    """Child process spawned by the installer (e.g. mingw-get GUI subprocess)."""

    process_id: int = Field(alias="processId")
    parent_process_id: int | None = Field(default=None, alias="parentProcessId")
    process_name: str = Field(alias="processName")
    executable_path: str | None = Field(default=None, alias="executablePath")
    exit_code: int | None = Field(default=None, alias="exitCode")
    command_line: str | None = Field(default=None, alias="commandLine")

    model_config = {"populate_by_name": True}


class RegistryChangeEvidence(BaseModel):
    hive: str
    key_path: str = Field(alias="keyPath")
    value_name: str = Field(alias="valueName")
    change_type: str = Field(alias="changeType")  # added | removed | modified
    before_value: str | None = Field(default=None, alias="beforeValue")
    after_value: str | None = Field(default=None, alias="afterValue")

    model_config = {"populate_by_name": True}


class FilesystemChangeEvidence(BaseModel):
    path: str
    change_type: str = Field(alias="changeType")  # created | deleted | modified
    size_before: int | None = Field(default=None, alias="sizeBefore")
    size_after: int | None = Field(default=None, alias="sizeAfter")

    model_config = {"populate_by_name": True}


class InstallerLogFileEvidence(BaseModel):
    """Log file written by the installer or its children during the session."""

    file_path: str = Field(alias="filePath")
    copied_to: str | None = Field(default=None, alias="copiedTo")
    size_bytes: int = Field(alias="sizeBytes")
    modified_timestamp: str = Field(alias="modifiedTimestamp")
    extracted_error_count: int = Field(default=0, alias="extractedErrorCount")
    preview_lines: list[str] = Field(default_factory=list, alias="previewLines")

    model_config = {"populate_by_name": True}
