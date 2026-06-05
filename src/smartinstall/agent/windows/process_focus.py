"""Bring an installer process window to the foreground on Windows."""

from __future__ import annotations

import sys
import time


def focus_process_window(
    *,
    process_name: str,
    title_hint: str | None = None,
    timeout_seconds: float = 25.0,
    poll_interval_seconds: float = 0.4,
) -> bool:
    """
    Try to foreground the main window owned by *process_name* (e.g. TestAppSetup.exe).

    Returns True when a matching window was focused.
    """
    if sys.platform != "win32":
        return False

    normalized = process_name.lower()
    if not normalized.endswith(".exe"):
        normalized = f"{normalized}.exe"

    deadline = time.monotonic() + max(1.0, timeout_seconds)
    while time.monotonic() < deadline:
        if _focus_matching_window(normalized, title_hint=title_hint):
            return True
        time.sleep(poll_interval_seconds)
    return False


def _focus_matching_window(process_name: str, *, title_hint: str | None) -> bool:
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    matches: list[int] = []

    def _enum_proc(hwnd: int, _lparam: int) -> bool:
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, length + 1)
        title = buffer.value.strip()
        if title_hint and title_hint.lower() not in title.lower():
            return True

        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if int(pid.value) <= 0:
            return True

        handle = kernel32.OpenProcess(0x1000, False, pid.value)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return True
        try:
            exe_name = _query_image_name(handle, kernel32)
        finally:
            kernel32.CloseHandle(handle)

        if exe_name and exe_name.lower() == process_name:
            matches.append(hwnd)
        return True

    user32.EnumWindows(WNDENUMPROC(_enum_proc), 0)
    if not matches:
        return False

    hwnd = matches[0]
    user32.ShowWindow(hwnd, 9)  # SW_RESTORE
    user32.SetForegroundWindow(hwnd)
    return True


def _query_image_name(process_handle: int, kernel32) -> str | None:
    import ctypes
    from ctypes import wintypes

    try:
        is_wow64 = wintypes.BOOL()
        if not kernel32.IsWow64Process(process_handle, ctypes.byref(is_wow64)):
            return None
        if bool(is_wow64.value):
            return None
    except (AttributeError, OSError):
        pass

    size = wintypes.DWORD(32768)
    buffer = ctypes.create_unicode_buffer(size.value)
    if not kernel32.QueryFullProcessImageNameW(process_handle, 0, buffer, ctypes.byref(size)):
        return None
    from pathlib import Path

    return Path(buffer.value).name
