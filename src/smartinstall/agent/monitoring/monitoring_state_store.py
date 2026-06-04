"""Persist background monitoring state for dashboard synchronization."""

from __future__ import annotations

import json
import os
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class ActiveInstallationState:
    session_id: str
    installer_name: str
    installer_path: str
    pid: int
    stage: str
    started_at: str
    mode: str = "automatic"


@dataclass(slots=True)
class CompletedInstallationState:
    session_id: str
    installer_name: str
    outcome: str
    report_path: str | None
    error_summary: str | None
    completed_at: str
    mode: str = "automatic"


@dataclass(slots=True)
class MonitoringPlatformState:
    service_running: bool = False
    automatic_monitoring_enabled: bool = True
    active_installations: list[ActiveInstallationState] = field(default_factory=list)
    recent_installations: list[CompletedInstallationState] = field(default_factory=list)
    pending_notifications: list[dict[str, Any]] = field(default_factory=list)
    last_updated: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class MonitoringStateStore:
    """Thread-safe JSON state file shared between background service and UI."""

    def __init__(self, state_path: Path) -> None:
        self._path = state_path
        self._lock = threading.Lock()
        self._path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def path(self) -> Path:
        return self._path

    def load(self) -> MonitoringPlatformState:
        with self._lock:
            if not self._path.is_file():
                return MonitoringPlatformState()
            try:
                raw = json.loads(self._path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                return MonitoringPlatformState()
        return _parse_state(raw)

    def save(self, state: MonitoringPlatformState) -> None:
        state.last_updated = _utc_now()
        payload = json.dumps(state.to_dict(), indent=2)
        with self._lock:
            # Use a per-thread unique tmp name to avoid file-lock conflicts
            # when multiple sessions write concurrently.
            tmp = self._path.with_name(
                f"{self._path.stem}.{os.getpid()}.{threading.get_ident()}.tmp"
            )
            try:
                tmp.write_text(payload, encoding="utf-8")
                tmp.replace(self._path)
            finally:
                try:
                    tmp.unlink(missing_ok=True)
                except OSError:
                    pass

    def upsert_active(self, active: ActiveInstallationState) -> MonitoringPlatformState:
        state = self.load()
        state.active_installations = [
            item for item in state.active_installations if item.session_id != active.session_id
        ]
        state.active_installations.append(active)
        self.save(state)
        return state

    def remove_active(self, session_id: str) -> MonitoringPlatformState:
        state = self.load()
        state.active_installations = [
            item for item in state.active_installations if item.session_id != session_id
        ]
        self.save(state)
        return state

    def record_completed(self, completed: CompletedInstallationState, *, max_recent: int = 20) -> None:
        state = self.load()
        state.recent_installations = [
            item for item in state.recent_installations if item.session_id != completed.session_id
        ]
        state.recent_installations.insert(0, completed)
        state.recent_installations = state.recent_installations[:max_recent]
        self.save(state)

    def enqueue_notification(self, notification: dict[str, Any]) -> None:
        """Append a notification; replace prior entry for the same session + type."""
        state = self.load()
        session_id = str(notification.get("sessionId", ""))
        notification_type = str(notification.get("type", ""))
        if session_id and notification_type:
            state.pending_notifications = [
                item
                for item in state.pending_notifications
                if not (
                    str(item.get("sessionId", "")) == session_id
                    and str(item.get("type", "")) == notification_type
                )
            ]
        state.pending_notifications.append(notification)
        self.save(state)

    def drain_notifications(self) -> list[dict[str, Any]]:
        state = self.load()
        pending = list(state.pending_notifications)
        state.pending_notifications = []
        self.save(state)
        return pending


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _parse_state(raw: dict[str, Any]) -> MonitoringPlatformState:
    active = [
        ActiveInstallationState(**item) for item in raw.get("active_installations", []) if item
    ]
    recent = [
        CompletedInstallationState(**item) for item in raw.get("recent_installations", []) if item
    ]
    return MonitoringPlatformState(
        service_running=bool(raw.get("service_running", False)),
        automatic_monitoring_enabled=bool(raw.get("automatic_monitoring_enabled", True)),
        active_installations=active,
        recent_installations=recent,
        pending_notifications=list(raw.get("pending_notifications", [])),
        last_updated=str(raw.get("last_updated", "")),
    )
