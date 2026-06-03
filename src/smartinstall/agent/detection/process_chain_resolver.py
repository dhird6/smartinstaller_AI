"""Resolve installer root PID and package path across MSI, UAC, and wrapper chains."""

from __future__ import annotations

import os
import re
import shlex
from dataclasses import dataclass, field
from pathlib import Path

import psutil
import structlog

logger = structlog.get_logger(__name__)

_MSI_PATH_RE = re.compile(r"\.msi\b", re.IGNORECASE)
_UAC_PARENT_NAMES = frozenset(
    {
        "consent.exe",
        "dllhost.exe",
        "werfault.exe",
        "applicationframehost.exe",
    }
)
_SETUP_TOKENS = ("setup", "install", "update", "patch", "bootstrap", "deploy", "unins")
_MAX_CHAIN_DEPTH = 16


@dataclass(slots=True, frozen=True)
class ProcessChainContext:
    """Normalized installer target after parent-chain analysis."""

    pid: int
    monitor_pid: int
    process_name: str
    executable_path: Path | None
    command_line: str | None
    installer_path: Path | None
    installer_type: str
    parent_chain: tuple[str, ...] = ()
    elevation_detected: bool = False
    via_msiexec: bool = False
    chain_summary: str = ""


def resolve_installer_chain(pid: int) -> ProcessChainContext | None:
    """Walk ancestors and siblings to find the true installer package and monitor PID."""
    try:
        proc = psutil.Process(pid)
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return None

    chain: list[tuple[int, str, str | None, list[str] | None]] = []
    current: psutil.Process | None = proc
    depth = 0
    elevation = False

    while current is not None and depth < _MAX_CHAIN_DEPTH:
        try:
            name = current.name().lower()
            cmd_parts = current.cmdline() or []
            cmdline = " ".join(cmd_parts) if cmd_parts else None
            exe = _safe_exe(current)
            chain.append((current.pid, name, cmdline, cmd_parts))
            if name in _UAC_PARENT_NAMES or name == "consent.exe":
                elevation = True
            current = _safe_parent(current)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            break
        depth += 1

    if not chain:
        return None

    anchor_pid, anchor_name, anchor_cmd, anchor_parts = chain[0]
    parent_names = tuple(entry[1] for entry in chain[1:])

    msi_path = _extract_msi_path(anchor_parts or [], anchor_cmd)
    if anchor_name == "msiexec.exe" or msi_path is not None:
        return _build_msi_context(
            chain=chain,
            msi_path=msi_path,
            elevation=elevation,
            parent_names=parent_names,
        )

    setup_entry = _find_setup_entry(chain)
    if setup_entry is not None:
        setup_pid, setup_name, setup_cmd, setup_parts = setup_entry
        wrapped_msi = _extract_msi_path(setup_parts or [], setup_cmd)
        if wrapped_msi is not None:
            return _build_msi_context(
                chain=chain,
                msi_path=wrapped_msi,
                elevation=elevation,
                parent_names=parent_names,
                wrapper_pid=setup_pid,
            )
        exe_path = _path_from_chain_entry(setup_pid, setup_name, setup_cmd)
        if exe_path is not None and exe_path.suffix.lower() in {".exe", ".msi"}:
            return ProcessChainContext(
                pid=setup_pid,
                monitor_pid=setup_pid,
                process_name=setup_name,
                executable_path=exe_path,
                command_line=setup_cmd,
                installer_path=exe_path,
                installer_type="MSI" if exe_path.suffix.lower() == ".msi" else "EXE",
                parent_chain=parent_names,
                elevation_detected=elevation,
                via_msiexec=False,
                chain_summary=_format_chain(chain),
            )

    exe_path = _path_from_chain_entry(anchor_pid, anchor_name, anchor_cmd)
    if exe_path is None:
        return None

    return ProcessChainContext(
        pid=anchor_pid,
        monitor_pid=anchor_pid,
        process_name=anchor_name,
        executable_path=exe_path,
        command_line=anchor_cmd,
        installer_path=exe_path,
        installer_type="MSI" if exe_path.suffix.lower() == ".msi" else "EXE",
        parent_chain=parent_names,
        elevation_detected=elevation,
        via_msiexec=False,
        chain_summary=_format_chain(chain),
    )


def _build_msi_context(
    *,
    chain: list[tuple[int, str, str | None, list[str] | None]],
    msi_path: Path | None,
    elevation: bool,
    parent_names: tuple[str, ...],
    wrapper_pid: int | None = None,
) -> ProcessChainContext | None:
    msiexec_entry = next((e for e in chain if e[1] == "msiexec.exe"), chain[0])
    msi_pid, msi_name, msi_cmd, _ = msiexec_entry
    if msi_path is None or not msi_path.is_file():
        msi_path = _guess_msi_from_chain(chain)

    if msi_path is None:
        return None

    root_pid = wrapper_pid or msi_pid
    return ProcessChainContext(
        pid=root_pid,
        monitor_pid=msi_pid,
        process_name=msi_name,
        executable_path=Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "msiexec.exe",
        command_line=msi_cmd,
        installer_path=msi_path.resolve(),
        installer_type="MSI",
        parent_chain=parent_names,
        elevation_detected=elevation,
        via_msiexec=True,
        chain_summary=_format_chain(chain),
    )


def _find_setup_entry(
    chain: list[tuple[int, str, str | None, list[str] | None]],
) -> tuple[int, str, str | None, list[str] | None] | None:
    for entry in chain:
        name = entry[1]
        if name == "msiexec.exe":
            continue
        if any(token in name for token in _SETUP_TOKENS):
            return entry
        cmd = entry[2] or ""
        if _MSI_PATH_RE.search(cmd) or ".exe" in cmd.lower():
            if any(token in cmd.lower() for token in _SETUP_TOKENS):
                return entry
    return chain[0] if chain else None


def _extract_msi_path(parts: list[str], cmdline: str | None) -> Path | None:
    for part in parts:
        if _MSI_PATH_RE.search(part):
            candidate = part.strip('"')
            path = Path(candidate)
            if path.suffix.lower() == ".msi":
                return path
    if cmdline:
        for match in re.finditer(r'"([^"]+\.msi)"|(\S+\.msi)', cmdline, re.IGNORECASE):
            raw = match.group(1) or match.group(2)
            if raw:
                return Path(raw.strip('"'))
    return None


def _guess_msi_from_chain(
    chain: list[tuple[int, str, str | None, list[str] | None]],
) -> Path | None:
    for _, _, cmd, parts in chain:
        found = _extract_msi_path(parts or [], cmd)
        if found is not None and found.is_file():
            return found
    return None


def _path_from_chain_entry(pid: int, name: str, cmdline: str | None) -> Path | None:
    try:
        exe = psutil.Process(pid).exe()
        if exe:
            path = Path(exe)
            if path.is_file():
                return path.resolve()
    except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
        pass
    if cmdline:
        try:
            parts = shlex.split(cmdline, posix=False)
        except ValueError:
            parts = cmdline.split()
        if parts:
            candidate = Path(parts[0].strip('"'))
            if candidate.is_file():
                return candidate.resolve()
    return None


def _safe_parent(proc: psutil.Process) -> psutil.Process | None:
    try:
        parent = proc.parent()
        return parent
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return None


def _safe_exe(proc: psutil.Process) -> str | None:
    try:
        return proc.exe()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return None


def _format_chain(chain: list[tuple[int, str, str | None, list[str] | None]]) -> str:
    labels = [f"{name}({pid})" for pid, name, _, _ in chain[:6]]
    return " → ".join(labels)
