"""Desktop application controller (UI orchestration)."""

from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QFileDialog, QWidget

from smartinstall.agent.di.container import ServiceContainer
from smartinstall.agent.intake.installer_discovery import DiscoveredInstaller, InstallerDiscovery
from smartinstall.agent.orchestration.automated_run_orchestrator import AutomatedRunResult
from smartinstall.agent.slm.rag_engine import RagDiagnosisConfig, RagDiagnosisResult
from smartinstall.core.enums.installation import InstallerType
from smartinstall.core.models.requests import StartSessionRequest
from smartinstall.ui.bridge.event_bridge import QtEventBridge
from smartinstall.ui.models.chat_message import ChatMessage
from smartinstall.ui.services.chat_formatter import ChatFormatter
from smartinstall.ui.workers.install_worker import InstallWorkflowWorker
from smartinstall.ui.workers.slm_worker import SlmDiagnosisWorker


class DesktopController(QObject):
    """Coordinates chat commands, install workflow, and SLM diagnosis."""

    def __init__(self, container: ServiceContainer, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._container = container
        self._config = container.config
        self._discovery = InstallerDiscovery(self._config.installers_dir)
        self._formatter = ChatFormatter()
        self._event_bridge = QtEventBridge(container.event_bus)
        self._install_worker: InstallWorkflowWorker | None = None
        self._slm_worker: SlmDiagnosisWorker | None = None
        self._busy = False

        self.on_message: Callable[[ChatMessage], None] | None = None
        self.on_run_completed: Callable[[object], None] | None = None
        self.on_slm_completed: Callable[[str, list[str]], None] | None = None
        self.on_slm_failed: Callable[[str], None] | None = None
        self._last_slm_answer: str = ""
        self._last_slm_sources: list[str] = []
        self._last_run_report_path: Path | None = None
        self._last_run_session_id: str = ""

        self._event_bridge.status_update.connect(self._emit_status)

    @property
    def auto_run_slm(self) -> bool:
        return self._config.auto_run_slm

    @property
    def event_bridge(self) -> QtEventBridge:
        return self._event_bridge

    @property
    def is_busy(self) -> bool:
        return self._busy

    def show_welcome(self) -> None:
        self._emit(self._formatter.welcome())

    def handle_user_input(self, text: str, parent_widget: QWidget) -> None:
        if self._busy:
            self._emit(self._formatter.error_message("Please wait until the current workflow finishes."))
            return

        normalized = text.strip()
        if not normalized:
            return

        lowered = normalized.lower()
        if lowered == "list":
            self._list_installers()
            return
        if lowered.startswith("install "):
            installer_name = normalized[8:].strip()
            if installer_name:
                self.start_install(installer_name=installer_name)
            else:
                self.browse_and_install(parent_widget)
            return
        if lowered in {"install", "browse"}:
            self.browse_and_install(parent_widget)
            return

        self._emit(
            self._formatter.error_message(
                "Unknown command. Try `list`, `install <file-name>`, or use Browse Installer."
            )
        )

    def upload_installer(self, parent_widget: QWidget) -> None:
        selected, _ = QFileDialog.getOpenFileName(
            parent_widget,
            "Upload Installer",
            str(self._config.installers_dir),
            "Installers (*.exe *.msi)",
        )
        if not selected:
            return
        source = Path(selected).resolve()
        if source.suffix.lower() not in {".exe", ".msi"}:
            self._emit(self._formatter.error_message("Only .exe and .msi installers are supported."))
            return
        dest = self._config.installers_dir / source.name
        if dest.resolve() == source:
            self._emit(self._formatter.status_update(f"`{source.name}` is already in installers/."))
            return
        try:
            self._config.installers_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, dest)
        except OSError as exc:
            self._emit(self._formatter.error_message(f"Upload failed: {exc}"))
            return
        self._emit(
            self._formatter.status_update(
                f"Uploaded `{source.name}` to installers/. Use Browse to start manual monitoring."
            )
        )

    def browse_and_install(self, parent_widget: QWidget) -> None:
        selected, _ = QFileDialog.getOpenFileName(
            parent_widget,
            "Select Installer",
            str(self._config.installers_dir),
            "Installers (*.exe *.msi)",
        )
        if not selected:
            return
        selected_path = Path(selected)
        if selected_path.parent.resolve() == self._config.installers_dir.resolve():
            self.start_install(installer_name=selected_path.name)
            return
        self.start_install_from_path(selected_path)

    def start_install(self, *, installer_name: str) -> None:
        self._set_busy(True)
        self._emit(
            self._formatter.status_update(f"Starting monitored installation for `{installer_name}`...")
        )
        self._start_install_worker(installer_name=installer_name)

    def start_install_from_path(self, installer_path: Path) -> None:
        self._set_busy(True)
        self._emit(
            self._formatter.status_update(
                f"Starting monitored installation from `{installer_path.name}`..."
            )
        )
        self._start_install_worker(installer_path=installer_path.resolve())

    def _start_install_worker(
        self,
        *,
        installer_name: str | None = None,
        installer_path: Path | None = None,
    ) -> None:
        if installer_path is not None:
            self._install_worker = _ExplicitPathInstallWorker(
                self._container,
                self._event_bridge,
                installer_path=installer_path,
            )
        else:
            self._install_worker = InstallWorkflowWorker(
                self._container,
                self._event_bridge,
                installer_name=installer_name,
            )

        self._install_worker.succeeded.connect(self._on_install_succeeded)
        self._install_worker.failed.connect(self._on_install_failed)
        self._install_worker.start()

    def _on_install_succeeded(self, payload: object) -> None:
        run_result: AutomatedRunResult = payload  # type: ignore[assignment]
        self._last_run_report_path = run_result.report_path
        self._last_run_session_id = run_result.session.session_id
        self._emit(
            self._formatter.installation_summary(
                run_result.report,
                str(run_result.report_path),
            )
        )
        if self.on_run_completed is not None:
            self.on_run_completed(run_result)
        if self._config.auto_run_slm:
            self._start_slm(run_result.report_path)
        else:
            self._set_busy(False)

    def _on_install_failed(self, message: str) -> None:
        self._emit(self._formatter.error_message(message))
        self._set_busy(False)

    def _start_slm(self, report_path: Path) -> None:
        self._emit(self._formatter.status_update("Running local AI troubleshooting..."))
        self._slm_worker = SlmDiagnosisWorker(report_path, self._build_rag_config())
        self._slm_worker.succeeded.connect(self._on_slm_succeeded)
        self._slm_worker.failed.connect(self._on_slm_failed)
        self._slm_worker.start()

    def _on_slm_succeeded(self, payload: object) -> None:
        diagnosis: RagDiagnosisResult = payload  # type: ignore[assignment]
        self._last_slm_answer = diagnosis.answer
        self._last_slm_sources = list(diagnosis.sources)
        self._emit(self._formatter.slm_diagnosis(diagnosis.answer, diagnosis.sources))
        if self.on_slm_completed is not None:
            self.on_slm_completed(diagnosis.answer, diagnosis.sources)
        self._set_busy(False)

    def _on_slm_failed(self, message: str) -> None:
        self._emit(
            self._formatter.error_message(
                f"SLM diagnosis failed: {message}\n"
                "Ensure Ollama is running and required models are installed."
            )
        )
        if self.on_slm_failed is not None:
            self.on_slm_failed(message)
        self._set_busy(False)

    def _list_installers(self) -> None:
        names = [item.file_name for item in self._discovery.list_installers()]
        self._emit(self._formatter.installer_list(names))

    def _emit_status(self, message: str) -> None:
        self._emit(self._formatter.status_update(message))

    def _emit(self, message: ChatMessage) -> None:
        if self.on_message is not None:
            self.on_message(message)

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy

    def _build_rag_config(self) -> RagDiagnosisConfig:
        return RagDiagnosisConfig(
            docs_path=self._config.rag_docs_directory.resolve(),
            llm_model=self._config.slm_model,
            embedding_model=self._config.slm_embedding_model,
            top_k=self._config.slm_top_k,
        )


class _ExplicitPathInstallWorker(InstallWorkflowWorker):
    """Install worker for explicit installer paths outside installers/."""

    def __init__(
        self,
        container: ServiceContainer,
        event_bridge: QtEventBridge,
        *,
        installer_path: Path,
    ) -> None:
        super().__init__(container, event_bridge)
        self._installer_path = installer_path

    def run(self) -> None:
        self._event_bridge.attach()
        try:
            suffix = self._installer_path.suffix.lower()
            installer_type = InstallerType.MSI if suffix == ".msi" else InstallerType.EXE
            request = StartSessionRequest(
                installerPath=str(self._installer_path),
                installerType=installer_type,
                productName=self._installer_path.stem,
                callerTag="desktop-ui",
                outputDirectory=str(self._container.config.output_root),
            )
            install_result = self._container.installation_agent.run_monitored_installation(request)
            if not install_result.success or install_result.value is None:
                message = "Installation workflow failed."
                if install_result.error is not None:
                    message = install_result.error.message
                self.failed.emit(message)
                return

            session, unified = install_result.value
            report_path = self._container.automated_run_orchestrator._publisher.publish(  # noqa: SLF001
                unified,
                application_name=request.product_name or self._installer_path.stem,
            )
            discovered = DiscoveredInstaller(
                path=self._installer_path,
                file_name=self._installer_path.name,
                installer_type=installer_type.value,
                size_bytes=self._installer_path.stat().st_size,
                modified_timestamp=session.start_timestamp,
            )
            self.succeeded.emit(
                AutomatedRunResult(
                    session=session,
                    discovered=discovered,
                    report=unified,
                    report_path=report_path,
                    workflow_status=unified.status.installation_outcome,
                )
            )
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))
        finally:
            self._event_bridge.detach()
