"""System tray — always-on monitoring access without keeping the dashboard open."""

from __future__ import annotations

import sys

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from smartinstall.agent.monitoring.monitoring_state_store import MonitoringPlatformState
from smartinstall.agent.services.background_monitor_service import BackgroundMonitorService
from smartinstall.agent.windows.auto_start import (
    disable_auto_start,
    enable_auto_start,
    is_auto_start_enabled,
)
from smartinstall.ui.resources.brand_assets import load_brand_logo_pixmap
from smartinstall.ui.shell.main_shell import MainShell
from smartinstall.ui.theme.cctech_theme import CCTechPalette


class SystemTrayController:
    """Tray icon with quick actions for monitoring, service, and auto-start."""

    def __init__(
        self,
        *,
        shell: MainShell,
        palette: CCTechPalette,
        background_service: BackgroundMonitorService | None,
        app,
    ) -> None:
        self._shell = shell
        self._background_service = background_service
        self._app = app
        self._auto_monitor_paused = False

        self._tray = QSystemTrayIcon(QIcon(load_brand_logo_pixmap(32)), shell)
        self._tray.setToolTip("Smart Install AI — monitoring active")
        self._menu = QMenu()
        self._active_action = QAction("Active installations: 0", self._menu)
        self._active_action.setEnabled(False)
        self._heartbeat_action = QAction("Service heartbeat: —", self._menu)
        self._heartbeat_action.setEnabled(False)
        self._auto_start_action = QAction("Enable auto-start at login", self._menu)
        self._auto_start_action.setCheckable(True)
        self._auto_start_action.setChecked(is_auto_start_enabled())
        self._pause_action = QAction("Pause automatic monitoring", self._menu)

        open_dashboard = QAction("Open dashboard", self._menu)
        open_dashboard.triggered.connect(self._show_dashboard)
        open_monitoring = QAction("Live monitoring", self._menu)
        open_monitoring.triggered.connect(self._show_monitoring)
        last_failed = QAction("View last failed install", self._menu)
        last_failed.triggered.connect(self._open_last_failed)
        install_service = QAction("Install Windows Service (admin)…", self._menu)
        install_service.triggered.connect(self._show_service_instructions)
        self._auto_start_action.triggered.connect(self._toggle_auto_start)
        self._pause_action.triggered.connect(self._toggle_auto_monitor)
        quit_action = QAction("Exit Smart Installer", self._menu)
        quit_action.triggered.connect(self._quit_app)

        self._menu.addAction(self._active_action)
        self._menu.addAction(self._heartbeat_action)
        self._menu.addSeparator()
        self._menu.addAction(open_dashboard)
        self._menu.addAction(open_monitoring)
        self._menu.addAction(last_failed)
        self._menu.addSeparator()
        self._menu.addAction(self._pause_action)
        self._menu.addAction(self._auto_start_action)
        if sys.platform == "win32":
            self._menu.addAction(install_service)
        self._menu.addSeparator()
        self._menu.addAction(quit_action)

        self._tray.setContextMenu(self._menu)
        self._tray.activated.connect(self._on_activated)
        self._tray.show()

    def update_from_state(self, state: MonitoringPlatformState) -> None:
        count = len(state.active_installations)
        self._active_action.setText(f"Active installations: {count}")
        heartbeat = state.last_updated or "—"
        self._heartbeat_action.setText(f"Service heartbeat: {heartbeat}")
        self._tray.setToolTip(
            f"Smart Install AI — {count} active, auto-monitor "
            f"{'paused' if self._auto_monitor_paused else 'on'}"
        )

    def notify(self, title: str, message: str) -> None:
        self._tray.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, 8000)

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._show_dashboard()

    def _show_dashboard(self) -> None:
        self._shell.showNormal()
        self._shell.raise_()
        self._shell.activateWindow()
        self._shell._navigate(self._shell.PAGE_DASHBOARD)  # noqa: SLF001

    def _show_monitoring(self) -> None:
        self._shell.showNormal()
        self._shell.raise_()
        self._shell._navigate(self._shell.PAGE_MONITORING)  # noqa: SLF001

    def _open_last_failed(self) -> None:
        if self._background_service is None:
            self._show_dashboard()
            return
        state = self._background_service.state_store.load()
        failed = [
            item
            for item in state.recent_installations
            if "fail" in item.outcome.lower() or item.error_summary
        ]
        self._shell.showNormal()
        self._shell._navigate(self._shell.PAGE_TROUBLESHOOTING)  # noqa: SLF001
        if failed:
            self.notify("Last failed install", failed[0].installer_name)

    def _toggle_auto_monitor(self) -> None:
        if self._background_service is None:
            return
        config = self._background_service._container.config  # noqa: SLF001
        config.auto_monitor_enabled = not config.auto_monitor_enabled
        self._auto_monitor_paused = not config.auto_monitor_enabled
        self._pause_action.setText(
            "Resume automatic monitoring"
            if self._auto_monitor_paused
            else "Pause automatic monitoring"
        )
        state = self._background_service.state_store.load()
        state.automatic_monitoring_enabled = config.auto_monitor_enabled
        self._background_service.state_store.save(state)
        label = "paused" if self._auto_monitor_paused else "resumed"
        self.notify("Auto-monitoring", f"Automatic detection {label}.")

    def _toggle_auto_start(self, checked: bool) -> None:
        try:
            if checked:
                enable_auto_start(tray_only=True)
            else:
                disable_auto_start()
        except OSError as exc:
            self.notify("Auto-start", f"Could not update registry: {exc}")
            self._auto_start_action.setChecked(is_auto_start_enabled())

    def _show_service_instructions(self) -> None:
        self.notify(
            "Windows Service",
            "Run scripts\\install_windows_service.ps1 as Administrator to register SCM.",
        )

    def _quit_app(self) -> None:
        self._shell._shutdown_workers()  # noqa: SLF001
        self._tray.hide()
        self._app.quit()
