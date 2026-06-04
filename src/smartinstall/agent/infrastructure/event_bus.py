"""In-process event bus (EXT-04, M1-T06)."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from enum import StrEnum
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class AgentEvent(StrEnum):
    SESSION_STARTED = "SessionStarted"
    SESSION_ENDED = "SessionEnded"
    INSTALLER_DETECTED = "InstallerDetected"
    INSTALLER_LAUNCHED = "InstallerLaunched"
    INSTALLER_EXITED = "InstallerExited"
    INSTALL_STAGE_CHANGED = "InstallStageChanged"
    LIVE_LOG_LINE = "LiveLogLine"
    INSTALLATION_ERROR_DETECTED = "InstallationErrorDetected"
    SLM_DIAGNOSIS_COMPLETE = "SlmDiagnosisComplete"
    COLLECTION_COMPLETE = "CollectionComplete"
    REPORT_WRITE_FAILURE = "ReportWriteFailure"


EventHandler = Callable[[AgentEvent, dict[str, Any]], None]


class EventBus:
    """Synchronous publish/subscribe bus for lifecycle decoupling."""

    def __init__(self) -> None:
        self._handlers: dict[AgentEvent, list[EventHandler]] = defaultdict(list)

    def subscribe(self, event: AgentEvent, handler: EventHandler) -> None:
        if handler not in self._handlers[event]:
            self._handlers[event].append(handler)

    def unsubscribe(self, event: AgentEvent, handler: EventHandler) -> None:
        if handler in self._handlers[event]:
            self._handlers[event].remove(handler)

    def publish(self, event: AgentEvent, payload: dict[str, Any] | None = None) -> None:
        data = payload or {}
        logger.debug("event_published", agent_event=event.value, payload_keys=list(data.keys()))
        for handler in list(self._handlers[event]):
            handler(event, data)
