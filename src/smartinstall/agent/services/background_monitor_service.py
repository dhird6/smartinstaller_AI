"""Windows background service for automatic installer detection and monitoring."""

from __future__ import annotations

import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import structlog

from smartinstall.agent.detection.installer_process_detector import (
    DetectedInstallerProcess,
    InstallerProcessDetector,
)
from smartinstall.agent.di.container import ServiceContainer
from smartinstall.agent.infrastructure.event_bus import AgentEvent, EventBus
from smartinstall.agent.intake.report_publisher import ReportPublisher
from smartinstall.agent.monitoring.completion_notifications import build_completion_notification
from smartinstall.agent.monitoring.monitoring_state_store import (
    ActiveInstallationState,
    CompletedInstallationState,
    MonitoringStateStore,
)
from smartinstall.agent.notifications.windows_notifier import WindowsNotifier
from smartinstall.core.enums.installation import InstallerType
from smartinstall.core.models.requests import StartSessionRequest

logger = structlog.get_logger(__name__)


class BackgroundMonitorService:
    """
    Polls for external user-initiated installer processes and runs passive monitoring.

    Uses cooldowns and concurrency limits to avoid loops on background/OS installers.
    """

    def __init__(self, container: ServiceContainer) -> None:
        self._container = container
        self._config = container.config
        self._event_bus = container.event_bus
        self._agent = container.installation_agent
        self._publisher = ReportPublisher(self._config.reports_dir)
        state_path = self._config.output_root / "monitoring_state.json"
        self._state_store = MonitoringStateStore(state_path)
        self._notifier = WindowsNotifier()
        self._tracked_pids: set[int] = set()
        self._in_progress_packages: set[str] = set()
        self._cooldown_until: dict[str, float] = {}
        self._active_monitor_count = 0
        self._scan_lock = threading.Lock()
        self._active_sessions: dict[int, str] = {}
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._handlers_attached = False

    @property
    def state_store(self) -> MonitoringStateStore:
        return self._state_store

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._attach_event_handlers()
        self._stop.clear()
        state = self._state_store.load()
        state.service_running = True
        state.automatic_monitoring_enabled = self._config.auto_monitor_enabled
        self._state_store.save(state)
        self._thread = threading.Thread(target=self._run_loop, name="BackgroundMonitor", daemon=True)
        self._thread.start()
        logger.info("background_monitor_service_started")

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=10)
        state = self._state_store.load()
        state.service_running = False
        self._state_store.save(state)
        logger.info("background_monitor_service_stopped")

    def _attach_event_handlers(self) -> None:
        if self._handlers_attached:
            return
        self._event_bus.subscribe(AgentEvent.INSTALLER_LAUNCHED, self._on_installer_launched)
        self._event_bus.subscribe(AgentEvent.INSTALL_STAGE_CHANGED, self._on_stage)
        self._handlers_attached = True

    def _run_loop(self) -> None:
        interval = max(2, self._config.background_poll_interval_seconds)
        while not self._stop.is_set():
            self._touch_heartbeat()
            if self._config.auto_monitor_enabled:
                self._scan_once()
            self._stop.wait(interval)

    def _touch_heartbeat(self) -> None:
        state = self._state_store.load()
        state.last_updated = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        self._state_store.save(state)

    def _scan_once(self) -> None:
        max_concurrent = max(1, self._config.auto_monitor_max_concurrent)
        with self._scan_lock:
            if self._active_monitor_count >= max_concurrent:
                return

            self._prune_cooldowns()
            exclude = frozenset(self._tracked_pids)
            detector = InstallerProcessDetector(
                exclude_pids=exclude,
                max_process_age_seconds=float(self._config.auto_monitor_max_process_age_seconds),
            )
            for detected in detector.scan():
                if self._active_monitor_count >= max_concurrent:
                    break

                monitor_pid = detected.monitor_pid or detected.pid
                installer_path = detected.installer_path or detected.executable_path
                if installer_path is None or not installer_path.is_file():
                    if detected.executable_path and detected.executable_path.is_file():
                        installer_path = detected.executable_path
                    else:
                        continue

                package_key = _package_key(installer_path)
                if package_key in self._in_progress_packages:
                    continue
                if self._is_on_cooldown(package_key):
                    continue
                if monitor_pid in self._tracked_pids:
                    continue

                self._tracked_pids.add(monitor_pid)
                self._in_progress_packages.add(package_key)
                self._active_monitor_count += 1
                worker = threading.Thread(
                    target=self._monitor_detected,
                    args=(detected, package_key),
                    name=f"PassiveMonitor-{monitor_pid}",
                    daemon=True,
                )
                worker.start()

    def _monitor_detected(
        self,
        detected: DetectedInstallerProcess,
        package_key: str,
    ) -> None:
        installer_path = detected.installer_path or detected.executable_path
        if installer_path is None:
            self._release_slot(package_key, detected)
            return

        monitor_pid = detected.monitor_pid or detected.pid
        if detected.installer_type == "MSI":
            installer_type = InstallerType.MSI
        else:
            installer_type = (
                InstallerType.MSI
                if installer_path.suffix.lower() == ".msi"
                else InstallerType.EXE
            )
        request = StartSessionRequest(
            installerPath=str(installer_path),
            installerType=installer_type,
            productName=installer_path.stem,
            callerTag="background-auto",
            outputDirectory=str(self._config.output_root),
        )

        session_id = ""
        try:
            result = self._agent.run_passive_monitoring(request, detected, monitor_pid=monitor_pid)
            if not result.success or result.value is None:
                logger.warning("passive_monitor_failed", pid=detected.pid)
                if session_id:
                    self._state_store.remove_active(session_id)
                return

            finalized_session, unified = result.value
            session_id = finalized_session.session_id
            report_path = self._publisher.publish(
                unified,
                application_name=request.product_name or installer_path.stem,
            )

            outcome = unified.status.installation_outcome
            error_summary = None
            error_code = ""
            error_message = ""
            if unified.errors:
                err = unified.errors[0]
                error_code = err.code
                error_message = err.message
                error_summary = f"{error_code}: {error_message}"

            self._enqueue_completion_notification(
                session_id=session_id,
                installer_name=installer_path.name,
                outcome=outcome,
                report_path=str(report_path),
                has_errors=bool(unified.errors),
                error_code=error_code,
                error_message=error_message,
            )

            self._state_store.remove_active(session_id)
            self._state_store.record_completed(
                CompletedInstallationState(
                    session_id=session_id,
                    installer_name=installer_path.name,
                    outcome=outcome,
                    report_path=str(report_path),
                    error_summary=error_summary,
                    completed_at=finalized_session.end_timestamp or "",
                    mode="automatic",
                )
            )
        except Exception:  # noqa: BLE001
            logger.exception("background_monitor_thread_failed", pid=detected.pid)
            if session_id:
                self._state_store.remove_active(session_id)
        finally:
            self._release_slot(package_key, detected)

    def _release_slot(self, package_key: str, detected: DetectedInstallerProcess) -> None:
        monitor_pid = detected.monitor_pid or detected.pid
        cooldown = max(60, self._config.auto_monitor_cooldown_seconds)
        self._cooldown_until[package_key] = time.monotonic() + cooldown
        self._in_progress_packages.discard(package_key)
        self._tracked_pids.discard(monitor_pid)
        self._active_sessions.pop(monitor_pid, None)
        with self._scan_lock:
            self._active_monitor_count = max(0, self._active_monitor_count - 1)

    def _is_on_cooldown(self, package_key: str) -> bool:
        until = self._cooldown_until.get(package_key, 0.0)
        return time.monotonic() < until

    def _prune_cooldowns(self) -> None:
        now = time.monotonic()
        expired = [key for key, until in self._cooldown_until.items() if until <= now]
        for key in expired:
            del self._cooldown_until[key]

    def _enqueue_completion_notification(
        self,
        *,
        session_id: str,
        installer_name: str,
        outcome: str,
        report_path: str,
        has_errors: bool,
        error_code: str,
        error_message: str,
    ) -> None:
        suggested = _suggest_fix(error_message) if has_errors else ""
        payload = build_completion_notification(
            session_id=session_id,
            installer_name=installer_name,
            outcome=outcome,
            report_path=report_path,
            has_errors=has_errors,
            mode="automatic",
            error_code=error_code,
            error_message=error_message,
            suggested_fix=suggested,
        )
        self._state_store.enqueue_notification(payload)
        if not self._config.enable_windows_notifications:
            return
        if has_errors:
            self._notifier.show_installation_failed(
                error_message=error_message or outcome,
                suggested_fix=suggested,
            )
        else:
            self._notifier.show_toast(
                title="Installation Complete",
                message=f"{installer_name} finished ({outcome}).",
            )

    def _on_installer_launched(self, event: AgentEvent, payload: dict) -> None:
        if payload.get("mode") != "passive":
            return
        session_id = str(payload.get("sessionId", ""))
        pid = int(payload.get("pid", 0))
        if not session_id or not pid:
            return
        self._active_sessions[pid] = session_id
        self._state_store.upsert_active(
            ActiveInstallationState(
                session_id=session_id,
                installer_name=str(payload.get("installerName", "Installer")),
                installer_path=str(payload.get("installerPath", "")),
                pid=pid,
                stage="Monitoring installer process",
                started_at=str(payload.get("startedAt", "")),
                mode="automatic",
            )
        )

    def _on_stage(self, event: AgentEvent, payload: dict) -> None:
        session_id = payload.get("sessionId")
        stage = payload.get("stage")
        if not session_id or not stage:
            return
        state = self._state_store.load()
        updated = False
        for item in state.active_installations:
            if item.session_id == session_id:
                item.stage = str(stage)
                updated = True
        if updated:
            self._state_store.save(state)

def _package_key(path: Path) -> str:
    return str(path.resolve()).lower()


def _suggest_fix(error_message: str) -> str:
    lowered = error_message.lower()
    if "visual c++" in lowered or "vcruntime" in lowered or "msvcp" in lowered:
        return "Install Microsoft Visual C++ Redistributable and retry."
    if ".net" in lowered:
        return "Install .NET Framework 4.8 (or required runtime) and retry."
    if "1618" in lowered or "another installation" in lowered:
        return "Wait for other installations to finish, then retry."
    return "Open Smart Installer for full AI troubleshooting analysis."
