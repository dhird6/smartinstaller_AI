"""Tests for user-initiated-only installation policy."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from smartinstall.agent.detection.user_installation_policy import (
    evaluate_user_installation,
    looks_like_user_installer_candidate,
)


def test_rejects_windows_update_style_path() -> None:
    ok, reason = evaluate_user_installation(
        pid=99999,
        monitor_pid=99999,
        process_name="msiexec.exe",
        installer_path=Path(r"C:\Windows\Installer\abc.msi"),
        executable_path=Path(r"C:\Windows\System32\msiexec.exe"),
        command_line=r'msiexec /i C:\Windows\Installer\abc.msi /qn',
        parent_chain=("services.exe", "svchost.exe"),
        via_msiexec=True,
        process_create_time=None,
        max_process_age_seconds=120,
    )
    assert ok is False
    assert "system" in reason.lower() or "background" in reason.lower() or "silent" in reason.lower()


@patch(
    "smartinstall.agent.detection.user_installation_policy._is_interactive_user",
    return_value=True,
)
def test_accepts_downloads_setup(_mock_interactive: object) -> None:
    ok, reason = evaluate_user_installation(
        pid=99998,
        monitor_pid=99998,
        process_name="setup.exe",
        installer_path=Path(r"C:\Downloads\MyApp-setup.exe"),
        executable_path=Path(r"C:\Downloads\MyApp-setup.exe"),
        command_line=r"C:\Downloads\MyApp-setup.exe",
        parent_chain=("explorer.exe",),
        via_msiexec=False,
        process_create_time=__import__("time").time(),
        max_process_age_seconds=120,
    )
    assert ok is True
    assert reason == "user-initiated"


def test_rejects_broad_update_token() -> None:
    assert looks_like_user_installer_candidate(
        "update.exe",
        Path(r"C:\Program Files\Vendor\update.exe"),
        None,
    ) is False


def test_accepts_msiexec_with_install_flag_in_downloads() -> None:
    assert looks_like_user_installer_candidate(
        "msiexec.exe",
        Path(r"C:\Windows\System32\msiexec.exe"),
        r'msiexec.exe /i C:\Users\Public\Downloads\app.msi',
    ) is True
