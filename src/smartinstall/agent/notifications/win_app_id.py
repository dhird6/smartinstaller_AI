"""Windows App User Model ID for toast notifications."""

from __future__ import annotations

import sys

WINDOWS_TOAST_APP_ID = "CCTech.SmartInstallAI"
_registered = False


def ensure_windows_toast_app_id() -> None:
    """Register AUMID so WinRT toasts display for this process."""
    global _registered  # noqa: PLW0603
    if _registered or sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(WINDOWS_TOAST_APP_ID)
        _registered = True
    except OSError:
        pass
