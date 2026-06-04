"""Detect user-initiated installer processes (Explorer / Downloads), not background OS installs."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path

import psutil
import structlog

from smartinstall.agent.detection.process_chain_resolver import (
    _extract_msi_path,
    resolve_installer_chain,
)
from smartinstall.agent.detection.user_installation_policy import (
    evaluate_user_installation,
    looks_like_user_installer_candidate,
)

logger = structlog.get_logger(__name__)

_EXCLUDED_PROCESS_NAMES = frozenset(
    {
        "python.exe",
        "pythonw.exe",
        "smartinstallai.exe",
        "cursor.exe",
        "code.exe",
        "explorer.exe",
        "cmd.exe",
        "powershell.exe",
        "pwsh.exe",
        "conhost.exe",
        "svchost.exe",
        "dllhost.exe",
        "searchhost.exe",
        "runtimebroker.exe",
        "trustedinstaller.exe",
        "tiworker.exe",
        "wuauclt.exe",
        "usoclient.exe",
        "taskeng.exe",
        "taskhostw.exe",
    }
)


@dataclass(slots=True, frozen=True)
class DetectedInstallerProcess:
    pid: int
    process_name: str
    executable_path: Path | None
    command_line: str | None
    parent_process_name: str | None
    monitor_pid: int | None = None
    installer_path: Path | None = None
    installer_type: str | None = None
    elevation_detected: bool = False
    via_msiexec: bool = False
    chain_summary: str = ""
    launch_id: str = ""


class InstallerProcessDetector:
    """Scans for user-launched installers only (strict; excludes background/OS updates)."""

    def __init__(
        self,
        *,
        exclude_pids: frozenset[int] | None = None,
        max_process_age_seconds: float = 120.0,
    ) -> None:
        self._exclude_pids = exclude_pids or frozenset()
        self._own_pid = os.getpid()
        self._max_process_age_seconds = max_process_age_seconds

    def scan(self) -> list[DetectedInstallerProcess]:
        seen_monitor: set[int] = set()
        seen_packages: set[str] = set()
        detected: list[DetectedInstallerProcess] = []

        for proc in psutil.process_iter(
            ["pid", "name", "exe", "cmdline", "ppid", "create_time"]
        ):
            try:
                info = proc.info
                pid = int(info["pid"])
            except (TypeError, ValueError, psutil.NoSuchProcess):
                continue
            if pid == self._own_pid or pid in self._exclude_pids:
                continue

            candidate = self._classify(pid, info)
            if candidate is None:
                continue

            monitor_key = candidate.monitor_pid or candidate.pid
            package_key = str(candidate.installer_path or candidate.executable_path or monitor_key)
            if monitor_key in seen_monitor or package_key in seen_packages:
                continue

            seen_monitor.add(monitor_key)
            seen_packages.add(package_key)
            detected.append(candidate)

        return detected

    def _classify(self, pid: int, info: dict) -> DetectedInstallerProcess | None:
        name = (info.get("name") or "").lower()
        if name in _EXCLUDED_PROCESS_NAMES:
            return None

        create_time = info.get("create_time")
        chain_ctx = resolve_installer_chain(pid)

        if chain_ctx is not None and chain_ctx.installer_path is not None:
            parent_chain = chain_ctx.parent_chain
            parent_name = parent_chain[0] if parent_chain else None
            candidate = DetectedInstallerProcess(
                pid=chain_ctx.pid,
                process_name=chain_ctx.process_name,
                executable_path=chain_ctx.executable_path,
                command_line=chain_ctx.command_line,
                parent_process_name=parent_name,
                monitor_pid=chain_ctx.monitor_pid,
                installer_path=chain_ctx.installer_path,
                installer_type=chain_ctx.installer_type,
                elevation_detected=chain_ctx.elevation_detected,
                via_msiexec=chain_ctx.via_msiexec,
                chain_summary=chain_ctx.chain_summary,
            )
            return self._apply_user_policy(candidate, create_time, parent_chain)

        exe_raw = info.get("exe")
        exe_path: Path | None = None
        if exe_raw:
            try:
                exe_path = Path(exe_raw).resolve()
            except OSError:
                exe_path = Path(exe_raw)

        cmdline_parts = info.get("cmdline") or []
        cmdline = " ".join(cmdline_parts) if cmdline_parts else None

        if not looks_like_user_installer_candidate(name, exe_path, cmdline):
            return None

        parent_name: str | None = None
        parent_chain: tuple[str, ...] = ()
        ppid = info.get("ppid")
        if ppid:
            parent_chain = _parent_names(int(ppid))
            parent_name = parent_chain[0] if parent_chain else None

        via_msiexec = name == "msiexec.exe"
        msi_path = _extract_msi_path(cmdline_parts, cmdline) if via_msiexec else None
        if msi_path is not None:
            installer_path = msi_path
            installer_type = "MSI"
        elif exe_path and exe_path.suffix.lower() in {".exe", ".msi"}:
            installer_path = exe_path
            installer_type = "MSI" if exe_path.suffix.lower() == ".msi" else "EXE"
        else:
            installer_path = None
            installer_type = None

        candidate = DetectedInstallerProcess(
            pid=pid,
            process_name=name,
            executable_path=exe_path,
            command_line=cmdline,
            parent_process_name=parent_name,
            monitor_pid=pid,
            installer_path=installer_path,
            installer_type=installer_type,
            via_msiexec=via_msiexec and installer_path is not None,
        )
        return self._apply_user_policy(candidate, create_time, parent_chain)

    def _apply_user_policy(
        self,
        candidate: DetectedInstallerProcess,
        create_time: float | None,
        parent_chain: tuple[str, ...],
    ) -> DetectedInstallerProcess | None:
        ok, reason = evaluate_user_installation(
            pid=candidate.pid,
            monitor_pid=candidate.monitor_pid or candidate.pid,
            process_name=candidate.process_name,
            installer_path=candidate.installer_path,
            executable_path=candidate.executable_path,
            command_line=candidate.command_line,
            parent_chain=parent_chain,
            via_msiexec=candidate.via_msiexec,
            process_create_time=create_time,
            max_process_age_seconds=self._max_process_age_seconds,
        )
        if not ok:
            logger.debug(
                "installer_detection_skipped",
                pid=candidate.pid,
                name=candidate.process_name,
                path=str(candidate.installer_path),
                reason=reason,
            )
            return None
        return candidate


def _parent_names(ppid: int, depth: int = 8) -> tuple[str, ...]:
    names: list[str] = []
    try:
        current = psutil.Process(ppid)
    except (psutil.NoSuchProcess, psutil.AccessDenied, ValueError):
        return ()
    for _ in range(depth):
        try:
            names.append(current.name())
            current = current.parent()
            if current is None:
                break
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            break
    return tuple(names)
