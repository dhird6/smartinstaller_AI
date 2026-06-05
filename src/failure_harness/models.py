"""Pydantic models for harness configuration and reporting."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class FailureCategory(str, Enum):
    """All supported failure injection categories."""

    DOWNLOAD_ACQUISITION = "download_acquisition"
    DISK_STORAGE = "disk_storage"
    PERMISSIONS_SECURITY = "permissions_security"
    DEPENDENCY = "dependency"
    VERSION_COMPATIBILITY = "version_compatibility"
    REGISTRY = "registry"
    SERVICE = "service"
    INSTALLER_ENGINE = "installer_engine"
    FILE_PROCESS_LOCKING = "file_process_locking"
    OS_LEVEL = "os_level"
    GPU_DRIVER = "gpu_driver"
    LICENSING = "licensing"
    CLOUD_API = "cloud_api"
    ENTERPRISE_DEPLOYMENT = "enterprise_deployment"
    UPDATE = "update"
    UNINSTALLATION = "uninstallation"
    MIGRATION = "migration"
    LOCALIZATION = "localization"
    PLUGIN_ECOSYSTEM = "plugin_ecosystem"
    HUMAN_USER = "human_user"
    TELEMETRY = "telemetry"
    RARE_EDGE_CASE = "rare_edge_case"


class FailureMode(str, Enum):
    """How failures are scheduled within a scenario."""

    SINGLE = "single"
    SIMULTANEOUS = "simultaneous"
    SEQUENTIAL = "sequential"
    RANDOM = "random"
    DETERMINISTIC = "deterministic"


class FailureSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RecoveryPolicy(str, Enum):
    NONE = "none"
    RETRY = "retry"
    SKIP = "skip"
    ABORT = "abort"
    AUTO = "auto"


class InjectedFailureSpec(BaseModel):
    """Single failure injection definition."""

    id: str
    category: FailureCategory
    sub_type: str = Field(alias="subType")
    severity: FailureSeverity = FailureSeverity.MEDIUM
    delay_seconds: float = Field(default=0.0, alias="delaySeconds")
    duration_seconds: float | None = Field(default=None, alias="durationSeconds")
    exit_code: int | None = Field(default=None, alias="exitCode")
    message: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    expected_rag_keywords: list[str] = Field(default_factory=list, alias="expectedRagKeywords")
    recovery_policy: RecoveryPolicy = Field(default=RecoveryPolicy.AUTO, alias="recoveryPolicy")
    retry_count: int = Field(default=0, alias="retryCount")

    model_config = {"populate_by_name": True}


class ScenarioConfig(BaseModel):
    """JSON scenario driving a harness test run."""

    scenario_id: str = Field(alias="scenarioId")
    name: str
    description: str = ""
    failure_mode: FailureMode = Field(default=FailureMode.SINGLE, alias="failureMode")
    failures: list[InjectedFailureSpec]
    random_seed: int | None = Field(default=None, alias="randomSeed")
    install_timeout_seconds: int = Field(default=300, alias="installTimeoutSeconds")
    expect_smart_installer_detection: bool = Field(default=True, alias="expectSmartInstallerDetection")
    expect_rag_response: bool = Field(default=True, alias="expectRagResponse")
    min_rag_relevance_score: float = Field(default=0.3, alias="minRagRelevanceScore")

    model_config = {"populate_by_name": True}


class HarnessConfig(BaseModel):
    """Top-level harness configuration."""

    harness_version: str = Field(default="1.0", alias="harnessVersion")
    smart_installer_root: str | None = Field(default=None, alias="smartInstallerRoot")
    test_app_path: str | None = Field(default=None, alias="testAppPath")
    scenarios_directory: str = Field(default="failure_harness/config/scenarios", alias="scenariosDirectory")
    output_directory: str = Field(default="failure_harness/artifacts", alias="outputDirectory")
    logs_directory: str = Field(default="failure_harness/logs", alias="logsDirectory")
    rag_docs_directory: str | None = Field(default=None, alias="ragDocsDirectory")
    phase1_skip_install: bool = Field(default=True, alias="phase1SkipInstall")
    phase1_launch_desktop: bool = Field(default=False, alias="phase1LaunchDesktop")
    phase1_start_background_monitor: bool = Field(default=True, alias="phase1StartBackgroundMonitor")
    ollama_host: str = Field(default="http://127.0.0.1:11434", alias="ollamaHost")
    slm_model: str = Field(default="phi3:mini", alias="slmModel")
    embedding_model: str = Field(default="nomic-embed-text", alias="embeddingModel")
    default_scenario: str | None = Field(default=None, alias="defaultScenario")

    model_config = {"populate_by_name": True}


class HarnessEvent(BaseModel):
    """Structured log event."""

    timestamp: str
    phase: str
    component: str
    event_type: str = Field(alias="eventType")
    message: str
    details: dict[str, Any] = Field(default_factory=dict)

    model_config = {"populate_by_name": True}


class RagValidationResult(BaseModel):
    """RAG response validation outcome."""

    success: bool
    relevance_score: float = Field(alias="relevanceScore")
    matched_keywords: list[str] = Field(default_factory=list, alias="matchedKeywords")
    expected_keywords: list[str] = Field(default_factory=list, alias="expectedKeywords")
    sources: list[str] = Field(default_factory=list)
    answer_preview: str = Field(default="", alias="answerPreview")

    model_config = {"populate_by_name": True}


class PhaseResult(BaseModel):
    """Outcome of a harness phase."""

    phase: str
    success: bool
    duration_seconds: float = Field(alias="durationSeconds")
    checks: list[dict[str, Any]] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class HarnessRunReport(BaseModel):
    """Final harness execution report."""

    run_id: str = Field(alias="runId")
    scenario_id: str = Field(alias="scenarioId")
    started_at: str = Field(alias="startedAt")
    completed_at: str = Field(alias="completedAt")
    overall_success: bool = Field(alias="overallSuccess")
    phase1: PhaseResult
    phase2: PhaseResult
    failure_timeline: list[HarnessEvent] = Field(default_factory=list, alias="failureTimeline")
    recovery_timeline: list[HarnessEvent] = Field(default_factory=list, alias="recoveryTimeline")
    rag_validation: RagValidationResult | None = Field(default=None, alias="ragValidation")
    smart_install_report_path: str | None = Field(default=None, alias="smartInstallReportPath")
    metrics: dict[str, Any] = Field(default_factory=dict)

    model_config = {"populate_by_name": True}
