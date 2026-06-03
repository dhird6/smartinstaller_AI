"""Installer process execution and stream capture (functional-spec §2)."""

from __future__ import annotations

import os
import shlex
import subprocess
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import structlog

from smartinstall.agent.collectors.event_log_collector import EventLogCollector
from smartinstall.agent.collectors.process_collector import ProcessCollector
from smartinstall.agent.infrastructure.config_provider import SmartInstallConfig
from smartinstall.agent.infrastructure.credential_redactor import redact_command_line
from smartinstall.agent.infrastructure.privilege_checker import is_user_admin
from smartinstall.agent.runners.exit_codes import describe_exit_code
from smartinstall.core.enums.installation import InstallerType

logger = structlog.get_logger(__name__)

_HIGH_PRIORITY_STDERR = ("error", "fail", "exception", "access denied", "rollback")
_WIN_ERROR_ELEVATION_REQUIRED = 740


@dataclass(slots=True)
class InstallerRunResult:
    pid: int
    parent_pid: int
    command_line: str
    start_timestamp: str
    end_timestamp: str | None = None
    exit_code: int | None = None
    timed_out: bool = False
    stdout_path: Path | None = None
    stderr_path: Path | None = None
    stdout_line_count: int = 0
    stderr_line_count: int = 0
    stderr_high_priority_count: int = 0
    msi_verbose_log_path: Path | None = None
    launched_elevated: bool = False


@dataclass
class _StreamCapture:
    lines: list[str] = field(default_factory=list)
    high_priority_count: int = 0
    lock: threading.Lock = field(default_factory=threading.Lock)

    def append(self, line: str, *, is_stderr: bool) -> None:
        with self.lock:
            self.lines.append(line)
            if is_stderr and any(k in line.lower() for k in _HIGH_PRIORITY_STDERR):
                self.high_priority_count += 1


class InstallerRunner:
    """Launches EXE or MSI installers with stdout/stderr capture."""

    def __init__(self, config: SmartInstallConfig) -> None:
        self._config = config

    def run(
        self,
        *,
        installer_path: Path,
        installer_type: InstallerType,
        session_directory: Path,
        additional_args: str | None,
        timeout_seconds: int,
        process_collector: ProcessCollector | None = None,
        event_collector: EventLogCollector | None = None,
    ) -> InstallerRunResult:
        session_directory.mkdir(parents=True, exist_ok=True)
        stdout_path = session_directory / "stdout.log"
        stderr_path = session_directory / "stderr.log"
        msi_log_path = session_directory / "msi_verbose.log"

        command = self._build_command(
            installer_path=installer_path,
            installer_type=installer_type,
            msi_log_path=msi_log_path,
            additional_args=additional_args,
        )
        command_line = redact_command_line(subprocess.list2cmdline(command))
        start_ts = _utc_now_iso()
        parent_pid = os.getpid()

        use_elevation = (
            os.name == "nt"
            and self._config.elevate_installers
            and not is_user_admin()
        )

        if use_elevation:
            logger.info(
                "launching_installer_elevated",
                reason="agent not elevated; elevateInstallers=true",
            )
            return self._run_elevated(
                command=command,
                command_line=command_line,
                installer_path=installer_path,
                installer_type=installer_type,
                session_directory=session_directory,
                stdout_path=stdout_path,
                stderr_path=stderr_path,
                msi_log_path=msi_log_path,
                start_ts=start_ts,
                parent_pid=parent_pid,
                timeout_seconds=timeout_seconds,
                process_collector=process_collector,
                event_collector=event_collector,
            )

        try:
            return self._run_standard(
                command=command,
                command_line=command_line,
                installer_path=installer_path,
                installer_type=installer_type,
                stdout_path=stdout_path,
                stderr_path=stderr_path,
                msi_log_path=msi_log_path,
                start_ts=start_ts,
                parent_pid=parent_pid,
                timeout_seconds=timeout_seconds,
                process_collector=process_collector,
                event_collector=event_collector,
            )
        except OSError as exc:
            if getattr(exc, "winerror", None) != _WIN_ERROR_ELEVATION_REQUIRED:
                raise
            if not self._config.elevate_installers:
                raise PermissionError(
                    "Installer requires administrator privileges. "
                    "Restart PowerShell as Administrator or set elevateInstallers=true."
                ) from exc
            logger.warning("elevation_required_retry", error=str(exc))
            return self._run_elevated(
                command=command,
                command_line=command_line,
                installer_path=installer_path,
                installer_type=installer_type,
                session_directory=session_directory,
                stdout_path=stdout_path,
                stderr_path=stderr_path,
                msi_log_path=msi_log_path,
                start_ts=start_ts,
                parent_pid=parent_pid,
                timeout_seconds=timeout_seconds,
                process_collector=process_collector,
                event_collector=event_collector,
            )

    def _run_standard(
        self,
        *,
        command: list[str],
        command_line: str,
        installer_path: Path,
        installer_type: InstallerType,
        stdout_path: Path,
        stderr_path: Path,
        msi_log_path: Path,
        start_ts: str,
        parent_pid: int,
        timeout_seconds: int,
        process_collector: ProcessCollector | None,
        event_collector: EventLogCollector | None,
    ) -> InstallerRunResult:
        stdout_capture = _StreamCapture()
        stderr_capture = _StreamCapture()

        process = subprocess.Popen(
            command,
            cwd=str(installer_path.parent),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        assert process.stdout is not None
        assert process.stderr is not None

        def pump(stream, capture: _StreamCapture, *, is_stderr: bool) -> None:
            for line in iter(stream.readline, ""):
                offset = time.monotonic()
                stamped = f"[+{offset:.3f}s] {line.rstrip()}\n"
                capture.append(stamped, is_stderr=is_stderr)
            stream.close()

        threads = [
            threading.Thread(
                target=pump,
                args=(process.stdout, stdout_capture),
                kwargs={"is_stderr": False},
                daemon=True,
            ),
            threading.Thread(
                target=pump,
                args=(process.stderr, stderr_capture),
                kwargs={"is_stderr": True},
                daemon=True,
            ),
        ]
        for thread in threads:
            thread.start()

        if process_collector is not None:
            process_collector.start_tracking(process.pid)

        stop_sampling = threading.Event()

        def sampler() -> None:
            while not stop_sampling.is_set():
                if process_collector is not None:
                    process_collector.sample()
                if event_collector is not None:
                    event_collector.poll_live()
                time.sleep(2.0)

        sampler_thread = threading.Thread(target=sampler, daemon=True)
        sampler_thread.start()

        timed_out = False
        try:
            exit_code = process.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
            process.kill()
            exit_code = process.wait()
        finally:
            stop_sampling.set()
            sampler_thread.join(timeout=5)
            for thread in threads:
                thread.join(timeout=5)

        stdout_path.write_text("".join(stdout_capture.lines), encoding="utf-8")
        stderr_path.write_text("".join(stderr_capture.lines), encoding="utf-8")

        end_ts = _utc_now_iso()
        logger.info(
            "installer_exited",
            pid=process.pid,
            exit_code=exit_code,
            timed_out=timed_out,
            elevated=False,
        )

        return InstallerRunResult(
            pid=process.pid,
            parent_pid=parent_pid,
            command_line=command_line,
            start_timestamp=start_ts,
            end_timestamp=end_ts,
            exit_code=exit_code,
            timed_out=timed_out,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            stdout_line_count=len(stdout_capture.lines),
            stderr_line_count=len(stderr_capture.lines),
            stderr_high_priority_count=stderr_capture.high_priority_count,
            msi_verbose_log_path=msi_log_path if installer_type == InstallerType.MSI else None,
            launched_elevated=False,
        )

    def _run_elevated(
        self,
        *,
        command: list[str],
        command_line: str,
        installer_path: Path,
        installer_type: InstallerType,
        session_directory: Path,
        stdout_path: Path,
        stderr_path: Path,
        msi_log_path: Path,
        start_ts: str,
        parent_pid: int,
        timeout_seconds: int,
        process_collector: ProcessCollector | None,
        event_collector: EventLogCollector | None,
    ) -> InstallerRunResult:
        from smartinstall.agent.runners.windows_elevated_runner import (
            run_elevated,
            write_elevated_stream_placeholders,
        )

        write_elevated_stream_placeholders(stdout_path, stderr_path)

        stop_sampling = threading.Event()

        def sampler() -> None:
            while not stop_sampling.is_set():
                if process_collector is not None:
                    process_collector.sample()
                if event_collector is not None:
                    event_collector.poll_live()
                time.sleep(2.0)

        sampler_thread = threading.Thread(target=sampler, daemon=True)
        sampler_thread.start()

        try:
            exit_code, pid, timed_out = run_elevated(
                command,
                working_directory=str(installer_path.parent),
                timeout_seconds=timeout_seconds,
            )
        finally:
            stop_sampling.set()
            sampler_thread.join(timeout=5)

        if process_collector is not None:
            process_collector.start_tracking(pid)

        end_ts = _utc_now_iso()
        logger.info(
            "installer_exited",
            pid=pid,
            exit_code=exit_code,
            timed_out=timed_out,
            elevated=True,
        )

        return InstallerRunResult(
            pid=pid,
            parent_pid=parent_pid,
            command_line=command_line,
            start_timestamp=start_ts,
            end_timestamp=end_ts,
            exit_code=exit_code,
            timed_out=timed_out,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            stdout_line_count=0,
            stderr_line_count=0,
            stderr_high_priority_count=0,
            msi_verbose_log_path=msi_log_path if installer_type == InstallerType.MSI else None,
            launched_elevated=True,
        )

    @staticmethod
    def describe_exit(exit_code: int | None) -> tuple[str, bool]:
        if exit_code is None:
            return "Process did not return an exit code", False
        return describe_exit_code(exit_code)

    def _build_command(
        self,
        *,
        installer_path: Path,
        installer_type: InstallerType,
        msi_log_path: Path,
        additional_args: str | None,
    ) -> list[str]:
        extra = shlex.split(additional_args, posix=False) if additional_args else []

        if installer_type == InstallerType.MSI:
            system_root = Path(os.environ.get("SystemRoot", r"C:\Windows"))
            msiexec = system_root / "System32" / "msiexec.exe"
            if not msiexec.is_file():
                raise FileNotFoundError(f"msiexec.exe not found at {msiexec}")
            command = [
                str(msiexec),
                "/i",
                str(installer_path),
                "/l*v",
                str(msi_log_path),
                "/qb",
                "/norestart",
            ]
            return command + extra

        command = [str(installer_path)]
        return command + extra


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
