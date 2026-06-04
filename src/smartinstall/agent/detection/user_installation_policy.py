"""Decide whether a detected process is a user-initiated install (not OS/background)."""

from __future__ import annotations

import os
import time
from pathlib import Path

import psutil
import structlog

logger = structlog.get_logger(__name__)

# Strict name tokens for automatic detection (no broad "update"/"patch").
_USER_INSTALLER_NAME_TOKENS = (
    "setup",
    "install",
    "installer",
    "unins",
    "uninstall",
    "bootstrap",
    "deploy",
)

_BACKGROUND_PROCESS_NAMES = frozenset(
    {
        "trustedinstaller.exe",
        "tiworker.exe",
        "wuauclt.exe",
        "usoclient.exe",
        "uhssvc.exe",
        "musnotification.exe",
        "musnotificationux.exe",
        "sedlauncher.exe",
        "sedsvc.exe",
        "omadmclient.exe",
        "devicecensus.exe",
        "taskeng.exe",
        "taskhostw.exe",
        "sppsvc.exe",
        "searchindexer.exe",
        "wermgr.exe",
        "wsappx.exe",
        "appinstaller.exe",
    }
)

_BACKGROUND_PARENT_NAMES = frozenset(
    {
        "services.exe",
        "svchost.exe",
        "trustedinstaller.exe",
        "wuauclt.exe",
        "usoclient.exe",
        "tiworker.exe",
        "taskeng.exe",
        "taskhostw.exe",
        "msiexec.exe",
        "runtimebroker.exe",
        "sihost.exe",
        "wininit.exe",
        "spoolsv.exe",
    }
)

_USER_LAUNCH_PARENT_NAMES = frozenset(
    {
        "explorer.exe",
        "openwith.exe",
        "chrome.exe",
        "firefox.exe",
        "msedge.exe",
        "brave.exe",
        "opera.exe",
        "vivaldi.exe",
        "winrar.exe",
        "7zfm.exe",
        "totalcmd.exe",
        "doublecmd.exe",
    }
)

_SYSTEM_ACCOUNT_MARKERS = (
    "SYSTEM",
    "LOCAL SERVICE",
    "NETWORK SERVICE",
    "NT AUTHORITY",
    "SERVICE R",
)

_SYSTEM_PATH_MARKERS = (
    "\\windows\\installer\\",
    "\\winsxs\\",
    "\\windows\\temp\\",
    "\\windows\\ccm\\",
    "\\windows\\ccmcache\\",
    "\\programdata\\package cache\\",
    "\\program files\\windowsapps\\",
    "\\windows\\system32\\",
    "\\windows\\syswow64\\",
)

_SILENT_MSI_FLAGS = ("/qn", "/qb", "/quiet", "/passive", "-qn", "-quiet")

# Paths where background apps commonly auto-update (not user double-click installs).
_BACKGROUND_INSTALL_PATH_MARKERS = (
    "\\program files\\",
    "\\program files (x86)\\",
    "\\appdata\\local\\programs\\",
    "\\appdata\\roaming\\",
)


def evaluate_user_installation(
    *,
    pid: int,
    monitor_pid: int,
    process_name: str,
    installer_path: Path | None,
    executable_path: Path | None,
    command_line: str | None,
    parent_chain: tuple[str, ...],
    via_msiexec: bool,
    process_create_time: float | None,
    max_process_age_seconds: float,
) -> tuple[bool, str]:
    """
    Return (should_monitor, rejection_reason).

    Only user-driven installs (Explorer, Downloads, etc.) should be monitored.
    """
    if not _is_interactive_user(pid):
        return False, "non-interactive account (SYSTEM/service)"

    if _chain_has_background_actor(parent_chain, process_name):
        return False, "background maintenance parent chain"

    target = installer_path or executable_path
    if target is None:
        return False, "no installer path"

    path_lower = str(target).lower()
    if _is_system_managed_path(path_lower) and not _is_user_content_path(path_lower):
        return False, "system-managed install location"

    if via_msiexec or process_name == "msiexec.exe":
        ok, reason = _evaluate_msiexec(command_line, parent_chain)
        if not ok:
            return False, reason

    if process_create_time is not None:
        age = time.time() - process_create_time
        if age > max_process_age_seconds:
            return False, f"process too old ({int(age)}s)"

    if not _has_user_launch_signal(parent_chain, path_lower):
        return False, "not launched by user (Explorer/browser/file manager)"

    return True, "user-initiated"


def looks_like_user_installer_candidate(
    process_name: str,
    exe_path: Path | None,
    command_line: str | None,
    *,
    parent_chain: tuple[str, ...] = (),
) -> bool:
    """Narrow pattern match before chain resolution (automatic mode only)."""
    name = process_name.lower()
    if name in _BACKGROUND_PROCESS_NAMES:
        return False

    parents = {p.lower() for p in parent_chain}
    user_launched = bool(parents.intersection(_USER_LAUNCH_PARENT_NAMES))

    if exe_path is not None and exe_path.suffix.lower() in {".exe", ".msi"}:
        path_lower = str(exe_path).lower()
        if _is_user_pickup_location(path_lower):
            return user_launched
        stem_lower = exe_path.stem.lower()
        if any(token in stem_lower for token in _USER_INSTALLER_NAME_TOKENS):
            return user_launched
        if exe_path.suffix.lower() == ".msi":
            return user_launched
        if user_launched and _is_direct_user_launch(parent_chain):
            return True

    if name == "msiexec.exe":
        combined = (command_line or "").lower()
        if "/i" not in combined and "-i" not in combined:
            return False
        if ".msi" not in combined:
            return False
        if _is_silent_msi(combined) and not user_launched:
            return False
        return user_launched

    combined = f"{name} {exe_path or ''} {command_line or ''}".lower()
    if not any(token in combined for token in _USER_INSTALLER_NAME_TOKENS):
        return False
    if ".exe" not in combined and ".msi" not in combined:
        return False
    return user_launched


def _evaluate_msiexec(command_line: str | None, parent_chain: tuple[str, ...]) -> tuple[bool, str]:
    cmd = (command_line or "").lower()
    if "/i" not in cmd and "-i" not in cmd:
        return False, "msiexec without install (/i) flag"
    if "/x" in cmd or "/f" in cmd:
        return False, "msiexec maintenance/uninstall mode"
    parents_lower = {p.lower() for p in parent_chain}
    if _is_silent_msi(cmd) and not parents_lower.intersection(_USER_LAUNCH_PARENT_NAMES):
        return False, "silent MSI without user parent"
    if parents_lower.intersection(_BACKGROUND_PARENT_NAMES) and not parents_lower.intersection(
        _USER_LAUNCH_PARENT_NAMES
    ):
        return False, "MSI spawned by background service"
    return True, "ok"


def _is_silent_msi(cmd: str) -> bool:
    return any(flag in cmd for flag in _SILENT_MSI_FLAGS)


def _is_interactive_user(pid: int) -> bool:
    try:
        username = psutil.Process(pid).username() or ""
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False
    upper = username.upper()
    return not any(marker in upper for marker in _SYSTEM_ACCOUNT_MARKERS)


def _chain_has_background_actor(parent_chain: tuple[str, ...], process_name: str) -> bool:
    names = {process_name.lower(), *(p.lower() for p in parent_chain)}
    if names.intersection(_BACKGROUND_PROCESS_NAMES):
        return True
    if names.intersection(_BACKGROUND_PARENT_NAMES) and not names.intersection(
        _USER_LAUNCH_PARENT_NAMES
    ):
        return True
    return False


def _has_user_launch_signal(parent_chain: tuple[str, ...], installer_path_lower: str) -> bool:
    """Require a user shell launch and an installer-like target (not every background .exe)."""
    parents = {p.lower() for p in parent_chain}
    if not parents.intersection(_USER_LAUNCH_PARENT_NAMES):
        return False

    if _is_background_install_path(installer_path_lower):
        return False

    if _is_direct_user_launch(parent_chain):
        return installer_path_lower.endswith((".exe", ".msi"))

    if _is_user_pickup_location(installer_path_lower):
        return True

    if _has_installer_name_tokens(installer_path_lower):
        return True

    if installer_path_lower.endswith(".msi"):
        return True

    return False


def _is_direct_user_launch(parent_chain: tuple[str, ...]) -> bool:
    if not parent_chain:
        return False
    return parent_chain[0].lower() in _USER_LAUNCH_PARENT_NAMES


def _is_user_pickup_location(path_lower: str) -> bool:
    """Downloads/Desktop/Documents/Temp only — not the entire user profile tree."""
    for root in _user_profile_roots():
        marker = str(root).lower()
        if not marker or marker not in path_lower:
            continue
        for sub in (
            "\\downloads\\",
            "\\desktop\\",
            "\\documents\\",
            "\\appdata\\local\\temp\\",
            "\\temp\\",
        ):
            if sub in path_lower:
                return True
    return False


def _has_installer_name_tokens(path_lower: str) -> bool:
    name = Path(path_lower).name.lower()
    return any(token in name for token in _USER_INSTALLER_NAME_TOKENS)


def _is_background_install_path(path_lower: str) -> bool:
    return any(marker in path_lower for marker in _BACKGROUND_INSTALL_PATH_MARKERS)


def _is_system_managed_path(path_lower: str) -> bool:
    return any(marker in path_lower for marker in _SYSTEM_PATH_MARKERS)


def _user_profile_roots() -> list[Path]:
    roots: list[Path] = []
    profile = os.environ.get("USERPROFILE")
    if profile:
        roots.append(Path(profile))
    return roots
