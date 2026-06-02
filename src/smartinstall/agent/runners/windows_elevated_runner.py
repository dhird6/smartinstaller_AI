"""Launch installers elevated via UAC (ShellExecute runas)."""

from __future__ import annotations

import ctypes
import os
import subprocess
import time
from ctypes import wintypes
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)

SEE_MASK_NOCLOSEPROCESS = 0x00000040
SW_HIDE = 0
WAIT_OBJECT_0 = 0x00000000
WAIT_TIMEOUT = 0x00000102
STILL_ACTIVE = 259
ERROR_CANCELLED = 1223


class _SHELLEXECUTEINFOW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("fMask", ctypes.c_ulong),
        ("hwnd", wintypes.HWND),
        ("lpVerb", wintypes.LPCWSTR),
        ("lpFile", wintypes.LPCWSTR),
        ("lpParameters", wintypes.LPCWSTR),
        ("lpDirectory", wintypes.LPCWSTR),
        ("nShow", ctypes.c_int),
        ("hInstApp", wintypes.HINSTANCE),
        ("lpIDList", ctypes.c_void_p),
        ("lpClass", wintypes.LPCWSTR),
        ("hkeyClass", wintypes.HKEY),
        ("dwHotKey", wintypes.DWORD),
        ("hMonitor", wintypes.HANDLE),
        ("hProcess", wintypes.HANDLE),
    ]


def run_elevated(
    command: list[str],
    *,
    working_directory: str,
    timeout_seconds: int,
) -> tuple[int, int, bool]:
    """
    Launch *command* with the runas verb (UAC elevation).

    Returns (exit_code, process_id, timed_out).
    """
    if os.name != "nt":
        raise OSError("Elevated launch is only supported on Windows")

    executable = command[0]
    parameters = subprocess.list2cmdline(command[1:]) if len(command) > 1 else ""

    info = _SHELLEXECUTEINFOW()
    info.cbSize = ctypes.sizeof(info)
    info.fMask = SEE_MASK_NOCLOSEPROCESS
    info.lpVerb = "runas"
    info.lpFile = executable
    info.lpParameters = parameters
    info.lpDirectory = working_directory
    info.nShow = SW_HIDE

    if not ctypes.windll.shell32.ShellExecuteExW(ctypes.byref(info)):
        raise ctypes.WinError()

    if info.hInstApp is not None and int(info.hInstApp) <= 32:
        error_code = int(info.hInstApp)
        if error_code == ERROR_CANCELLED:
            raise PermissionError("UAC elevation was cancelled by the user")
        raise OSError(f"ShellExecuteEx failed with code {error_code}")

    if not info.hProcess:
        raise OSError("Elevated process handle was not returned")

    kernel32 = ctypes.windll.kernel32
    pid = int(kernel32.GetProcessId(info.hProcess))
    logger.info("elevated_installer_launched", pid=pid, executable=executable)

    wait_ms = timeout_seconds * 1000
    timed_out = False
    wait_result = kernel32.WaitForSingleObject(info.hProcess, wait_ms)
    if wait_result == WAIT_TIMEOUT:
        timed_out = True
        kernel32.TerminateProcess(info.hProcess, 1)
        exit_code = 1
    else:
        exit_code_dword = wintypes.DWORD()
        if not kernel32.GetExitCodeProcess(info.hProcess, ctypes.byref(exit_code_dword)):
            raise ctypes.WinError()
        exit_code = int(exit_code_dword.value)
        if exit_code == STILL_ACTIVE:
            exit_code = 1

    kernel32.CloseHandle(info.hProcess)
    return exit_code, pid, timed_out


def write_elevated_stream_placeholders(stdout_path: Path, stderr_path: Path) -> None:
    note = (
        "Installer was launched with UAC elevation (runas).\n"
        "STDOUT/STDERR stream capture is not available for elevated child processes.\n"
        "Review installation_failure_report.json, MSI verbose log, and Windows Event Logs.\n"
    )
    stdout_path.write_text(note, encoding="utf-8")
    stderr_path.write_text(note, encoding="utf-8")
