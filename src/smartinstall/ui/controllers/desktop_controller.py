"""Desktop application controller (UI orchestration)."""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QFileDialog, QWidget

from smartinstall.agent.di.container import ServiceContainer
from smartinstall.agent.monitoring.completion_notifications import build_completion_notification
from smartinstall.agent.intake.installer_discovery import DiscoveredInstaller, InstallerDiscovery
from smartinstall.agent.orchestration.automated_run_orchestrator import AutomatedRunResult
from smartinstall.agent.slm.diagnosis_policy import (
    actionable_install_errors,
    should_run_slm_diagnosis,
)
from smartinstall.agent.slm.rag_engine import RagDiagnosisConfig, RagDiagnosisResult
from smartinstall.core.enums.installation import InstallerType
from smartinstall.core.models.requests import StartSessionRequest
from smartinstall.ui.bridge.event_bridge import QtEventBridge
from smartinstall.ui.models.chat_message import ChatMessage
from smartinstall.ui.services.chat_formatter import ChatFormatter
from smartinstall.ui.workers.install_worker import InstallWorkflowWorker
from smartinstall.ui.workers.slm_worker import SlmDiagnosisWorker
from smartinstall.ui.workers.thread_lifecycle import stop_qthread, wire_worker_lifetime


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
        self.on_installation_complete: Callable[[dict], None] | None = None
        self.on_slm_completed: Callable[[str, list[str]], None] | None = None
        self._last_slm_answer: str = ""
        self._last_slm_sources: list[str] = []
        self._pending_completion: dict | None = None

        self._event_bridge.status_update.connect(self._emit_status)

    @property
    def event_bridge(self) -> QtEventBridge:
        return self._event_bridge

    @property
    def is_busy(self) -> bool:
        return self._busy

    def build_rag_config(self) -> RagDiagnosisConfig:
        return self._build_rag_config()

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

    def run_bundled_test_install(self, scenario_id: str) -> None:
        """Launch bundled TestAppSetup.exe with a failure-injection scenario."""
        if self._busy:
            self._emit(self._formatter.error_message("Please wait until the current workflow finishes."))
            return

        from smartinstall.agent.infrastructure.bundled_assets import (
            bundled_test_app_path,
            ensure_bundled_assets,
        )

        ensure_bundled_assets()
        test_app = bundled_test_app_path()
        if test_app is None or not test_app.is_file():
            dev_candidate = self._config.installers_dir / "TestAppSetup.exe"
            if dev_candidate.is_file():
                test_app = dev_candidate
            else:
                self._emit(
                    self._formatter.error_message(
                        "TestAppSetup.exe not found. Rebuild with scripts\\build_desktop.ps1 "
                        "or run failure_harness\\scripts\\build_test_installer.ps1."
                    )
                )
                return

        try:
            from failure_harness.scenario_manager import ScenarioManager

            manager = ScenarioManager.from_harness_config()
            scenario = manager.load_scenario(scenario_id)
        except Exception as exc:  # noqa: BLE001
            self._emit(self._formatter.error_message(f"Could not load scenario '{scenario_id}': {exc}"))
            return

        runtime_dir = self._config.output_root / "runtime_scenarios"
        runtime_dir.mkdir(parents=True, exist_ok=True)
        scenario_file = runtime_dir / f"{scenario.scenario_id}_ui.json"
        scenario_file.write_text(scenario.model_dump_json(by_alias=True, indent=2), encoding="utf-8")

        args = subprocess.list2cmdline(["--scenario", str(scenario_file.resolve())])
        self._set_busy(True)
        self._emit(
            self._formatter.status_update(
                f"Starting bundled test install — scenario `{scenario.scenario_id}`..."
            )
        )
        stop_qthread(self._install_worker, wait_ms=5_000)
        stop_qthread(self._slm_worker, wait_ms=5_000)
        self._install_worker = InstallWorkflowWorker(
            self._container,
            self._event_bridge,
            installer_name=test_app.name,
            product_name="TestApp Failure Injection",
            additional_args=args,
            timeout_seconds=scenario.install_timeout_seconds,
            parent=self,
        )
        wire_worker_lifetime(
            self._install_worker,
            on_finished=lambda: setattr(self, "_install_worker", None),
        )
        self._install_worker.succeeded.connect(self._on_install_succeeded)
        self._install_worker.failed.connect(self._on_install_failed)
        self._install_worker.start()

    def start_install_from_path(self, installer_path: Path) -> None:
        self._set_busy(True)
        self._emit(
            self._formatter.status_update(
                f"Starting monitored installation from `{installer_path.name}`..."
            )
        )
        self._start_install_worker(installer_path=installer_path.resolve())

    def shutdown_workers(self, *, wait_ms: int = 30_000) -> None:
        """Stop install and SLM threads before application exit."""
        stop_qthread(self._install_worker, wait_ms=wait_ms)
        stop_qthread(self._slm_worker, wait_ms=wait_ms)
        self._install_worker = None
        self._slm_worker = None

    def _start_install_worker(
        self,
        *,
        installer_name: str | None = None,
        installer_path: Path | None = None,
    ) -> None:
        stop_qthread(self._install_worker, wait_ms=5_000)
        stop_qthread(self._slm_worker, wait_ms=5_000)

        if installer_path is not None:
            self._install_worker = _ExplicitPathInstallWorker(
                self._container,
                self._event_bridge,
                installer_path=installer_path,
                parent=self,
            )
        else:
            self._install_worker = InstallWorkflowWorker(
                self._container,
                self._event_bridge,
                installer_name=installer_name,
                parent=self,
            )

        wire_worker_lifetime(
            self._install_worker,
            on_finished=lambda: setattr(self, "_install_worker", None),
        )
        self._install_worker.succeeded.connect(self._on_install_succeeded)
        self._install_worker.failed.connect(self._on_install_failed)
        self._install_worker.start()

    def _on_install_succeeded(self, payload: object) -> None:
        run_result: AutomatedRunResult = payload  # type: ignore[assignment]
        self._emit(
            self._formatter.installation_summary(
                run_result.report,
                str(run_result.report_path),
            )
        )
        if self.on_run_completed is not None:
            self.on_run_completed(run_result)

        actionable = actionable_install_errors(run_result.report.errors)
        err_message = actionable[0].message if actionable else ""
        completion = build_completion_notification(
            session_id=run_result.session.session_id,
            installer_name=run_result.discovered.file_name,
            outcome=run_result.report.status.installation_outcome,
            report_path=str(run_result.report_path),
            has_errors=bool(actionable),
            mode="manual",
            error_code=actionable[0].code if actionable else "",
            error_message=err_message,
            suggested_fix=_suggest_fix_from_error_message(err_message) if err_message else "",
        )
        if self._config.auto_run_slm and self._needs_slm_diagnosis(run_result):
            self._pending_completion = completion
            self._start_slm(run_result.report_path)
        else:
            if self.on_installation_complete is not None:
                self.on_installation_complete(completion)
            self._set_busy(False)

    def _on_install_failed(self, message: str) -> None:
        self._emit(self._formatter.error_message(message))
        self._set_busy(False)

    def _start_slm(self, report_path: Path) -> None:
        self._emit(self._formatter.status_update("Running local AI troubleshooting..."))
        stop_qthread(self._slm_worker, wait_ms=5_000)
        self._slm_worker = SlmDiagnosisWorker(
            report_path,
            self._build_rag_config(),
            parent=self,
        )
        wire_worker_lifetime(
            self._slm_worker,
            on_finished=lambda: setattr(self, "_slm_worker", None),
        )
        self._slm_worker.succeeded.connect(self._on_slm_succeeded)
        self._slm_worker.failed.connect(self._on_slm_failed)
        self._slm_worker.start()

    def _on_slm_succeeded(self, payload: object) -> None:
        diagnosis: RagDiagnosisResult = payload  # type: ignore[assignment]
        self._last_slm_answer = diagnosis.answer
        self._last_slm_sources = list(diagnosis.sources)
        self._emit(self._formatter.slm_diagnosis(diagnosis.answer, diagnosis.sources))
        if self._pending_completion is not None:
            self._pending_completion["slmAnswer"] = diagnosis.answer
            self._pending_completion["slmSources"] = list(diagnosis.sources)
            if self.on_installation_complete is not None:
                self.on_installation_complete(self._pending_completion)
            self._pending_completion = None
        elif self.on_slm_completed is not None:
            self.on_slm_completed(diagnosis.answer, diagnosis.sources)
        self._set_busy(False)

    def _on_slm_failed(self, message: str) -> None:
        self._emit(
            self._formatter.error_message(
                f"SLM diagnosis failed: {message}\n"
                "Ensure Ollama is running and required models are installed."
            )
        )
        if self._pending_completion is not None:
            if self.on_installation_complete is not None:
                self.on_installation_complete(self._pending_completion)
            self._pending_completion = None
        self._set_busy(False)

    @staticmethod
    def _needs_slm_diagnosis(run_result: AutomatedRunResult) -> bool:
        return should_run_slm_diagnosis(run_result.report)

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


def _suggest_fix_from_error_message(message: str) -> str:
    lowered = message.lower()
    if "access denied" in lowered:
        return "Run installer as Administrator."
    if "visual c++" in lowered or "vcruntime" in lowered:
        return "Install Microsoft Visual C++ Redistributable."
    if ".net" in lowered:
        return "Install required .NET Framework runtime."
    if "1618" in lowered:
        return "Wait for other MSI operations to complete, then retry."
    return "Open Troubleshooting for full AI analysis."


class _ExplicitPathInstallWorker(InstallWorkflowWorker):
    """Install worker for explicit installer paths outside installers/."""

    def __init__(
        self,
        container: ServiceContainer,
        event_bridge: QtEventBridge,
        *,
        installer_path: Path,
        parent=None,
    ) -> None:
        super().__init__(container, event_bridge, parent=parent)
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
