"""Attach to an already-running installer process and monitor until exit."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

import psutil
import structlog

from smartinstall.agent.collectors.event_log_collector import EventLogCollector
from smartinstall.agent.collectors.process_collector import ProcessCollector
from smartinstall.agent.runners.installer_runner import InstallerRunResult
from smartinstall.core.enums.installation import InstallerType

logger = structlog.get_logger(__name__)

StageCallback = Callable[[str], None]
LogLineCallback = Callable[[str], None]


class ProcessAttachRunner:
    """Passive monitoring: observe external installer PID without launching it."""

    def attach_and_wait(
        self,
        *,
        root_pid: int,
        installer_path: Path,
        installer_type: InstallerType,
        session_directory: Path,
        command_line: str,
        timeout_seconds: int,
        process_collector: ProcessCollector | None = None,
        event_collector: EventLogCollector | None = None,
        on_stage: StageCallback | None = None,
        on_log_line: LogLineCallback | None = None,
    ) -> InstallerRunResult:
        session_directory.mkdir(parents=True, exist_ok=True)
        stdout_path = session_directory / "stdout_passive.log"
        stderr_path = session_directory / "stderr_passive.log"
        msi_log_path = session_directory / "msi_verbose.log"
        start_ts = _utc_now_iso()

        try:
            root = psutil.Process(root_pid)
        except psutil.NoSuchProcess as exc:
            raise RuntimeError(f"Installer process {root_pid} is not running") from exc

        parent_pid = root.ppid()
        if process_collector is not None:
            process_collector.start_tracking(root_pid)

        if on_stage is not None:
            on_stage("Monitoring external installer process")

        stop_sampling = threading.Event()

        def sampler() -> None:
            while not stop_sampling.is_set():
                if process_collector is not None:
                    process_collector.sample()
                    if on_log_line is not None:
                        for snap in process_collector.drain_recent_snapshots(2):
                            on_log_line(
                                f"[process] {snap.process_name} (pid={snap.process_id}) "
                                f"CPU={snap.cpu_percent}% MEM={snap.memory_mb:.1f}MB"
                            )
                if event_collector is not None:
                    event_collector.poll_live()
                    if on_log_line is not None:
                        for entry in event_collector.drain_live_entries(3):
                            on_log_line(
                                f"[event:{entry.log_name}] {entry.level}: {entry.message[:200]}"
                            )
                time.sleep(2.0)

        sampler_thread = threading.Thread(target=sampler, daemon=True)
        sampler_thread.start()

        timed_out = False
        exit_code: int | None = None
        deadline = time.monotonic() + timeout_seconds
        try:
            while time.monotonic() < deadline:
                if not root.is_running():
                    exit_code = root.wait(timeout=1)
                    break
                if on_stage is not None:
                    on_stage("Installer running — collecting live telemetry")
                time.sleep(1.0)
            else:
                timed_out = True
                try:
                    root.terminate()
                    exit_code = root.wait(timeout=10)
                except psutil.TimeoutExpired:
                    root.kill()
                    exit_code = root.wait(timeout=5)
        except psutil.NoSuchProcess:
            exit_code = exit_code if exit_code is not None else 0
        finally:
            stop_sampling.set()
            sampler_thread.join(timeout=5)

        stdout_path.write_text(
            "Passive monitoring — installer launched externally (no stdout capture).\n",
            encoding="utf-8",
        )
        stderr_path.write_text("", encoding="utf-8")
        end_ts = _utc_now_iso()

        logger.info(
            "passive_installer_exited",
            pid=root_pid,
            exit_code=exit_code,
            timed_out=timed_out,
        )

        return InstallerRunResult(
            pid=root_pid,
            parent_pid=parent_pid,
            command_line=command_line,
            start_timestamp=start_ts,
            end_timestamp=end_ts,
            exit_code=exit_code,
            timed_out=timed_out,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            stdout_line_count=1,
            stderr_line_count=0,
            stderr_high_priority_count=0,
            msi_verbose_log_path=msi_log_path if installer_type == InstallerType.MSI else None,
            launched_elevated=False,
        )


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
