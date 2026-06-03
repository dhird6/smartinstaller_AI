"""Tests for automatic installer process detection heuristics."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

from smartinstall.agent.detection.installer_process_detector import InstallerProcessDetector
from smartinstall.agent.detection.user_installation_policy import (
    evaluate_user_installation,
    looks_like_user_installer_candidate,
)


@patch(
    "smartinstall.agent.detection.user_installation_policy._is_interactive_user",
    return_value=True,
)
def test_classify_setup_exe(_mock_interactive: object) -> None:
    detector = InstallerProcessDetector()
    result = detector._classify(  # noqa: SLF001
        100,
        {
            "name": "setup.exe",
            "exe": r"C:\Downloads\MyApp-setup.exe",
            "cmdline": [r"C:\Downloads\MyApp-setup.exe", "/S"],
            "ppid": os.getpid(),
            "create_time": __import__("time").time(),
        },
    )
    assert result is not None
    assert result.process_name == "setup.exe"


@patch(
    "smartinstall.agent.detection.user_installation_policy._is_interactive_user",
    return_value=True,
)
def test_classify_msiexec(_mock_interactive: object) -> None:
    detector = InstallerProcessDetector()
    result = detector._classify(  # noqa: SLF001
        200,
        {
            "name": "msiexec.exe",
            "exe": r"C:\Windows\System32\msiexec.exe",
            "cmdline": ["msiexec.exe", "/i", r"C:\Downloads\product.msi"],
            "ppid": os.getpid(),
            "create_time": __import__("time").time(),
        },
    )
    assert result is not None


def test_excludes_python() -> None:
    detector = InstallerProcessDetector()
    result = detector._classify(  # noqa: SLF001
        300,
        {
            "name": "python.exe",
            "exe": r"C:\Python311\python.exe",
            "cmdline": ["python.exe", "app.py"],
            "ppid": 1,
        },
    )
    assert result is None


def test_msi_in_downloads_is_candidate() -> None:
    assert looks_like_user_installer_candidate(
        "msiexec.exe",
        Path(r"C:\Windows\System32\msiexec.exe"),
        r"msiexec /i C:\Downloads\vendor.msi",
    )


@patch(
    "smartinstall.agent.detection.user_installation_policy._is_interactive_user",
    return_value=True,
)
def test_accepts_downloads_setup_policy(_mock_interactive: object) -> None:
    ok, reason = evaluate_user_installation(
        pid=os.getpid(),
        monitor_pid=os.getpid(),
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
