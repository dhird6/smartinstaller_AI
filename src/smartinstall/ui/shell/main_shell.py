"""Enterprise application shell — CCTech branded SaaS-quality desktop UI."""



from __future__ import annotations



from PySide6.QtCore import Qt

from PySide6.QtGui import QAction, QIcon

from PySide6.QtWidgets import QHBoxLayout, QMainWindow, QStackedWidget, QVBoxLayout, QWidget



from pathlib import Path

from smartinstall.agent.notifications.installation_notification_builder import (
    format_slm_completion_toast,
    monitoring_started_message,
)
from smartinstall.agent.notifications.windows_notifier import WindowsNotifier
from smartinstall.core.models.unified_report import ReportErrorEntry
from smartinstall.agent.orchestration.automated_run_orchestrator import AutomatedRunResult

from smartinstall.ui.controllers.desktop_controller import DesktopController

from smartinstall.ui.models.chat_message import ChatMessage, ChatRole

from smartinstall.agent.monitoring.monitoring_state_store import MonitoringPlatformState
from smartinstall.agent.services.background_monitor_service import BackgroundMonitorService
from smartinstall.ui.pages.dashboard_page import DashboardPage
from smartinstall.ui.pages.full_chat_page import FullChatPage
from smartinstall.ui.pages.installation_center_page import InstallationCenterPage
from smartinstall.ui.pages.monitoring_page import MonitoringPage
from smartinstall.ui.pages.troubleshooting_page import TroubleshootingPage
from smartinstall.ui.workers.background_sync_worker import BackgroundSyncWorker

from smartinstall.ui.resources.brand_assets import load_brand_logo_pixmap

from smartinstall.ui.services.run_result_loader import load_run_result_from_report
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
        self._notifier = WindowsNotifier()
        self._shown_toast_keys: set[str] = set()



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
        self._controller.event_bridge.installation_detected.connect(self._on_installation_detected)
        self._controller.event_bridge.installation_error.connect(self._on_installation_error)
        self._troubleshooting.open_ai_chat.connect(self._on_troubleshooting_open_chat)
        self._controller.event_bridge.monitoring_started.connect(self._on_monitoring_started)
        self._controller.event_bridge.slm_diagnosis_ready.connect(self._on_slm_diagnosis_ready)
        if self._background_service is not None:
            self._sync_worker = BackgroundSyncWorker(self._background_service)
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

        self._monitoring.set_busy(message)

        self._monitoring.append_log(message)



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
                self._monitoring.set_busy(f"Monitoring {active.installer_name}")
                self._monitoring.set_stage(active.stage)
                self._monitoring.set_process_info(f"pid={active.pid}")

    def _toast_once(self, key: str, *, title: str, message: str) -> None:
        if key in self._shown_toast_keys:
            return
        if not self._controller._config.enable_windows_notifications:  # noqa: SLF001
            return
        self._shown_toast_keys.add(key)
        self._notifier.show_combined_notification(title=title, message=message)

    def _on_monitoring_started(self, installer_name: str) -> None:
        self._monitoring.set_busy(f"Live monitoring: {installer_name}")
        self._monitoring.append_log(
            "Smart Installer is actively monitoring this installation in real time."
        )
        self._navigate(self.PAGE_MONITORING)
        self._toast_once(
            f"monitoring-start:{installer_name}",
            title="Smart Installer — Live Monitoring",
            message=monitoring_started_message(installer_name),
        )

    def _on_installation_detected(self, message: str) -> None:
        self._monitoring.set_busy(message)
        self._navigate(self.PAGE_MONITORING)

    def _on_installation_error(self, payload: dict) -> None:
        message = str(payload.get("message", "Installation error"))
        code = str(payload.get("code", ""))
        self._monitoring.append_log(f"ERROR {code}: {message}")
        if self._controller.auto_run_slm:
            self._monitoring.set_slm_pending()

    def _on_pending_notification(self, payload: object) -> None:
        if not isinstance(payload, dict):
            return
        if payload.get("awaitingSlm"):
            return
        slm_answer = str(payload.get("slmAnswer", "")).strip()
        if slm_answer:
            sources = [str(item) for item in payload.get("slmSources", [])]
            errors = self._errors_from_notification(payload)
            self._apply_slm_diagnosis(
                slm_answer,
                sources,
                navigate=True,
                notification_errors=errors,
                session_id=str(payload.get("sessionId", "")),
            )

    def _on_slm_diagnosis_ready(self, payload: dict) -> None:
        answer = str(payload.get("answer", "")).strip()
        if not answer:
            return
        sources = [str(item) for item in payload.get("sources", [])]
        report_path = payload.get("reportPath")
        if self._last_run is None and report_path:
            loaded = load_run_result_from_report(Path(str(report_path)))
            if loaded is not None:
                self._last_run = loaded
        errors = self._last_run.report.errors if self._last_run is not None else []
        self._apply_slm_diagnosis(
            answer,
            sources,
            navigate=True,
            notification_errors=errors,
            session_id=str(payload.get("sessionId", "")),
        )

    @staticmethod
    def _errors_from_notification(payload: dict) -> list[ReportErrorEntry]:
        raw_errors = payload.get("errors")
        if not isinstance(raw_errors, list):
            return []
        entries: list[ReportErrorEntry] = []
        for item in raw_errors:
            if not isinstance(item, dict):
                continue
            entries.append(
                ReportErrorEntry(
                    category=str(item.get("category", "installation")),
                    code=str(item.get("code", "")),
                    message=str(item.get("message", "")),
                    source="notification",
                )
            )
        return entries

    def _apply_slm_diagnosis(
        self,
        answer: str,
        sources: list[str],
        *,
        navigate: bool = False,
        status: str = "ready",
        notification_errors: list[ReportErrorEntry] | None = None,
        session_id: str = "",
    ) -> None:
        self._last_slm_answer = answer
        self._last_slm_sources = sources
        self._monitoring.set_slm_diagnosis(answer, sources, status=status)
        pending = status == "running"
        if self._last_run is not None:
            self._troubleshooting.apply_run_result(
                self._last_run,
                slm_answer=answer,
                slm_sources=sources,
                ai_status=status,
                slm_pending=pending,
            )
            if navigate and self._run_needs_troubleshooting(self._last_run):
                self._navigate(self.PAGE_TROUBLESHOOTING)
        installer = ""
        errors = notification_errors or []
        if self._last_run is not None:
            installer = self._last_run.report.status.installer.installer_name
            if not errors:
                errors = self._last_run.report.errors
        if status == "ready":
            toast_key = f"slm-complete:{session_id or installer}"
            title, message = format_slm_completion_toast(
                installer_name=installer,
                slm_answer=answer,
                errors=errors,
            )
            self._toast_once(toast_key, title=title, message=message)

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
        if self._background_service is not None:
            self._background_service.stop()



    def _run_needs_troubleshooting(self, result: AutomatedRunResult) -> bool:
        report = result.report
        outcome = (report.status.installation_outcome or "").lower()
        if outcome in {"failed", "failure", "error", "partial"}:
            return True
        return bool(report.errors) or bool(report.status.failure_reason)

    def _troubleshooting_ai_status(
        self,
        *,
        slm_answer: str | None,
        pending_slm: bool,
    ) -> str:
        if slm_answer and slm_answer.strip():
            return "ready"
        if pending_slm:
            return "running"
        return "idle"

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
        needs_tshoot = self._run_needs_troubleshooting(result)
        pending_slm = (
            needs_tshoot
            and slm_answer is None
            and self._controller.auto_run_slm
        )

        if outcome in {"success", "completed"}:
            self._monitoring.set_success(result)
        elif outcome in {"failed", "failure", "error"}:
            self._monitoring.set_error(result)
            reason = (
                result.report.status.failure_reason
                or "Installation failed — see Troubleshooting for AI suggestions."
            )
            self._full_chat.show_error_notice(reason)
        else:
            self._monitoring.apply_run_result(result)

        self._troubleshooting.apply_run_result(
            result,
            slm_answer=slm_answer,
            slm_sources=slm_sources,
            ai_status=self._troubleshooting_ai_status(
                slm_answer=slm_answer,
                pending_slm=pending_slm,
            ),
            slm_pending=pending_slm,
        )

        if needs_tshoot:
            self._navigate(self.PAGE_TROUBLESHOOTING)
            if pending_slm:
                self._monitoring.set_slm_pending()
            elif slm_answer:
                self._monitoring.set_slm_diagnosis(slm_answer, slm_sources)

        self._refresh_dashboard()

        ctx = result.discovered.file_name
        self._floating_chat.set_context(ctx)
        self._full_chat.set_context(ctx)

    def on_slm_completed(self, answer: str, sources: list[str]) -> None:
        self._apply_slm_diagnosis(answer, sources, navigate=True, status="ready")

    def on_slm_failed(self, message: str) -> None:
        if self._last_run is not None:
            self._troubleshooting.apply_run_result(
                self._last_run,
                slm_answer=self._last_slm_answer,
                slm_sources=self._last_slm_sources,
                ai_status="unavailable",
                slm_pending=False,
            )
            self._monitoring.set_slm_diagnosis(
                f"AI diagnosis unavailable: {message[:300]}",
                self._last_slm_sources,
                status="unavailable",
            )
            if self._run_needs_troubleshooting(self._last_run):
                self._navigate(self.PAGE_TROUBLESHOOTING)
        self._full_chat.show_error_notice(
            f"AI diagnosis unavailable: {message[:200]}"
        )

    def _on_troubleshooting_open_chat(self, prompt: str) -> None:
        self._floating_chat.open_compact()
        self._chat.prefill_input(prompt)


def _suggest_fix_from_message(message: str) -> str:
    lowered = message.lower()
    if "visual c++" in lowered or "vcruntime" in lowered:
        return "Install Microsoft Visual C++ Redistributable and retry."
    if ".net" in lowered:
        return "Install .NET Framework 4.8 and retry."
    if "1618" in lowered:
        return "Wait for other MSI operations to complete, then retry."
    return "Review the full AI troubleshooting report in the dashboard."

