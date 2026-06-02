"""Installation failure report — primary RAG/SLM input artifact."""

from __future__ import annotations

from pydantic import BaseModel, Field

from smartinstall.core.models.evidence import (
    CrashReportEvidence,
    ErrorDetails,
    EventLogEvidence,
    InstallerDetails,
    MsiDiagnosticEvidence,
    ProcessSnapshotItem,
)
from smartinstall.version import SCHEMA_VERSION

FAILURE_REPORT_FILENAME = "installation_failure_report.json"


class InstallationFailureReport(BaseModel):
    """Structured evidence package emitted when installation monitoring completes."""

    schema_version: str = Field(default=SCHEMA_VERSION, alias="schemaVersion")
    session_id: str = Field(alias="sessionId")
    application: str
    status: str  # SUCCESS | FAILED | CRASHED | PARTIAL | TIMED_OUT
    failure_reason: str | None = Field(default=None, alias="failureReason")
    report_generated_at: str = Field(alias="reportGeneratedAt")
    installer_details: InstallerDetails = Field(alias="installerDetails")
    error_details: ErrorDetails | None = Field(default=None, alias="errorDetails")
    event_logs: list[EventLogEvidence] = Field(default_factory=list, alias="eventLogs")
    msi_diagnostics: list[MsiDiagnosticEvidence] = Field(
        default_factory=list, alias="msiDiagnostics"
    )
    crash_reports: list[CrashReportEvidence] = Field(default_factory=list, alias="crashReports")
    process_snapshot: list[ProcessSnapshotItem] = Field(
        default_factory=list, alias="processSnapshot"
    )
    collection_errors: list[str] = Field(default_factory=list, alias="collectionErrors")

    model_config = {"populate_by_name": True}
