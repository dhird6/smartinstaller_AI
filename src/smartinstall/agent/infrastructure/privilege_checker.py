"""Windows privilege detection (SEC-01, api-contracts SESSION_INSUFFICIENT_PRIVILEGES)."""

from __future__ import annotations

import os
import sys


def is_user_admin() -> bool:
    """Return True if the current process has administrator privileges (Windows)."""
    if os.name != "nt":
        return os.geteuid() == 0 if hasattr(os, "geteuid") else False

    try:
        import ctypes

        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def admin_status_message() -> str:
    if is_user_admin():
        return "Running with administrator privileges."
    return (
        "Not running as administrator. Installers that require elevation will trigger a "
        "UAC prompt, or you can restart PowerShell with 'Run as administrator'."
    )
