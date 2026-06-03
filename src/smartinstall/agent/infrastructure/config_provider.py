"""Configuration management (MAINT-02, EXT-05, architecture ConfigProvider)."""

from __future__ import annotations

import json
import os
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from smartinstall.agent.infrastructure.project_paths import get_project_root
from smartinstall.version import SCHEMA_VERSION


class LogLevel(StrEnum):
    VERBOSE = "Verbose"
    DEBUG = "Debug"
    INFO = "Info"
    WARNING = "Warning"
    ERROR = "Error"


class SmartInstallConfig(BaseSettings):
    """Validated agent configuration loaded from smartinstall.config.json."""

    config_version: str = Field(default="1.0", alias="configVersion")
    installers_dir: Path = Field(default=Path("installers"), alias="installersDirectory")
    reports_dir: Path = Field(default=Path("reports"), alias="reportsDirectory")
    logs_dir: Path = Field(default=Path("logs"), alias="logsDirectory")
    output_root: Path = Field(default=Path("sessions"), alias="outputRoot")
    sessions_summary_dir: Path | None = Field(default=None, alias="sessionsSummaryDirectory")
    agent_log_path: Path = Field(default=Path("logs/application.log"), alias="agentLogPath")
    log_level: LogLevel = Field(default=LogLevel.INFO, alias="logLevel")
    schema_version: str = Field(default=SCHEMA_VERSION, alias="schemaVersion")
    agent_version: str = Field(alias="agentVersion")
    min_free_disk_space_gb: float = Field(default=1.0, alias="minFreeDiskSpaceGb", gt=0)
    default_installer_timeout_seconds: int = Field(
        default=1800, alias="defaultInstallerTimeoutSeconds", ge=1
    )
    collector_pre_snapshot_timeout_seconds: int = Field(
        default=30, alias="collectorPreSnapshotTimeoutSeconds", ge=1
    )
    collector_post_snapshot_timeout_seconds: int = Field(
        default=60, alias="collectorPostSnapshotTimeoutSeconds", ge=1
    )
    max_filesystem_events: int = Field(default=10000, alias="maxFilesystemEvents", ge=1)
    max_event_log_entries: int = Field(default=50000, alias="maxEventLogEntries", ge=1)
    max_msi_log_size_mb: int = Field(default=200, alias="maxMsiLogSizeMb", ge=1)
    max_stdout_stderr_lines: int = Field(default=50000, alias="maxStdoutStderrLines", ge=1)
    max_process_tree_depth: int = Field(default=10, alias="maxProcessTreeDepth", ge=1)
    copy_dumps_default: bool = Field(default=False, alias="copyDumpsDefault")
    elevate_installers: bool = Field(
        default=True,
        alias="elevateInstallers",
        description="On Windows, use UAC elevation when the agent is not already admin",
    )
    gui_post_install_grace_seconds: int = Field(
        default=20,
        alias="guiPostInstallGraceSeconds",
        ge=0,
        description="Extra wait after GUI installer exits to capture late errors/logs",
    )
    max_installer_log_files: int = Field(default=40, alias="maxInstallerLogFiles", ge=1)
    installer_log_search_depth: int = Field(default=6, alias="installerLogSearchDepth", ge=1)
    auto_run_slm: bool = Field(default=True, alias="autoRunSlm")
    auto_monitor_enabled: bool = Field(
        default=True,
        alias="autoMonitorEnabled",
        description="Automatically detect and monitor installers launched outside Smart Installer",
    )
    background_poll_interval_seconds: int = Field(
        default=5,
        alias="backgroundPollIntervalSeconds",
        ge=2,
    )
    auto_monitor_max_process_age_seconds: int = Field(
        default=120,
        alias="autoMonitorMaxProcessAgeSeconds",
        ge=30,
        description="Only monitor installer processes started within this many seconds",
    )
    auto_monitor_cooldown_seconds: int = Field(
        default=600,
        alias="autoMonitorCooldownSeconds",
        ge=60,
        description="Do not re-monitor the same installer path until cooldown elapses",
    )
    auto_monitor_max_concurrent: int = Field(
        default=1,
        alias="autoMonitorMaxConcurrent",
        ge=1,
        le=3,
        description="Maximum simultaneous automatic monitoring sessions",
    )
    enable_windows_notifications: bool = Field(
        default=True,
        alias="enableWindowsNotifications",
    )
    minimize_to_tray: bool = Field(
        default=True,
        alias="minimizeToTray",
        description="Closing the window hides to system tray instead of exiting",
    )
    start_minimized_to_tray: bool = Field(
        default=False,
        alias="startMinimizedToTray",
        description="Start with dashboard hidden; tray icon only",
    )
    auto_start_at_login: bool = Field(
        default=False,
        alias="autoStartAtLogin",
        description="Register current user Run key to launch Smart Installer at logon",
    )
    slm_model: str = Field(default="phi3:mini", alias="slmModel")
    slm_embedding_model: str = Field(default="nomic-embed-text", alias="slmEmbeddingModel")
    slm_top_k: int = Field(default=2, alias="slmTopK", ge=1)
    slm_timeout_seconds: int = Field(default=300, alias="slmTimeoutSeconds", ge=1)
    rag_docs_directory: Path = Field(default=Path("rag_docs"), alias="ragDocsDirectory")
    monitored_filesystem_paths: list[str] = Field(
        default_factory=list, alias="monitoredFilesystemPaths"
    )
    registry_snapshot_keys: list[str] = Field(default_factory=list, alias="registrySnapshotKeys")

    model_config = SettingsConfigDict(
        populate_by_name=True,
        extra="forbid",
    )

    @field_validator(
        "installers_dir",
        "reports_dir",
        "logs_dir",
        "output_root",
        "sessions_summary_dir",
        "agent_log_path",
        "rag_docs_directory",
        mode="before",
    )
    @classmethod
    def expand_paths(cls, value: str | Path | None) -> Path | None:
        if value is None:
            return None
        expanded = Path(os.path.expandvars(str(value)))
        if expanded.is_absolute():
            return expanded.resolve()
        return (get_project_root() / expanded).resolve()


class ConfigProvider:
    """Loads and validates configuration from disk (MAINT-02)."""

    def __init__(self, config_path: Path | None = None) -> None:
        self._config_path = config_path
        self._config: SmartInstallConfig | None = None

    @property
    def config_path(self) -> Path:
        if self._config_path is not None:
            return self._config_path
        env_path = os.environ.get("SMARTINSTALL_CONFIG")
        if env_path:
            return Path(env_path).resolve()
        return self._default_config_path()

    def load(self) -> SmartInstallConfig:
        if self._config is not None:
            return self._config

        path = self.config_path
        if not path.is_file():
            raise FileNotFoundError(f"Configuration file not found: {path}")

        raw = json.loads(path.read_text(encoding="utf-8"))
        self._validate_config_version(raw)
        config = SmartInstallConfig.model_validate(raw)
        if config.sessions_summary_dir is None:
            config = config.model_copy(update={"sessions_summary_dir": config.output_root})
        self._config = config
        return self._config

    def reload(self) -> SmartInstallConfig:
        self._config = None
        return self.load()

    @staticmethod
    def _default_config_path() -> Path:
        import sys

        if getattr(sys, "frozen", False):
            exe_dir = Path(sys.executable).resolve().parent
            bundled = Path(getattr(sys, "_MEIPASS", exe_dir)) / "config" / "smartinstall.config.json"
            if bundled.is_file():
                return bundled
            exe_config = exe_dir / "config" / "smartinstall.config.json"
            if exe_config.is_file():
                return exe_config

        repo_config = Path(__file__).resolve().parents[4] / "config" / "smartinstall.config.json"
        if repo_config.is_file():
            return repo_config
        return Path(r"C:\ProgramData\SmartInstallAI\smartinstall.config.json")

    @staticmethod
    def _validate_config_version(raw: dict[str, Any]) -> None:
        version = raw.get("configVersion")
        if version != "1.0":
            raise ValueError(f"Unsupported configVersion: {version!r}; expected '1.0'")
