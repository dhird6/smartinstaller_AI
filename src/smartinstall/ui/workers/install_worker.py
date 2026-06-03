"""Background worker for monitored installation workflow."""

from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from smartinstall.agent.di.container import ServiceContainer
from smartinstall.agent.orchestration.automated_run_orchestrator import AutomatedRunResult
from smartinstall.ui.bridge.event_bridge import QtEventBridge


class InstallWorkflowWorker(QThread):
    """Runs AutomatedRunOrchestrator off the UI thread."""

    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        container: ServiceContainer,
        event_bridge: QtEventBridge,
        *,
        installer_name: str | None = None,
        product_name: str | None = None,
        additional_args: str | None = None,
        timeout_seconds: int | None = None,
    ) -> None:
        super().__init__()
        self._container = container
        self._event_bridge = event_bridge
        self._installer_name = installer_name
        self._product_name = product_name
        self._additional_args = additional_args
        self._timeout_seconds = timeout_seconds

    def run(self) -> None:
        self._event_bridge.attach()
        try:
            result = self._container.automated_run_orchestrator.run(
                installer_name=self._installer_name,
                product_name=self._product_name,
                additional_args=self._additional_args,
                timeout_seconds=self._timeout_seconds,
            )
            if not result.success or result.value is None:
                message = "Installation workflow failed."
                if result.error is not None:
                    message = result.error.message
                self.failed.emit(message)
                return
            run_result: AutomatedRunResult = result.value
            self.succeeded.emit(run_result)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))
        finally:
            self._event_bridge.detach()
