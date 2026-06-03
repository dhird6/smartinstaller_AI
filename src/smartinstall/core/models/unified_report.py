"""Single canonical installation report (status + errors in one file)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from smartinstall.core.models.evidence import (
    ChildProcessEvidence,
    CrashReportEvidence,
    EventLogEvidence,
    FilesystemChangeEvidence,
    InstallerDetails,
    InstallerLogFileEvidence,
    MsiDiagnosticEvidence,
    ProcessSnapshotItem,
    RegistryChangeEvidence,
)
from smartinstall.version import SCHEMA_VERSION

# Single output artifact filename (reports/ and referenced by session.reportPath)
UNIFIED_REPORT_FILENAME = "smartinstall_report.json"


class ReportErrorEntry(BaseModel):
    """One error or warning entry for the errors section."""

    category: str  # installation | network | collection | event_log | msi | crash | gui | installer_log
    code: str
    message: str
    source: str
    timestamp: str | None = None
    severity: str = "error"  # error | warning | info
    raw_excerpt: str | None = Field(default=None, alias="rawExcerpt")

    model_config = {"populate_by_name": True}


class InstallationStatusSection(BaseModel):
    """Full installation status (section 1 of unified report)."""

    session_id: str = Field(alias="sessionId")
    application: str
    installation_outcome: str = Field(alias="installationOutcome")
    workflow_status: str = Field(alias="workflowStatus")
    installation_completed: bool = Field(alias="installationCompleted")
    failure_reason: str | None = Field(default=None, alias="failureReason")
    session_status: str = Field(alias="sessionStatus")
    start_timestamp: str = Field(alias="startTimestamp")
    end_timestamp: str | None = Field(default=None, alias="endTimestamp")
    duration_seconds: int | None = Field(default=None, alias="durationSeconds")
    installer: InstallerDetails
    artifact_directory: str = Field(alias="artifactDirectory")
    log_files: dict[str, str | None] = Field(default_factory=dict, alias="logFiles")

    model_config = {"populate_by_name": True}


class EvidenceSection(BaseModel):
    """Collected diagnostic evidence (embedded in unified report)."""

    event_logs: list[EventLogEvidence] = Field(default_factory=list, alias="eventLogs")
    event_log_count: int = Field(default=0, alias="eventLogCount")
    msi_diagnostics: list[MsiDiagnosticEvidence] = Field(default_factory=list, alias="msiDiagnostics")
    crash_reports: list[CrashReportEvidence] = Field(default_factory=list, alias="crashReports")
    crash_detected: bool = Field(default=False, alias="crashDetected")
    process_snapshot: list[ProcessSnapshotItem] = Field(default_factory=list, alias="processSnapshot")
    child_processes: list[ChildProcessEvidence] = Field(default_factory=list, alias="childProcesses")
    installer_log_files: list[InstallerLogFileEvidence] = Field(
        default_factory=list, alias="installerLogFiles"
    )
    registry_changes: list[RegistryChangeEvidence] = Field(
        default_factory=list, alias="registryChanges"
    )
    filesystem_changes: list[FilesystemChangeEvidence] = Field(
        default_factory=list, alias="filesystemChanges"
    )

    model_config = {"populate_by_name": True}


class UnifiedInstallationReport(BaseModel):
    """
    Canonical SmartInstall report — one JSON file per run.

    Top-level keys:
      - status: full installation status
      - errors: all detected errors (install, network, collection, etc.)
      - evidence: optional detailed evidence for RAG/SLM
    """

    schema_version: str = Field(default=SCHEMA_VERSION, alias="schemaVersion")
    report_generated_at: str = Field(alias="reportGeneratedAt")
    status: InstallationStatusSection
    errors: list[ReportErrorEntry] = Field(default_factory=list)
    evidence: EvidenceSection = Field(default_factory=EvidenceSection)

    model_config = {"populate_by_name": True}
