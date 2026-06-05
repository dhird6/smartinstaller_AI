"""Enterprise application shell — CCTech branded SaaS-quality desktop UI."""



from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QApplication, QHBoxLayout, QMainWindow, QStackedWidget, QVBoxLayout, QWidget

from smartinstall.agent.monitoring.completion_notifications import is_completion_notification
from smartinstall.agent.windows.process_focus import focus_process_window
from smartinstall.agent.monitoring.monitoring_state_store import MonitoringPlatformState
from smartinstall.agent.orchestration.automated_run_orchestrator import AutomatedRunResult
from smartinstall.agent.services.background_monitor_service import BackgroundMonitorService
from smartinstall.agent.slm.diagnosis_policy import should_run_slm_diagnosis
from smartinstall.agent.slm.rag_engine import RagDiagnosisResult
from smartinstall.ui.controllers.desktop_controller import DesktopController
from smartinstall.ui.dialogs.exit_confirm_dialog import ExitConfirmDialog
from smartinstall.ui.dialogs.install_complete_dialog import InstallCompleteDialog
from smartinstall.ui.dialogs.install_detected_dialog import InstallDetectedDialog
from smartinstall.ui.dialogs.installation_details_dialog import InstallationDetailsDialog
from smartinstall.ui.dialogs.smart_error_dialog import SmartErrorDialog
from smartinstall.agent.monitoring.monitoring_state_store import (
    ActiveInstallationState,
    CompletedInstallationState,
)
from smartinstall.ui.models.chat_message import ChatMessage, ChatRole
from smartinstall.ui.services.chat_prompt_validator import is_install_command_intent
from smartinstall.ui.services.app_lifecycle import should_confirm_exit
from smartinstall.ui.services.installation_history import load_recent_run_results, merge_run_history
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

from smartinstall.ui.layout.responsive import clamp_window_to_screen, fit_main_window
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
        self._run_history: list[AutomatedRunResult] = []
        self._slm_history_by_session: dict[str, tuple[str | None, list[str] | None, str]] = {}

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
        self._last_platform_fingerprint = ""
        self._pending_stage_message = ""
        self._reflow_timer = QTimer(self)
        self._reflow_timer.setSingleShot(True)
        self._reflow_timer.setInterval(80)
        self._reflow_timer.timeout.connect(self._reflow_responsive_pages)
        self._stage_persist_timer = QTimer(self)
        self._stage_persist_timer.setSingleShot(True)
        self._stage_persist_timer.setInterval(500)
        self._stage_persist_timer.timeout.connect(self._persist_pending_stage)
        self._shutting_down = False
        self._startup_demo_scheduled = False

        self._build_ui()

        self._wire_events()

        self._mount_chat_floating()

        self._refresh_dashboard()

        self._load_run_history_from_disk()
        controller.show_welcome()

    def set_tray_controller(self, tray: object) -> None:
        self._tray = tray

    def launch_startup_demo(self) -> None:
        """
        Sales/demo path: run bundled TestAppSetup immediately using the existing workflow.

        Monitoring stays visible in SmartInstall; the TestApp console is brought to the foreground.
        """
        if self._startup_demo_scheduled or self._controller.is_busy:
            return
        config = self._controller._config  # noqa: SLF001
        if not config.auto_launch_demo_install_on_startup:
            return

        scenario_id = str(config.demo_install_scenario_id or "disk_insufficient_space").strip()
        if not scenario_id:
            scenario_id = "disk_insufficient_space"

        self._startup_demo_scheduled = True
        self._navigate(self.PAGE_MONITORING)
        self._monitoring.append_log("Demo mode: launching bundled TestAppSetup.exe for live monitoring…")
        self._monitoring.set_busy("Demo install: TestAppSetup.exe")
        self._controller.run_bundled_test_install(scenario_id)
        QTimer.singleShot(
            2500,
            lambda: self._focus_demo_installer_window(),
        )

    def _focus_demo_installer_window(self) -> None:
        focused = focus_process_window(
            process_name="TestAppSetup.exe",
            title_hint="TestApp Setup",
            timeout_seconds=20.0,
        )
        if focused:
            self._monitoring.append_log(
                "TestAppSetup.exe is running — SmartInstall AI is monitoring in the background."
            )
            if self._tray is not None and hasattr(self._tray, "notify"):
                self._tray.notify(  # type: ignore[union-attr]
                    "SmartInstall AI demo",
                    "TestAppSetup is running. SmartInstall is monitoring live in the app.",
                )
        else:
            self._monitoring.append_log(
                "Waiting for TestAppSetup.exe window — check Live Monitoring for progress."
            )

    def _build_ui(self) -> None:

        self.setWindowTitle("SmartInstall AI — CCTech")
        fit_main_window(self)

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
        content.setMinimumWidth(0)

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

        exit_action.triggered.connect(self.request_quit)

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
        self._controller.on_install_started = self._on_install_started

        self._chat.message_submitted.connect(self._on_user_message)

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
        self._installation_center.test_install_requested.connect(
            self._controller.run_bundled_test_install
        )
        self._populate_test_scenarios()
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



    def _populate_test_scenarios(self) -> None:
        try:
            from failure_harness.scenario_manager import ScenarioManager

            manager = ScenarioManager.from_harness_config()
            scenarios = [
                (sid, manager.load_scenario(sid).name)
                for sid in manager.list_scenario_ids()
            ]
            self._installation_center.set_test_scenarios(scenarios)
        except Exception:
            self._installation_center.set_test_scenarios(
                [("disk_insufficient_space", "Insufficient Disk Space")]
            )

    def _mount_chat_floating(self) -> None:

        self._full_chat.detach_chat()

        self._floating_chat.detach_chat()

        self._floating_chat.attach_chat(self._chat)



    def _mount_chat_full_page(self) -> None:

        self._floating_chat.close_chat()

        self._floating_chat.detach_chat()

        self._full_chat.detach_chat()

        self._full_chat.attach_chat(self._chat)



    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        clamp_window_to_screen(self)
        self._floating_chat.reposition()
        self._reflow_responsive_pages()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._floating_chat.reposition()
        self._reflow_timer.start()

    def _reflow_responsive_pages(self) -> None:
        width = self._content_width()
        self._dashboard.reflow_for_width(width)
        self._monitoring.reflow_for_width(width)

    def _content_width(self) -> int:
        sidebar_w = self._sidebar.width() if self._sidebar is not None else 240
        return max(320, self.width() - sidebar_w - 8)



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

        if index == self.PAGE_DASHBOARD:
            self._reflow_responsive_pages()

        if index == self.PAGE_TROUBLESHOOTING:
            self._sync_troubleshooting_history()



    def _on_user_message(self, text: str) -> None:

        self._chat.append_message(ChatMessage(role=ChatRole.USER, content=text))

        on_full_chat = self._current_page == self.PAGE_FULL_CHAT
        validation = self._controller.validate_input(text)
        starts_install = validation.valid and is_install_command_intent(validation.intent)

        if not on_full_chat and starts_install:
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
        if self._background_service is not None and self._active_session_id:
            self._pending_stage_message = message[:120]
            self._stage_persist_timer.start()

    def _persist_pending_stage(self) -> None:
        if self._background_service is None or not self._active_session_id:
            return
        stage = self._pending_stage_message
        if not stage:
            return
        state = self._background_service.state_store.load()
        updated = False
        for item in state.active_installations:
            if item.session_id == self._active_session_id and item.stage != stage:
                item.stage = stage
                updated = True
        if updated:
            self._background_service.state_store.save(state)



    def _load_run_history_from_disk(self) -> None:
        config = self._controller._config  # noqa: SLF001
        self._run_history = load_recent_run_results(config.reports_dir)
        if self._run_history:
            self._last_run = self._run_history[0]
        self._sync_troubleshooting_history()

    def _register_completed_run(
        self,
        result: AutomatedRunResult,
        *,
        slm_answer: str | None = None,
        slm_sources: list[str] | None = None,
        slm_status: str = "none",
    ) -> None:
        self._run_history = merge_run_history(self._run_history, result)
        session_id = result.session.session_id
        self._slm_history_by_session[session_id] = (slm_answer, slm_sources, slm_status)
        self._last_run = result
        self._dashboard.invalidate_cache()
        self._last_platform_fingerprint = ""
        self._sync_troubleshooting_history(selected_session_id=session_id)

    def _sync_troubleshooting_history(self, *, selected_session_id: str | None = None) -> None:
        session_id = selected_session_id
        if session_id is None and self._last_run is not None:
            session_id = self._last_run.session.session_id
        self._troubleshooting.set_run_history(
            self._run_history,
            slm_by_session=self._slm_history_by_session,
            selected_session_id=session_id,
        )
        target_run = None
        if session_id:
            for run in self._run_history:
                if run.session.session_id == session_id:
                    target_run = run
                    break
        if target_run is None and self._run_history:
            target_run = self._run_history[0]
        if target_run is None:
            self._troubleshooting.apply_run_result(None)
            return
        slm_answer, slm_sources, slm_status = self._slm_history_by_session.get(
            target_run.session.session_id,
            (None, None, "none"),
        )
        self._troubleshooting.apply_run_result(
            target_run,
            slm_answer=slm_answer,
            slm_sources=slm_sources,
            slm_status=slm_status,
        )

    def _on_install_started(self, installer_name: str) -> None:
        """Prepare UI for a new monitored install after a previous one finished."""
        self._active_session_id = ""
        self._live_error_slm_armed = False
        self._full_chat.clear_error_notice()
        self._monitoring.prepare_for_new_install(installer_name=installer_name)
        self._floating_chat.set_context(f"Installing: {installer_name}")
        self._full_chat.set_context(f"Installing: {installer_name}")

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
            from smartinstall.ui.workers.background_sync_worker import platform_state_fingerprint

            fingerprint = platform_state_fingerprint(state)
            if fingerprint != self._last_platform_fingerprint:
                self._last_platform_fingerprint = fingerprint
                self._refresh_dashboard(state)
            if self._tray is not None and hasattr(self._tray, "update_from_state"):
                self._tray.update_from_state(state)  # type: ignore[union-attr]
            if state.active_installations:
                active = state.active_installations[0]
                if not self._active_session_id:
                    self._monitoring.begin_monitoring(
                        installer_name=active.installer_name,
                        session_id=active.session_id,
                        pid=active.pid,
                        mode=active.mode,
                    )
                if self._current_page == self.PAGE_MONITORING:
                    busy_msg = f"Monitoring {active.installer_name}"
                    self._monitoring.set_busy(busy_msg)
                    self._monitoring.set_stage(active.stage)
                    self._monitoring.set_process_info(f"pid={active.pid}  ·  {active.mode}")
                    self._monitoring.set_start_time(active.started_at)

    def _bring_to_front(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _on_installation_detected_log(self, message: str) -> None:
        self._monitoring.append_log(message)

    def _on_live_monitoring_started(self, payload: dict) -> None:
        """First popup per install: live monitoring has started (Explorer or Installation Center)."""
        session_id = str(payload.get("sessionId", ""))
        if not session_id:
            return
        if session_id in self._live_monitoring_sessions:
            return
        self._live_monitoring_sessions.add(session_id)
        self._active_session_id = session_id
        self._live_error_slm_armed = False
        installer_name = str(payload.get("installerName", "installer"))

        detail = str(payload.get("detail", ""))
        mode = str(payload.get("mode", "automatic"))
        user_initiated = mode == "manual" and self._controller.is_busy
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
        if "testapp" in installer_name.lower():
            QTimer.singleShot(1500, self._focus_demo_installer_window)
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

        if not user_initiated:
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
        installer = str(payload.get("installerName", ""))
        if self._controller._config.auto_run_slm and not self._live_error_slm_armed:  # noqa: SLF001
            self._live_error_slm_armed = True
            self._monitoring.assistance_panel.set_slm_running(installer_name=installer)

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
            self._monitoring.assistance_panel.set_install_success(
                str(payload.get("installerName", "Installer"))
            )
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
        if slm_answer:
            self._last_slm_answer = slm_answer
            self._last_slm_sources = slm_sources or []
        self._register_completed_run(
            result,
            slm_answer=slm_answer,
            slm_sources=slm_sources,
            slm_status="ready" if slm_answer else "none",
        )

        outcome = result.report.status.installation_outcome.lower()
        if outcome in {"success", "completed"}:
            self._monitoring.set_success(result)
        elif outcome in {"failed", "failure", "error"}:
            self._monitoring.set_error(result)
        else:
            self._monitoring.apply_run_result(result)

        self._refresh_dashboard()
        ctx = result.discovered.file_name
        self._floating_chat.set_context(ctx)
        self._full_chat.set_context(ctx)

    def _active_installation_count(self) -> int:
        if self._background_service is None:
            return 0
        state = self._background_service.state_store.load()
        return len(state.active_installations)

    def _should_confirm_exit(self) -> bool:
        config = self._controller._config  # noqa: SLF001
        return should_confirm_exit(
            confirm_when_busy=config.confirm_exit_when_busy,
            controller_busy=self._controller.is_busy,
            active_session_id=self._active_session_id,
            active_installation_count=self._active_installation_count(),
        )

    def _confirm_exit(self) -> bool:
        dialog = ExitConfirmDialog(
            self._palette,
            detail=(
                "A monitored installation is still running. Exiting now will stop live "
                "monitoring and any in-progress AI diagnosis.\n\n"
                "Choose <b>Stay</b> to keep SmartInstall AI running, or "
                "<b>Exit anyway</b> to close the application."
            ),
            parent=self,
        )
        return dialog.exec() == ExitConfirmDialog.DialogCode.Accepted

    def request_quit(self) -> None:
        """Exit the application after optional confirmation and graceful shutdown."""
        if self._shutting_down:
            return
        if self._should_confirm_exit() and not self._confirm_exit():
            return
        self._finalize_shutdown()
        app = QApplication.instance()
        if app is not None:
            app.quit()

    def ensure_shutdown(self) -> None:
        """Idempotent cleanup hook for QApplication.aboutToQuit."""
        self._finalize_shutdown()

    def _finalize_shutdown(self) -> None:
        if self._shutting_down:
            return
        self._shutting_down = True
        self._shutdown_workers()
        if self._tray is not None and hasattr(self._tray, "shutdown"):
            self._tray.shutdown()  # type: ignore[union-attr]

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
        event.ignore()
        self.request_quit()

    def _shutdown_workers(self) -> None:
        if self._sync_worker is not None:
            self._sync_worker.requestInterruption()
            self._sync_worker.wait(3000)
        stop_qthread(self._slm_worker, wait_ms=60_000)
        self._slm_worker = None
        self._controller.shutdown_workers(wait_ms=60_000)
        self._controller.event_bridge.detach()
        if self._background_service is not None:
            self._background_service.stop()



    def on_run_completed(

        self,

        result: AutomatedRunResult,

        *,

        slm_answer: str | None = None,

        slm_sources: list[str] | None = None,

    ) -> None:

        if slm_answer:
            self._last_slm_answer = slm_answer
            self._last_slm_sources = slm_sources or []

        outcome = result.report.status.installation_outcome.lower()
        slm_status = "running"

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
        if needs_slm and not slm_answer:
            slm_status = "running"
        elif slm_answer:
            slm_status = "ready"
        else:
            slm_status = "none"
        self._register_completed_run(
            result,
            slm_answer=slm_answer,
            slm_sources=slm_sources,
            slm_status=slm_status,
        )
        from smartinstall.agent.slm.diagnosis_policy import actionable_install_errors

        actionable = actionable_install_errors(result.report.errors)
        if actionable:
            self._monitoring.assistance_panel.apply_errors_from_report(actionable)
        elif outcome in {"success", "completed"}:
            self._monitoring.assistance_panel.set_install_success(result.discovered.file_name)
        if needs_slm and not slm_answer:
            self._monitoring.assistance_panel.set_slm_running(
                installer_name=result.discovered.file_name
            )
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
            session_id = self._last_run.session.session_id
            self._slm_history_by_session[session_id] = (answer, sources, "ready")
            self._sync_troubleshooting_history(selected_session_id=session_id)

    @staticmethod
    def _needs_slm_for_result(result: AutomatedRunResult) -> bool:
        return should_run_slm_diagnosis(result.report)


def _suggest_fix_from_message(message: str) -> str:
    lowered = message.lower()
    if "visual c++" in lowered or "vcruntime" in lowered:
        return "Install Microsoft Visual C++ Redistributable and retry."
    if ".net" in lowered:
        return "Install .NET Framework 4.8 and retry."
    if "1618" in lowered:
        return "Wait for other MSI operations to complete, then retry."
    return "Review the full AI troubleshooting report in the dashboard."

