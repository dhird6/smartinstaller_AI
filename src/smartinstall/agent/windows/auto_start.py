"""Windows login auto-start via CurrentUser Run registry key."""

from __future__ import annotations

import sys
from pathlib import Path

_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_VALUE_NAME = "SmartInstallAI"


def is_auto_start_enabled() -> bool:
    if sys.platform != "win32":
        return False
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_READ) as key:
            winreg.QueryValueEx(key, _VALUE_NAME)
        return True
    except OSError:
        return False


def enable_auto_start(*, tray_only: bool = True) -> None:
    """Register Smart Installer to start at user logon."""
    if sys.platform != "win32":
        raise OSError("Auto-start is only supported on Windows")

    import winreg

    command = _build_launch_command(tray_only=tray_only)
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, _VALUE_NAME, 0, winreg.REG_SZ, command)


def disable_auto_start() -> None:
    if sys.platform != "win32":
        return
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, _VALUE_NAME)
    except OSError:
        pass


def _build_launch_command(*, tray_only: bool) -> str:
    """Build a safe, quoted launch command for the Run key."""
    project_root = Path(__file__).resolve().parents[4]
    desktop_script = project_root / "desktop.py"
    if desktop_script.is_file():
        launcher = f'"{sys.executable}" "{desktop_script}"'
    else:
        launcher = f'"{sys.executable}" -m smartinstall.ui.main'
    if tray_only:
        return f"{launcher} --tray"
    return launcher
