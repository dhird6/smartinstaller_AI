"""Regression: elevated install path must forward event_collector."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from smartinstall.agent.infrastructure.config_provider import SmartInstallConfig
from smartinstall.agent.runners.installer_runner import InstallerRunner
from smartinstall.core.enums.installation import InstallerType


@pytest.fixture
def runner(tmp_path: Path) -> InstallerRunner:
    config = SmartInstallConfig.model_construct(
        agent_version="test",
        installers_dir=tmp_path / "installers",
        output_root=tmp_path / "out",
        reports_dir=tmp_path / "reports",
        logs_dir=tmp_path / "logs",
        elevate_installers=True,
    )
    return InstallerRunner(config)


def test_run_elevated_receives_event_collector(runner: InstallerRunner, tmp_path: Path) -> None:
    installer = tmp_path / "setup.exe"
    installer.write_bytes(b"")
    session_dir = tmp_path / "session"
    event_collector = MagicMock()

    with (
        patch(
            "smartinstall.agent.runners.installer_runner.is_user_admin",
            return_value=False,
        ),
        patch.object(runner, "_run_elevated") as mock_elevated,
    ):
        mock_elevated.return_value = MagicMock(
            pid=1234,
            parent_pid=1,
            command_line="setup.exe",
            start_timestamp="2026-01-01T00:00:00.000Z",
            end_timestamp="2026-01-01T00:00:01.000Z",
            exit_code=0,
            timed_out=False,
            stdout_path=session_dir / "stdout.log",
            stderr_path=session_dir / "stderr.log",
        )
        runner.run(
            installer_path=installer,
            installer_type=InstallerType.EXE,
            session_directory=session_dir,
            additional_args=None,
            timeout_seconds=60,
            event_collector=event_collector,
        )

    mock_elevated.assert_called_once()
    assert mock_elevated.call_args.kwargs["event_collector"] is event_collector
