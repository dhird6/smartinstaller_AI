"""Bridge agent EventBus events to Qt signals."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QObject, Signal

from smartinstall.agent.infrastructure.event_bus import AgentEvent, EventBus


class QtEventBridge(QObject):
    """Translates in-process agent events into UI-friendly status messages."""

    status_update = Signal(str)
    live_log_line = Signal(str)
    stage_changed = Signal(str)
    installation_detected = Signal(str)
    installation_error = Signal(dict)

    def __init__(self, event_bus: EventBus) -> None:
        super().__init__()
        self._event_bus = event_bus
        self._attached = False

    def attach(self) -> None:
        if self._attached:
            return
        for event in AgentEvent:
            self._event_bus.subscribe(event, self._handle_event)
        self._attached = True

    def detach(self) -> None:
        if not self._attached:
            return
        for event in AgentEvent:
            self._event_bus.unsubscribe(event, self._handle_event)
        self._attached = False

    def _handle_event(self, event: AgentEvent, payload: dict[str, Any]) -> None:
        if event is AgentEvent.LIVE_LOG_LINE:
            line = payload.get("line")
            if line:
                self.live_log_line.emit(str(line))
            return
        if event is AgentEvent.INSTALL_STAGE_CHANGED:
            stage = payload.get("stage")
            if stage:
                self.stage_changed.emit(str(stage))
                self.status_update.emit(str(stage))
            return
        if event is AgentEvent.INSTALLER_DETECTED:
            name = payload.get("installerName", "installer")
            parts = [f"Detected external installer: {name}"]
            if payload.get("viaMsiexec"):
                parts.append("(MSI via msiexec)")
            if payload.get("elevationDetected"):
                parts.append("(UAC elevated)")
            chain = payload.get("chainSummary")
            if chain:
                parts.append(f"Chain: {chain}")
            self.installation_detected.emit(" ".join(parts))
            return
        if event is AgentEvent.INSTALLATION_ERROR_DETECTED:
            self.installation_error.emit(dict(payload))
            return
        message = _map_event_to_message(event, payload)
        if message:
            self.status_update.emit(message)


def _map_event_to_message(event: AgentEvent, payload: dict[str, Any]) -> str | None:
    if event is AgentEvent.INSTALLER_LAUNCHED:
        mode = payload.get("mode")
        if mode == "passive":
            return "Automatic monitoring started for external installer."
        return "Installation started. Monitoring progress..."
    if event is AgentEvent.INSTALLER_EXITED:
        exit_code = payload.get("exitCode")
        if exit_code is None:
            return "Installer process exited."
        return f"Installer process exited with code {exit_code}."
    if event is AgentEvent.COLLECTION_COMPLETE:
        status = payload.get("status")
        if status:
            return f"Evidence collection complete. Status: {status}."
        return "Evidence collection complete."
    if event is AgentEvent.REPORT_WRITE_FAILURE:
        return "Warning: report write failed. Check logs for details."
    return None
