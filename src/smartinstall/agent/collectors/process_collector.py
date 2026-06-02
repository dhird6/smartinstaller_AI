"""Process tree, child process exit codes, and resource snapshots."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import psutil
import structlog

from smartinstall.core.models.evidence import ChildProcessEvidence, ProcessSnapshotItem

logger = structlog.get_logger(__name__)


@dataclass(slots=True)
class ProcessCollectionResult:
    snapshots: list[ProcessSnapshotItem] = field(default_factory=list)
    child_processes: list[ChildProcessEvidence] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class ProcessCollector:
    """Tracks installer tree, child exits, and CPU/memory during installation."""

    def __init__(self, sample_interval_seconds: float = 2.0) -> None:
        self._sample_interval = sample_interval_seconds
        self._root_pid: int | None = None
        self._snapshots: list[ProcessSnapshotItem] = []
        self._child_processes: list[ChildProcessEvidence] = []
        self._errors: list[str] = []
        self._tracking = False
        self._handles: dict[int, psutil.Process] = {}
        self._recorded_child_pids: set[int] = set()

    def start_tracking(self, root_pid: int) -> None:
        self._root_pid = root_pid
        self._tracking = True
        self._snapshots.clear()
        self._child_processes.clear()
        self._errors.clear()
        self._handles.clear()
        self._recorded_child_pids.clear()
        try:
            self._handles[root_pid] = psutil.Process(root_pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied) as exc:
            self._errors.append(f"root pid={root_pid}: {exc}")

    def sample(self) -> None:
        if not self._tracking or self._root_pid is None:
            return

        self._reap_exited_children()
        try:
            tree_pids = self._collect_tree_pids(self._root_pid)
            for pid in tree_pids:
                if pid not in self._handles:
                    try:
                        self._handles[pid] = psutil.Process(pid)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue

                try:
                    proc = self._handles[pid]
                    with proc.oneshot():
                        cpu = proc.cpu_percent(interval=None)
                        mem_mb = proc.memory_info().rss / (1024 * 1024)
                        cmdline = " ".join(proc.cmdline()) if proc.cmdline() else None
                        self._snapshots.append(
                            ProcessSnapshotItem(
                                processId=pid,
                                parentProcessId=proc.ppid(),
                                processName=proc.name(),
                                executablePath=_safe_exe(proc),
                                cpuPercent=round(cpu, 2),
                                memoryMb=round(mem_mb, 2),
                                isInstallerRoot=pid == self._root_pid,
                            )
                        )
                except (psutil.NoSuchProcess, psutil.AccessDenied) as exc:
                    self._errors.append(f"pid={pid}: {exc}")
        except Exception as exc:  # noqa: BLE001
            self._errors.append(str(exc))

    def finalize(self) -> ProcessCollectionResult:
        self._tracking = False
        self._reap_exited_children()
        self._handles.clear()
        return ProcessCollectionResult(
            snapshots=list(self._snapshots),
            child_processes=list(self._child_processes),
            errors=list(self._errors),
        )

    def _reap_exited_children(self) -> None:
        for pid, proc in list(self._handles.items()):
            if pid == self._root_pid:
                if not proc.is_running():
                    self._handles.pop(pid, None)
                continue
            if not proc.is_running():
                self._record_child_exit(pid, proc)
                self._handles.pop(pid, None)

    def _record_child_exit(self, pid: int, proc: psutil.Process) -> None:
        if pid == self._root_pid or pid in self._recorded_child_pids:
            return
        exit_code = _read_exit_code(proc)

        try:
            name = proc.name()
            ppid = proc.ppid()
            exe = _safe_exe(proc)
            cmdline = " ".join(proc.cmdline()) if proc.cmdline() else None
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            name = "unknown"
            ppid = None
            exe = None
            cmdline = None

        self._recorded_child_pids.add(pid)
        self._child_processes.append(
            ChildProcessEvidence(
                processId=pid,
                parentProcessId=ppid,
                processName=name,
                executablePath=exe,
                exitCode=exit_code,
                commandLine=cmdline,
            )
        )
        if exit_code not in (None, 0):
            logger.info("child_process_exited", pid=pid, name=name, exit_code=exit_code)


def _read_exit_code(proc: psutil.Process) -> int | None:
    """psutil.Process has no returncode; use wait() after the process has exited."""
    try:
        if proc.is_running():
            return None
        return proc.wait(timeout=0)
    except psutil.TimeoutExpired:
        return None
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return None

    def _collect_tree_pids(self, root_pid: int) -> list[int]:
        pids = [root_pid]
        try:
            parent = psutil.Process(root_pid)
            for child in parent.children(recursive=True):
                pids.append(child.pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
        return pids


def _safe_exe(proc: psutil.Process) -> str | None:
    try:
        return proc.exe()
    except (psutil.AccessDenied, psutil.NoSuchProcess):
        return None
