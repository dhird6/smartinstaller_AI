"""Enterprise application shell — CCTech branded SaaS-quality desktop UI."""



from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QHBoxLayout, QMainWindow, QStackedWidget, QVBoxLayout, QWidget

from smartinstall.agent.monitoring.completion_notifications import is_completion_notification
from smartinstall.agent.monitoring.monitoring_state_store import MonitoringPlatformState
from smartinstall.agent.orchestration.automated_run_orchestrator import AutomatedRunResult
from smartinstall.agent.services.background_monitor_service import BackgroundMonitorService
from smartinstall.agent.slm.rag_engine import RagDiagnosisResult
from smartinstall.ui.controllers.desktop_controller import DesktopController
from smartinstall.ui.dialogs.install_complete_dialog import InstallCompleteDialog
from smartinstall.ui.dialogs.install_detected_dialog import InstallDetectedDialog
from smartinstall.ui.dialogs.installation_details_dialog import InstallationDetailsDialog
from smartinstall.ui.dialogs.smart_error_dialog import SmartErrorDialog
from smartinstall.agent.monitoring.monitoring_state_store import (
    ActiveInstallationState,
    CompletedInstallationState,
)
from smartinstall.ui.models.chat_message import ChatMessage, ChatRole
from smartinstall.ui.services.run_result_loader import load_run_result_from_report
from smartinstall.ui.workers.slm_worker import SlmDiagnosisWorker
from smartinstall.ui.workers.thread_lifecycle import stop_qthread, wire_worker_lifetime
from smartinstall.ui.pages.dashboard_page import DashboardPage
from smartinstall.ui.pages.full_chat_page import FullChatPage
from smartinstall.ui.pages.installation_center_page import InstallationCenterPage
from smartinstall.ui.pages.monitoring_page import MonitoringPage
from smartinstall.ui.pages.troubleshooting_page import TroubleshootingPage
from smartinstall.ui.workers.background_sync_worker import BackgroundSyncWorker

from smartinstall.ui.resources.brand_assets import load_brand_logo_pixmap

from smartinstall.ui.services.session_stats_service import load_dashboard_stats

from smartinstall.ui.shell.floating_chat_widget import FloatingChatWidget

from smartinstall.ui.shell.sidebar_nav import SidebarNav

from smartinstall.ui.shell.top_header import TopHeader

from smartinstall.ui.theme.cctech_theme import CCTechPalette

from smartinstall.ui.widgets.chat_panel import ChatPanel





class MainShell(QMainWindow):

    """CCTech × SmartInstall AI enterprise shell."""



    PAGE_DASHBOARD = 0
    PAGE_MONITORING = 1
    PAGE_TROUBLESHOOTING = 2
    PAGE_INSTALLATION_CENTER = 3
    PAGE_FULL_CHAT = 4

    _PAGE_TITLES = (
        "Home Dashboard",
        "Live Monitoring",
        "Troubleshooting",
        "Installation Center",
        "Full Chat AI Workspace",
    )



    def __init__(
        self,
        controller: DesktopController,
        palette: CCTechPalette,
        *,
        background_service: BackgroundMonitorService | None = None,
    ) -> None:
        super().__init__()
        self._controller = controller
        self._background_service = background_service
        self._palette = palette

        self._last_run: AutomatedRunResult | None = None

        self._last_slm_answer: str | None = None

        self._last_slm_sources: list[str] = []

        self._current_page = self.PAGE_DASHBOARD



        self._chat = ChatPanel(palette, variant="light")

        self._sidebar = SidebarNav(palette)

        self._floating_chat = FloatingChatWidget(palette)

        self._header = TopHeader(palette)

        self._dashboard = DashboardPage(palette)

        self._monitoring = MonitoringPage(palette)

        self._troubleshooting = TroubleshootingPage(palette)
        self._installation_center = InstallationCenterPage(palette)
        self._full_chat = FullChatPage(palette)
        self._stack = QStackedWidget()
        self._sync_worker: BackgroundSyncWorker | None = None
        self._tray: object | None = None
        self._completed_notification_sessions: set[str] = set()
        self._slm_pending_sessions: set[str] = set()
        self._live_monitoring_sessions: set[str] = set()
        self._slm_worker: SlmDiagnosisWorker | None = None
        self._active_session_id: str = ""
        self._live_error_slm_armed: bool = False

        self._build_ui()

        self._wire_events()

        self._mount_chat_floating()

        self._refresh_dashboard()

        controller.show_welcome()

    def set_tray_controller(self, tray: object) -> None:
        self._tray = tray

    def _build_ui(self) -> None:

        self.setWindowTitle("SmartInstall AI — CCTech")

        self.resize(1480, 920)

        self.setMinimumSize(1100, 680)

        self.setWindowIcon(QIcon(load_brand_logo_pixmap(32)))



        self._central_host = QWidget()

        self.setCentralWidget(self._central_host)

        root = QHBoxLayout(self._central_host)

        root.setContentsMargins(0, 0, 0, 0)

        root.setSpacing(0)

        root.addWidget(self._sidebar)



        center_wrap = QWidget()

        center_wrap.setObjectName("centerWrap")

        center_wrap.setStyleSheet(f"background: {self._palette.canvas};")

        center_outer = QVBoxLayout(center_wrap)

        center_outer.setContentsMargins(0, 0, 0, 0)

        center_outer.setSpacing(0)



        center_outer.addWidget(self._header)



        content = QWidget()

        content_layout = QVBoxLayout(content)

        content_layout.setContentsMargins(0, 0, 0, 0)

        self._stack.addWidget(self._dashboard)

        self._stack.addWidget(self._monitoring)

        self._stack.addWidget(self._troubleshooting)
        self._stack.addWidget(self._installation_center)
        self._stack.addWidget(self._full_chat)

        self._monitoring.set_idle()

        content_layout.addWidget(self._stack)

        center_outer.addWidget(content, stretch=1)



        self._floating_chat.setParent(center_wrap)
        self._floating_chat.show()
        self._floating_chat.raise_()
        self._floating_chat.reposition()



        root.addWidget(center_wrap, stretch=1)



        self._build_menu()

        self._navigate(self.PAGE_DASHBOARD)



    def _build_menu(self) -> None:

        file_menu = self.menuBar().addMenu("&File")

        exit_action = QAction("E&xit", self)

        exit_action.triggered.connect(self.close)

        file_menu.addAction(exit_action)

        view_menu = self.menuBar().addMenu("&View")

        for label, page in (

            ("&Home Dashboard", self.PAGE_DASHBOARD),

            ("&Monitoring", self.PAGE_MONITORING),

            ("&Troubleshooting", self.PAGE_TROUBLESHOOTING),
            ("&Installation Center", self.PAGE_INSTALLATION_CENTER),
            ("&Full Chat", self.PAGE_FULL_CHAT),

        ):

            action = QAction(label, self)

            action.triggered.connect(lambda checked=False, p=page: self._navigate(p))

            view_menu.addAction(action)

        view_menu.addSeparator()

        ai_action = QAction("&AI Assistant", self)

        ai_action.triggered.connect(self._floating_chat.open_compact)

        view_menu.addAction(ai_action)



    def _wire_events(self) -> None:

        self._controller.on_message = self._on_chat_message

        self._chat.message_submitted.connect(self._on_user_message)

        self._chat.prompt_chosen.connect(self._on_prompt_chosen)

        self._controller.event_bridge.status_update.connect(self._on_status)

        self._sidebar.page_selected.connect(self._navigate)

        self._dashboard.monitoring_requested.connect(
            lambda: self._navigate(self.PAGE_MONITORING)
        )
        self._dashboard.installation_center_requested.connect(
            lambda: self._navigate(self.PAGE_INSTALLATION_CENTER)
        )
        self._installation_center.browse_requested.connect(
            lambda: self._controller.browse_and_install(self)
        )
        self._installation_center.upload_requested.connect(
            lambda: self._controller.upload_installer(self)
        )
        self._installation_center.manual_monitor_requested.connect(
            lambda: self._controller.browse_and_install(self)
        )
        self._controller.event_bridge.live_log_line.connect(self._monitoring.append_log)
        self._controller.event_bridge.stage_changed.connect(self._monitoring.set_stage)
        self._controller.event_bridge.installation_detected.connect(self._on_installation_detected_log)
        self._controller.event_bridge.live_monitoring_started.connect(self._on_live_monitoring_started)
        self._controller.event_bridge.installation_error.connect(self._on_installation_error_logged)
        self._monitoring.view_details_requested.connect(self._show_installation_details)
        self._monitoring.export_logs_requested.connect(self._monitoring.export_logs_dialog)
        self._monitoring.open_troubleshooting_requested.connect(
            lambda: self._navigate(self.PAGE_TROUBLESHOOTING)
        )
        if self._background_service is not None:
            self._sync_worker = BackgroundSyncWorker(self._background_service, parent=self)
            self._sync_worker.setObjectName("BackgroundSyncWorker")
            self._sync_worker.state_updated.connect(self._on_platform_state)
            self._sync_worker.notification_pending.connect(self._on_pending_notification)
            self._sync_worker.start()



    def _mount_chat_floating(self) -> None:

        self._full_chat.detach_chat()

        self._floating_chat.detach_chat()

        self._floating_chat.attach_chat(self._chat)



    def _mount_chat_full_page(self) -> None:

        self._floating_chat.close_chat()

        self._floating_chat.detach_chat()

        self._full_chat.detach_chat()

        self._full_chat.attach_chat(self._chat)



    def resizeEvent(self, event) -> None:  # noqa: N802

        super().resizeEvent(event)

        self._floating_chat.reposition()



    def _navigate(self, index: int) -> None:

        if index < 0 or index >= self._stack.count():

            return

        self._current_page = index

        self._stack.setCurrentIndex(index)

        self._sidebar.set_active_page(index)

        self._header.set_page_title(self._PAGE_TITLES[index])



        if index == self.PAGE_FULL_CHAT:

            self._mount_chat_full_page()
            self._floating_chat.hide()
            self._full_chat.clear_error_notice()

        else:

            self._mount_chat_floating()
            self._floating_chat.show()
            self._floating_chat.raise_()
            self._floating_chat.reposition()

        if index == self.PAGE_TROUBLESHOOTING and self._last_run is not None:
            self._troubleshooting.apply_run_result(
                self._last_run,
                slm_answer=self._last_slm_answer,
                slm_sources=self._last_slm_sources,
                slm_status="ready" if self._last_slm_answer else "none",
            )



    def _on_prompt_chosen(self, text: str) -> None:

        if self._current_page != self.PAGE_FULL_CHAT and not self._floating_chat.is_open:

            self._floating_chat.open_compact()

        self._on_user_message(text)



    def _on_user_message(self, text: str) -> None:

        self._chat.append_message(ChatMessage(role=ChatRole.USER, content=text))

        on_full_chat = self._current_page == self.PAGE_FULL_CHAT

        if not on_full_chat:
            self._monitoring.set_busy("Installation in progress…")
            self._navigate(self.PAGE_MONITORING)

        self._controller.handle_user_input(text, self)

        self._chat.set_input_enabled(not self._controller.is_busy)

        if not on_full_chat and not self._floating_chat.is_open:
            self._floating_chat.open_compact()



    def _on_chat_message(self, message: ChatMessage) -> None:

        self._chat.append_message(message)

        self._chat.set_input_enabled(not self._controller.is_busy)

        if message.role is ChatRole.SYSTEM:
            self._monitoring.append_log(message.content)
            lower = message.content.lower()
            if any(tok in lower for tok in ("error", "failed", "failure", "exception")):
                self._full_chat.show_error_notice(message.content)
            elif self._current_page == self.PAGE_FULL_CHAT:
                self._full_chat.clear_error_notice()



    def _on_status(self, message: str) -> None:
        short = message[:80]
        self._floating_chat.set_context(short)
        self._full_chat.set_context(short)
        if self._active_session_id or self._controller.is_busy:
            self._monitoring.set_busy(message)
        self._monitoring.append_log(message)
        if self._background_service is not None and self._active_session_id:
            state = self._background_service.state_store.load()
            for item in state.active_installations:
                if item.session_id == self._active_session_id:
                    item.stage = message[:120]
            self._background_service.state_store.save(state)



    def _refresh_dashboard(self, platform_state: MonitoringPlatformState | None = None) -> None:
        config = self._controller._config  # noqa: SLF001
        if platform_state is None and self._background_service is not None:
            platform_state = self._background_service.state_store.load()
        stats = load_dashboard_stats(
            sessions_dir=config.output_root,
            reports_dir=config.reports_dir,
            platform_state=platform_state,
        )
        self._dashboard.refresh(stats)

    def _on_platform_state(self, state: object) -> None:
        if isinstance(state, MonitoringPlatformState):
            self._refresh_dashboard(state)
            if self._tray is not None and hasattr(self._tray, "update_from_state"):
                self._tray.update_from_state(state)  # type: ignore[union-attr]
            if state.active_installations:
                active = state.active_installations[0]
                busy_msg = f"Monitoring {active.installer_name}"
                if not self._active_session_id:
                    self._monitoring.begin_monitoring(
                        installer_name=active.installer_name,
                        session_id=active.session_id,
                        pid=active.pid,
                        mode=active.mode,
                    )
                self._monitoring.set_busy(busy_msg)
                self._monitoring.set_stage(active.stage)
                self._monitoring.set_process_info(f"pid={active.pid}  ·  {active.mode}")
                self._monitoring.set_start_time(active.started_at)
                if self._current_page != self.PAGE_MONITORING:
                    self._monitoring.append_log(f"[auto] {busy_msg} — {active.stage}")

    def _bring_to_front(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _on_installation_detected_log(self, message: str) -> None:
        self._monitoring.append_log(message)

    def _on_live_monitoring_started(self, payload: dict) -> None:
        """First popup per install: live monitoring has started (Explorer or Installation Center)."""
        session_id = str(payload.get("sessionId", ""))
        installer_name = str(payload.get("installerName", "installer"))
        if not session_id:
            return
        if session_id in self._live_monitoring_sessions:
            return
        self._live_monitoring_sessions.add(session_id)
        self._active_session_id = session_id
        self._live_error_slm_armed = False

        detail = str(payload.get("detail", ""))
        mode = str(payload.get("mode", "automatic"))
        mode_label = (
            "Automatic (installer launched outside Smart Installer)"
            if mode in {"automatic", "passive"}
            else "Manual (Installation Center / Browse)"
        )
        pid = int(payload.get("pid", 0) or 0)
        started_at = str(payload.get("startedAt", ""))

        self._monitoring.begin_monitoring(
            installer_name=installer_name,
            session_id=session_id,
            pid=pid,
            mode=mode,
        )
        if started_at:
            self._monitoring.set_start_time(started_at)
        busy = f"Live monitoring: {installer_name}"
        self._monitoring.set_busy(busy)
        self._monitoring.append_log(detail or busy)
        self._sync_active_installation(payload)
        self._navigate(self.PAGE_MONITORING)
        self._bring_to_front()

        if self._tray is not None and hasattr(self._tray, "notify"):
            self._tray.notify(  # type: ignore[union-attr]
                "SmartInstall AI — Live Monitoring",
                f"Monitoring {installer_name} in real time.",
            )

        dialog = InstallDetectedDialog(
            self._palette,
            installer_name=installer_name,
            detail=detail,
            mode_label=mode_label,
            parent=self,
        )
        dialog.view_monitoring.connect(lambda: self._navigate(self.PAGE_MONITORING))
        dialog.exec()

    def _on_installation_error_logged(self, payload: dict) -> None:
        message = str(payload.get("message", "Installation error"))
        code = str(payload.get("code", ""))
        self._monitoring.append_log(f"ERROR {code}: {message}")
        self._monitoring.set_installation_status("Failed")
        self._monitoring.assistance_panel.add_troubleshooting_hint(
            f"{code}: {message[:200]}",
            _suggest_fix_from_message(message),
        )
        if self._controller._config.auto_run_slm and not self._live_error_slm_armed:  # noqa: SLF001
            self._live_error_slm_armed = True
            self._monitoring.assistance_panel.set_slm_running()

    def _on_pending_notification(self, payload: object) -> None:
        if isinstance(payload, dict) and is_completion_notification(payload):
            self.handle_installation_complete(payload)

    def handle_installation_complete(self, payload: dict) -> None:
        """One completion popup + troubleshooting/SLM update per installation session."""
        session_id = str(payload.get("sessionId", ""))
        if not session_id:
            session_id = str(payload.get("reportPath", "")) or str(
                payload.get("installerName", "")
            )
        if not session_id or session_id in self._completed_notification_sessions:
            return

        config = self._controller._config  # noqa: SLF001
        has_errors = bool(payload.get("hasErrors"))
        outcome = str(payload.get("outcome", "")).lower()
        failed = has_errors or outcome in {"failed", "failure", "error"}
        slm_answer = str(payload.get("slmAnswer", "") or "")
        slm_sources = list(payload.get("slmSources") or [])

        if (
            failed
            and config.auto_run_slm
            and not slm_answer
            and session_id not in self._slm_pending_sessions
        ):
            report_path = Path(str(payload.get("reportPath", "")))
            if report_path.is_file():
                self._slm_pending_sessions.add(session_id)
                self._start_background_slm_worker(report_path, payload, session_id)
                return

        self._completed_notification_sessions.add(session_id)
        self._slm_pending_sessions.discard(session_id)
        self._live_monitoring_sessions.discard(session_id)
        self._active_session_id = ""
        self._live_error_slm_armed = False

        report_path = Path(str(payload.get("reportPath", "")))
        run_result = load_run_result_from_report(report_path) if report_path.is_file() else None
        if run_result is not None:
            self._apply_run_to_workspace(
                run_result,
                slm_answer=slm_answer or None,
                slm_sources=slm_sources,
            )
            if slm_answer:
                self._monitoring.assistance_panel.apply_slm(
                    slm_answer,
                    confidence=0.85 if failed else None,
                )

        self._record_completed_installation(payload, failed=failed)
        self._bring_to_front()
        installer_name = str(payload.get("installerName", "Installer"))

        if failed:
            self._show_failure_completion_popup(payload, slm_answer=slm_answer)
            self._navigate(self.PAGE_TROUBLESHOOTING)
            if self._tray is not None and hasattr(self._tray, "notify"):
                self._tray.notify(  # type: ignore[union-attr]
                    "Installation needs attention",
                    f"{installer_name}: see AI troubleshooting in the app.",
                )
        else:
            self._show_success_completion_popup(payload)
            self._navigate(self.PAGE_MONITORING)
            if self._tray is not None and hasattr(self._tray, "notify"):
                self._tray.notify(  # type: ignore[union-attr]
                    "Installation Complete",
                    f"{installer_name} finished successfully.",
                )

    def _start_background_slm_worker(
        self,
        report_path: Path,
        payload: dict,
        session_id: str,
    ) -> None:
        stop_qthread(self._slm_worker, wait_ms=5_000)
        worker = SlmDiagnosisWorker(
            report_path,
            self._controller.build_rag_config(),
            parent=self,
        )
        self._slm_worker = worker
        wire_worker_lifetime(
            worker,
            on_finished=lambda: setattr(self, "_slm_worker", None),
        )
        worker.succeeded.connect(
            lambda result, p=payload, sid=session_id: self._on_background_slm_done(
                result, p, sid
            )
        )
        worker.failed.connect(
            lambda _msg, p=payload, sid=session_id: self._on_background_slm_failed(p, sid)
        )
        worker.start()

    def _on_background_slm_done(self, result: object, payload: dict, session_id: str) -> None:
        self._slm_pending_sessions.discard(session_id)
        if isinstance(result, RagDiagnosisResult):
            payload = dict(payload)
            payload["slmAnswer"] = result.answer
            payload["slmSources"] = list(result.sources)
        self.handle_installation_complete(payload)

    def _on_background_slm_failed(self, payload: dict, session_id: str) -> None:
        self._slm_pending_sessions.discard(session_id)
        self.handle_installation_complete(payload)

    def _show_failure_completion_popup(self, payload: dict, *, slm_answer: str) -> None:
        dialog = SmartErrorDialog(
            self._palette,
            title=str(payload.get("installerName", "Installation")),
            error_code=str(payload.get("errorCode", "")),
            error_message=str(payload.get("errorMessage", "Installation failed")),
            root_cause="Installation completed with errors",
            suggested_solution=str(
                payload.get("suggestedFix") or "Review the Troubleshooting page for full analysis."
            ),
            confidence=0.85 if slm_answer else 0.75,
            session_id=str(payload.get("sessionId", "")),
            slm_summary=slm_answer,
            parent=self,
        )
        dialog.view_details.connect(self._show_installation_details)
        dialog.open_troubleshooting.connect(lambda: self._navigate(self.PAGE_TROUBLESHOOTING))
        dialog.open_dashboard.connect(lambda _: self._navigate(self.PAGE_TROUBLESHOOTING))
        dialog.exec()

    def _show_success_completion_popup(self, payload: dict) -> None:
        error_count = 0
        if self._last_run is not None:
            error_count = len(self._last_run.report.errors)
        dialog = InstallCompleteDialog(
            self._palette,
            installer_name=str(payload.get("installerName", "Installer")),
            outcome=str(payload.get("outcome", "Success")),
            report_path=str(payload.get("reportPath", "")),
            error_count=error_count,
            parent=self,
        )
        dialog.view_details.connect(self._show_installation_details)
        dialog.open_monitoring.connect(lambda: self._navigate(self.PAGE_MONITORING))
        dialog.exec()

    def _show_installation_details(self) -> None:
        if self._last_run is None:
            return
        dialog = InstallationDetailsDialog(
            self._palette,
            run_result=self._last_run,
            slm_answer=self._last_slm_answer or "",
            parent=self,
        )
        dialog.exec()

    def _sync_active_installation(self, payload: dict) -> None:
        if self._background_service is None:
            return
        session_id = str(payload.get("sessionId", ""))
        if not session_id:
            return
        self._background_service.state_store.upsert_active(
            ActiveInstallationState(
                session_id=session_id,
                installer_name=str(payload.get("installerName", "Installer")),
                installer_path=str(payload.get("installerPath", "")),
                pid=int(payload.get("pid", 0) or 0),
                stage="Monitoring",
                started_at=str(payload.get("startedAt", "")),
                mode=str(payload.get("mode", "manual")),
            )
        )

    def _record_completed_installation(self, payload: dict, *, failed: bool) -> None:
        if self._background_service is None:
            return
        session_id = str(payload.get("sessionId", ""))
        if session_id:
            self._background_service.state_store.remove_active(session_id)
        self._background_service.state_store.record_completed(
            CompletedInstallationState(
                session_id=session_id,
                installer_name=str(payload.get("installerName", "Installer")),
                outcome=str(payload.get("outcome", "")),
                report_path=str(payload.get("reportPath", "")) or None,
                error_summary=str(payload.get("errorMessage", "")) if failed else None,
                completed_at="",
                mode=str(payload.get("mode", "manual")),
            )
        )

    def _apply_run_to_workspace(
        self,
        result: AutomatedRunResult,
        *,
        slm_answer: str | None = None,
        slm_sources: list[str] | None = None,
    ) -> None:
        self._last_run = result
        if slm_answer:
            self._last_slm_answer = slm_answer
            self._last_slm_sources = slm_sources or []

        outcome = result.report.status.installation_outcome.lower()
        if outcome in {"success", "completed"}:
            self._monitoring.set_success(result)
        elif outcome in {"failed", "failure", "error"}:
            self._monitoring.set_error(result)
        else:
            self._monitoring.apply_run_result(result)

        self._troubleshooting.apply_run_result(
            result,
            slm_answer=slm_answer,
            slm_sources=slm_sources,
            slm_status="ready" if slm_answer else "none",
        )
        self._refresh_dashboard()
        ctx = result.discovered.file_name
        self._floating_chat.set_context(ctx)
        self._full_chat.set_context(ctx)

    def closeEvent(self, event) -> None:  # noqa: N802
        if self._controller._config.minimize_to_tray:  # noqa: SLF001
            event.ignore()
            self.hide()
            if self._tray is not None and hasattr(self._tray, "notify"):
                self._tray.notify(  # type: ignore[union-attr]
                    "Smart Install AI",
                    "Still monitoring in the background. Double-click the tray icon to reopen.",
                )
            return
        self._shutdown_workers()
        super().closeEvent(event)

    def _shutdown_workers(self) -> None:
        if self._sync_worker is not None:
            self._sync_worker.requestInterruption()
            self._sync_worker.wait(3000)
        stop_qthread(self._slm_worker, wait_ms=60_000)
        self._slm_worker = None
        self._controller.shutdown_workers(wait_ms=60_000)
        if self._background_service is not None:
            self._background_service.stop()



    def on_run_completed(

        self,

        result: AutomatedRunResult,

        *,

        slm_answer: str | None = None,

        slm_sources: list[str] | None = None,

    ) -> None:

        self._last_run = result

        self._last_slm_answer = slm_answer

        self._last_slm_sources = slm_sources or []

        outcome = result.report.status.installation_outcome.lower()

        if outcome in {"success", "completed"}:

            self._monitoring.set_success(result)

        elif outcome in {"failed", "failure", "error"}:

            self._monitoring.set_error(result)
            reason = (
                result.report.status.failure_reason
                or "Installation failed — open Troubleshooting or ask in Full Chat."
            )
            self._full_chat.show_error_notice(reason)

        else:

            self._monitoring.apply_run_result(result)

        needs_slm = self._controller._config.auto_run_slm and self._needs_slm_for_result(result)  # noqa: SLF001
        self._troubleshooting.apply_run_result(
            result,
            slm_answer=slm_answer,
            slm_sources=slm_sources,
            slm_status="running" if needs_slm and not slm_answer else ("ready" if slm_answer else "none"),
        )
        if result.report.errors:
            self._monitoring.assistance_panel.apply_errors_from_report(result.report.errors)
        if needs_slm and not slm_answer:
            self._monitoring.assistance_panel.set_slm_running()
        elif slm_answer:
            self._monitoring.assistance_panel.apply_slm(slm_answer)

        self._refresh_dashboard()

        ctx = result.discovered.file_name

        self._floating_chat.set_context(ctx)

        self._full_chat.set_context(ctx)



    def on_slm_completed(self, answer: str, sources: list[str]) -> None:
        """Refresh Troubleshooting when SLM finishes after a manual install."""
        self._last_slm_answer = answer
        self._last_slm_sources = sources
        self._monitoring.assistance_panel.apply_slm(answer)
        if self._last_run is not None:
            self._troubleshooting.apply_run_result(
                self._last_run,
                slm_answer=answer,
                slm_sources=sources,
                slm_status="ready",
            )

    @staticmethod
    def _needs_slm_for_result(result: AutomatedRunResult) -> bool:
        outcome = result.report.status.installation_outcome.lower()
        if outcome in {"failed", "failure", "error"}:
            return True
        return bool(result.report.errors)


def _suggest_fix_from_message(message: str) -> str:
    lowered = message.lower()
    if "visual c++" in lowered or "vcruntime" in lowered:
        return "Install Microsoft Visual C++ Redistributable and retry."
    if ".net" in lowered:
        return "Install .NET Framework 4.8 and retry."
    if "1618" in lowered:
        return "Wait for other MSI operations to complete, then retry."
    return "Review the full AI troubleshooting report in the dashboard."

