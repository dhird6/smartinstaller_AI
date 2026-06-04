"""Poll background monitoring state and push updates to the desktop UI."""

from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from smartinstall.agent.monitoring.monitoring_state_store import MonitoringPlatformState
from smartinstall.agent.services.background_monitor_service import BackgroundMonitorService


class BackgroundSyncWorker(QThread):
    """Reads monitoring_state.json and emits platform updates."""

    state_updated = Signal(object)
    notification_pending = Signal(object)

    def __init__(
        self,
        service: BackgroundMonitorService,
        poll_ms: int = 1000,
        *,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("BackgroundSyncWorker")
        self._service = service
        self._poll_ms = max(1000, poll_ms)

    def run(self) -> None:
        while not self.isInterruptionRequested():
            state = self._service.state_store.load()
            self.state_updated.emit(state)
            for item in self._service.state_store.drain_notifications():
                self.notification_pending.emit(item)
            self.msleep(self._poll_ms)
