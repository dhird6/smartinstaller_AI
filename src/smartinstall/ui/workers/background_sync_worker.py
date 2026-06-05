"""Poll background monitoring state and push updates to the desktop UI."""

from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from smartinstall.agent.monitoring.monitoring_state_store import MonitoringPlatformState
from smartinstall.agent.services.background_monitor_service import BackgroundMonitorService


def platform_state_fingerprint(state: MonitoringPlatformState) -> str:
    """Stable fingerprint — ignores heartbeat-only `last_updated` churn."""
    active = ",".join(
        f"{item.session_id}:{item.stage}:{item.pid}"
        for item in state.active_installations
    )
    recent = ",".join(
        f"{item.session_id}:{item.outcome}"
        for item in state.recent_installations[:8]
    )
    pending = str(len(state.pending_notifications))
    return (
        f"{int(state.service_running)}|"
        f"{int(state.automatic_monitoring_enabled)}|"
        f"{active}|{recent}|{pending}"
    )


class BackgroundSyncWorker(QThread):
    """Reads monitoring_state.json and emits platform updates."""

    state_updated = Signal(object)
    notification_pending = Signal(object)

    def __init__(
        self,
        service: BackgroundMonitorService,
        poll_ms: int = 3000,
        *,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("BackgroundSyncWorker")
        self._service = service
        self._idle_poll_ms = max(2000, poll_ms)
        self._active_poll_ms = 1000
        self._last_fingerprint = ""

    def run(self) -> None:
        while not self.isInterruptionRequested():
            state = self._service.state_store.load()
            fingerprint = platform_state_fingerprint(state)
            if fingerprint != self._last_fingerprint:
                self._last_fingerprint = fingerprint
                self.state_updated.emit(state)

            if state.pending_notifications:
                for item in self._service.state_store.drain_notifications():
                    self.notification_pending.emit(item)
                    fingerprint = platform_state_fingerprint(
                        self._service.state_store.load()
                    )
                    self._last_fingerprint = fingerprint

            poll_ms = self._active_poll_ms if state.active_installations else self._idle_poll_ms
            self.msleep(poll_ms)
