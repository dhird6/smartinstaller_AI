"""Shared pytest fixtures."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from smartinstall.agent.di.container import build_container
from smartinstall.agent.infrastructure.project_paths import get_project_root


@pytest.fixture
def temp_config(tmp_path: Path) -> Path:
    installers = tmp_path / "installers"
    reports = tmp_path / "reports"
    logs = tmp_path / "logs"
    sessions = tmp_path / "sessions"
    for directory in (installers, reports, logs, sessions):
        directory.mkdir(parents=True, exist_ok=True)

    config = {
        "configVersion": "1.0",
        "installersDirectory": str(installers),
        "reportsDirectory": str(reports),
        "logsDirectory": str(logs),
        "outputRoot": str(sessions),
        "agentLogPath": str(logs / "application.log"),
        "logLevel": "Info",
        "schemaVersion": "1.0",
        "agentVersion": "0.1.0",
        "minFreeDiskSpaceGb": 0.001,
        "defaultInstallerTimeoutSeconds": 1800,
        "collectorPreSnapshotTimeoutSeconds": 30,
        "collectorPostSnapshotTimeoutSeconds": 60,
        "maxFilesystemEvents": 10000,
        "maxEventLogEntries": 50000,
        "maxMsiLogSizeMb": 200,
        "maxStdoutStderrLines": 50000,
        "maxProcessTreeDepth": 10,
        "copyDumpsDefault": False,
        "elevateInstallers": False,
        "monitoredFilesystemPaths": [],
        "registrySnapshotKeys": [],
    }
    path = tmp_path / "smartinstall.config.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    return path


@pytest.fixture
def container(temp_config: Path):
    return build_container(temp_config)


@pytest.fixture
def sample_installer(tmp_path: Path) -> Path:
    installer = tmp_path / "setup.exe"
    installer.write_bytes(b"fake-installer")
    return installer


@pytest.fixture
def project_root() -> Path:
    return get_project_root()
