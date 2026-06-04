"""Detect only NEW installer launches rooted in Explorer / user shell (one install = one track)."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path

import psutil
import structlog

from smartinstall.agent.detection.installer_process_detector import DetectedInstallerProcess
from smartinstall.agent.detection.process_chain_resolver import _extract_msi_path
from smartinstall.agent.detection.user_installation_policy import (
    _BACKGROUND_PROCESS_NAMES,
    _USER_INSTALLER_NAME_TOKENS,
    _is_interactive_user,
    _is_system_managed_path,
    _is_user_content_path,
    looks_like_user_installer_candidate,
)

logger = structlog.get_logger(__name__)

_EXCLUDED_NAMES = frozenset(
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
    }
)

# Immediate parent must be one of these, OR UAC consent with Explorer above.
_DIRECT_LAUNCH_PARENTS = frozenset(
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

_UAC_LAUNCH_PARENTS = frozenset({"consent.exe", "dllhost.exe"})

# setup.exe may spawn msiexec — link to same install if parent setup is already tracked.
_SETUP_PARENT_TOKENS = ("setup", "install", "installer", "unins", "bootstrap")


@dataclass(slots=True)
class _ParentLink:
    pid: int
    name: str


@dataclass(slots=True)
class _TrackedLaunch:
    """One user double-click / open-with → one monitoring session."""

    launch_id: str
    root_pid: int
    monitor_pid: int
    installer_path: Path
    installer_type: str
    process_name: str
    command_line: str | None
    chain_summary: str
    via_msiexec: bool
    elevation_detected: bool


class InstallationLaunchDetector:
    """
    Tracks process snapshots and reacts only to NEW PIDs that are a direct user launch.

    Avoids re-scanning every installer-like process on the machine each poll.
    """

    def __init__(
        self,
        *,
        exclude_pids: frozenset[int] | None = None,
        max_launch_age_seconds: float = 60.0,
    ) -> None:
        self._exclude_pids = exclude_pids or frozenset()
        self._own_pid = os.getpid()
        self._max_launch_age = max_launch_age_seconds
        self._known_pids: set[int] | None = None
        self._active_launches: dict[str, _TrackedLaunch] = {}

    def set_exclude_pids(self, pids: frozenset[int]) -> None:
        self._exclude_pids = pids

    def scan_new_launches(self) -> list[DetectedInstallerProcess]:
        current_pids: set[int] = set()
        all_infos: list[dict] = []

        for proc in psutil.process_iter(["pid", "name", "exe", "cmdline", "ppid", "create_time"]):
            try:
                info = proc.info
                pid = int(info["pid"])
            except (TypeError, ValueError, psutil.NoSuchProcess):
                continue
            current_pids.add(pid)
            all_infos.append(info)

        first_scan = self._known_pids is None
        if first_scan:
            self._known_pids = current_pids

        results: list[DetectedInstallerProcess] = []
        for info in all_infos:
            pid = int(info["pid"])
            is_new = not first_scan and pid not in self._known_pids
            is_warmup = first_scan and _is_young_process(
                info.get("create_time"),
                self._max_launch_age,
            )
            if not is_new and not is_warmup:
                continue
            detected = self._try_new_process(info)
            if detected is not None:
                results.append(detected)

        if not first_scan:
            self._known_pids = current_pids

        self._reap_finished_launches()
        return results

    def _try_new_process(self, info: dict) -> DetectedInstallerProcess | None:
        try:
            pid = int(info["pid"])
        except (TypeError, ValueError):
            return None
        if pid == self._own_pid or pid in self._exclude_pids:
            return None

        name = (info.get("name") or "").lower()
        if name in _EXCLUDED_NAMES or name in _BACKGROUND_PROCESS_NAMES:
            return None

        create_time = info.get("create_time")
        if create_time is not None and (time.time() - create_time) > self._max_launch_age:
            return None

        ppid = info.get("ppid")
        if not ppid:
            return None

        parent_links = _walk_parents(int(ppid), max_depth=10)
        if not parent_links:
            return None

        immediate_parent = parent_links[0].name.lower()
        parent_names = tuple(link.name.lower() for link in parent_links)
        chain_summary = " → ".join(f"{link.name}({link.pid})" for link in parent_links[:6])

        exe_path = _exe_path(info.get("exe"))
        cmdline_parts = info.get("cmdline") or []
        cmdline = " ".join(cmdline_parts) if cmdline_parts else None

        # Child msiexec of an in-flight setup — extend same install, do not start another.
        if name == "msiexec.exe":
            return self._link_msiexec_child(
                pid=pid,
                cmdline_parts=cmdline_parts,
                cmdline=cmdline,
                parent_links=parent_links,
                chain_summary=chain_summary,
            )

        if not looks_like_user_installer_candidate(name, exe_path, cmdline):
            return None

        launch_kind = _classify_launch_type(immediate_parent, parent_names)
        if launch_kind is None:
            logger.debug(
                "launch_rejected_no_user_parent",
                pid=pid,
                name=name,
                parent=immediate_parent,
            )
            return None

        if not _is_interactive_user(pid):
            return None

        installer_path, installer_type, via_msiexec = _resolve_installer_target(
            name, exe_path, cmdline_parts, cmdline
        )
        if installer_path is None or not installer_path.is_file():
            return None

        path_lower = str(installer_path).lower()
        if _is_system_managed_path(path_lower) and not _is_user_content_path(path_lower):
            return None

        elevation = launch_kind == "uac"
        launch_id = _launch_id(installer_path, pid)

        if launch_id in self._active_launches:
            return None

        tracked = _TrackedLaunch(
            launch_id=launch_id,
            root_pid=pid,
            monitor_pid=pid,
            installer_path=installer_path,
            installer_type=installer_type,
            process_name=name,
            command_line=cmdline,
            chain_summary=chain_summary,
            via_msiexec=via_msiexec,
            elevation_detected=elevation,
        )
        self._active_launches[launch_id] = tracked
        logger.info(
            "user_install_launch_detected",
            launch_id=launch_id,
            pid=pid,
            installer=str(installer_path),
            launch_kind=launch_kind,
            parent=immediate_parent,
        )
        return _to_detected(tracked, parent_names[0] if parent_names else None)

    def _link_msiexec_child(
        self,
        *,
        pid: int,
        cmdline_parts: list[str],
        cmdline: str | None,
        parent_links: list[_ParentLink],
        chain_summary: str,
    ) -> DetectedInstallerProcess | None:
        cmd = (cmdline or "").lower()
        if "/i" not in cmd and "-i" not in cmd:
            return None
        if "/x" in cmd or "/f" in cmd:
            return None

        msi_path = _extract_msi_path(cmdline_parts, cmdline)
        if msi_path is None or not msi_path.is_file():
            return None

        parent_launch: _TrackedLaunch | None = None
        for link in parent_links:
            for tracked in self._active_launches.values():
                if tracked.monitor_pid == link.pid or tracked.root_pid == link.pid:
                    parent_launch = tracked
                    break
            if parent_launch is not None:
                break

        if parent_launch is None:
            setup_parent = parent_links[0].name.lower() if parent_links else ""
            if not any(token in setup_parent for token in _SETUP_PARENT_TOKENS):
                return None
            if not _chain_includes_user_shell(parent_links):
                return None
            launch_id = _launch_id(msi_path, pid)
            if launch_id in self._active_launches:
                return None
            tracked = _TrackedLaunch(
                launch_id=launch_id,
                root_pid=parent_links[0].pid,
                monitor_pid=pid,
                installer_path=msi_path,
                installer_type="MSI",
                process_name="msiexec.exe",
                command_line=cmdline,
                chain_summary=chain_summary,
                via_msiexec=True,
                elevation_detected=False,
            )
            self._active_launches[launch_id] = tracked
            logger.info(
                "msiexec_linked_to_user_setup",
                launch_id=launch_id,
                msi_pid=pid,
                msi=str(msi_path),
            )
            return _to_detected(tracked, parent_links[0].name)

        parent_launch.monitor_pid = pid
        parent_launch.via_msiexec = True
        parent_launch.installer_path = msi_path
        parent_launch.installer_type = "MSI"
        parent_launch.process_name = "msiexec.exe"
        parent_launch.command_line = cmdline
        parent_launch.chain_summary = chain_summary
        logger.info(
            "msiexec_adopted_by_launch",
            launch_id=parent_launch.launch_id,
            msi_pid=pid,
        )
        return None

    def _reap_finished_launches(self) -> None:
        dead: list[str] = []
        for launch_id, tracked in self._active_launches.items():
            if not _process_alive(tracked.monitor_pid):
                dead.append(launch_id)
        for launch_id in dead:
            del self._active_launches[launch_id]

    def release_launch(self, launch_id: str) -> None:
        self._active_launches.pop(launch_id, None)


def _classify_launch_type(immediate_parent: str, parent_names: tuple[str, ...]) -> str | None:
    if immediate_parent in _DIRECT_LAUNCH_PARENTS:
        return "direct"
    if immediate_parent in _UAC_LAUNCH_PARENTS and _chain_includes_user_shell_names(parent_names):
        return "uac"
    return None


def _chain_includes_user_shell(links: list[_ParentLink]) -> bool:
    return _chain_includes_user_shell_names(tuple(link.name.lower() for link in links))


def _chain_includes_user_shell_names(names: tuple[str, ...]) -> bool:
    return any(name in _DIRECT_LAUNCH_PARENTS for name in names)


def _resolve_installer_target(
    name: str,
    exe_path: Path | None,
    cmdline_parts: list[str],
    cmdline: str | None,
) -> tuple[Path | None, str, bool]:
    if name == "msiexec.exe":
        msi = _extract_msi_path(cmdline_parts, cmdline)
        if msi is not None:
            return msi, "MSI", True
        return None, "EXE", False
    if exe_path is not None and exe_path.suffix.lower() == ".msi":
        return exe_path, "MSI", False
    if exe_path is not None and exe_path.suffix.lower() == ".exe":
        return exe_path, "EXE", False
    return None, "EXE", False


def _launch_id(installer_path: Path, pid: int) -> str:
    return f"{installer_path.resolve()}:{pid}"


def _to_detected(tracked: _TrackedLaunch, parent_name: str | None) -> DetectedInstallerProcess:
    return DetectedInstallerProcess(
        pid=tracked.root_pid,
        process_name=tracked.process_name,
        executable_path=tracked.installer_path,
        command_line=tracked.command_line,
        parent_process_name=parent_name,
        monitor_pid=tracked.monitor_pid,
        installer_path=tracked.installer_path,
        installer_type=tracked.installer_type,
        elevation_detected=tracked.elevation_detected,
        via_msiexec=tracked.via_msiexec,
        chain_summary=tracked.chain_summary,
        launch_id=tracked.launch_id,
    )


def _walk_parents(ppid: int, max_depth: int) -> list[_ParentLink]:
    links: list[_ParentLink] = []
    try:
        current = psutil.Process(ppid)
    except (psutil.NoSuchProcess, psutil.AccessDenied, ValueError):
        return links
    for _ in range(max_depth):
        try:
            links.append(_ParentLink(pid=current.pid, name=current.name()))
            current = current.parent()
            if current is None:
                break
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            break
    return links


def _exe_path(raw: str | None) -> Path | None:
    if not raw:
        return None
    try:
        return Path(raw).resolve()
    except OSError:
        return Path(raw)


def _is_young_process(create_time: float | None, max_age: float) -> bool:
    if create_time is None:
        return False
    return (time.time() - create_time) <= max_age


def _process_alive(pid: int) -> bool:
    try:
        return psutil.Process(pid).is_running()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False
