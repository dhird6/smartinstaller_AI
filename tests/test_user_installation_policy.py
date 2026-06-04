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


@patch(
    "smartinstall.agent.detection.user_installation_policy._is_interactive_user",
    return_value=True,
)
def test_rejects_profile_path_without_explorer_launch(_mock_interactive: object) -> None:
    ok, reason = evaluate_user_installation(
        pid=99996,
        monitor_pid=99996,
        process_name="helper.exe",
        installer_path=Path(r"C:\Users\Test\AppData\Local\SomeApp\helper.exe"),
        executable_path=Path(r"C:\Users\Test\AppData\Local\SomeApp\helper.exe"),
        command_line=r"C:\Users\Test\AppData\Local\SomeApp\helper.exe",
        parent_chain=("sihost.exe",),
        via_msiexec=False,
        process_create_time=__import__("time").time(),
        max_process_age_seconds=120,
    )
    assert ok is False


@patch(
    "smartinstall.agent.detection.user_installation_policy._is_interactive_user",
    return_value=True,
)
def test_rejects_broad_update_token_without_user_launch(_mock_interactive: object) -> None:
    ok, reason = evaluate_user_installation(
        pid=99997,
        monitor_pid=99997,
        process_name="update.exe",
        installer_path=Path(r"C:\Program Files\Vendor\update.exe"),
        executable_path=Path(r"C:\Program Files\Vendor\update.exe"),
        command_line=r"C:\Program Files\Vendor\update.exe",
        parent_chain=("services.exe", "svchost.exe"),
        via_msiexec=False,
        process_create_time=__import__("time").time(),
        max_process_age_seconds=120,
    )
    assert ok is False
    assert reason


def test_accepts_msiexec_with_install_flag_in_downloads() -> None:
    assert looks_like_user_installer_candidate(
        "msiexec.exe",
        Path(r"C:\Windows\System32\msiexec.exe"),
        r'msiexec.exe /i C:\Users\Public\Downloads\app.msi',
        parent_chain=("explorer.exe",),
    ) is True
