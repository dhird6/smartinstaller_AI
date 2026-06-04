"""Tests for launch-based installer detection (Explorer parent required)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from smartinstall.agent.detection.installation_launch_detector import (
    _classify_launch_type,
    _chain_includes_user_shell_names,
)


def test_direct_explorer_launch() -> None:
    assert _classify_launch_type("explorer.exe", ("explorer.exe",)) == "direct"


def test_rejects_svchost_parent() -> None:
    assert _classify_launch_type("svchost.exe", ("svchost.exe", "services.exe")) is None


def test_uac_with_explorer_above() -> None:
    assert _classify_launch_type("consent.exe", ("consent.exe", "explorer.exe")) == "uac"


def test_chain_includes_explorer() -> None:
    assert _chain_includes_user_shell_names(("setup.exe", "explorer.exe")) is True


@patch("smartinstall.agent.detection.installation_launch_detector.psutil")
@patch(
    "smartinstall.agent.detection.installation_launch_detector._is_interactive_user",
    return_value=True,
)
def test_detects_new_explorer_launched_setup(
    mock_interactive: object,
    mock_psutil: MagicMock,
    tmp_path,
) -> None:
    from smartinstall.agent.detection.installation_launch_detector import InstallationLaunchDetector

    installer = tmp_path / "app-setup.exe"
    installer.write_bytes(b"fake")

    explorer = MagicMock()
    explorer.pid = 100
    explorer.name.return_value = "explorer.exe"
    explorer.parent.return_value = None

    setup = MagicMock()
    setup.pid = 500
    setup.name.return_value = "setup.exe"
    setup.exe.return_value = str(installer)
    setup.cmdline.return_value = [str(installer)]
    setup.parent.return_value = explorer

    mock_psutil.Process.side_effect = lambda pid: explorer if pid == 100 else setup
    mock_psutil.process_iter.return_value = [
        MagicMock(
            info={
                "pid": 500,
                "name": "setup.exe",
                "exe": str(installer),
                "cmdline": [str(installer)],
                "ppid": 100,
                "create_time": __import__("time").time(),
            }
        )
    ]

    detector = InstallationLaunchDetector(max_launch_age_seconds=120.0)
    found = detector.scan_new_launches()
    assert len(found) == 1
    assert found[0].installer_path == installer.resolve()
