"""Desktop application entry point."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from smartinstall.agent.di.container import build_container
from smartinstall.agent.services.background_monitor_service import BackgroundMonitorService
from smartinstall.agent.windows.auto_start import enable_auto_start, is_auto_start_enabled
from smartinstall.ui.controllers.desktop_controller import DesktopController
from smartinstall.ui.resources.brand_assets import load_brand_logo_pixmap
from smartinstall.ui.shell.main_shell import MainShell
from smartinstall.ui.shell.splash_screen import SplashScreen
from smartinstall.ui.shell.system_tray import SystemTrayController
from smartinstall.ui.theme.cctech_theme import apply_cctech_theme


def run_desktop(config_path: Path | None = None, *, start_in_tray: bool = False) -> int:
    """Launch the SmartInstall AI enterprise desktop application."""
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName("SmartInstall AI")
    app.setOrganizationName("CCTech")
    app.setApplicationDisplayName("SmartInstall AI — CCTech")
    app.setWindowIcon(QIcon(load_brand_logo_pixmap(32)))
    app.setQuitOnLastWindowClosed(False)

    palette = apply_cctech_theme(app)
    splash = SplashScreen(palette)
    if not start_in_tray:
        splash.show()
        app.processEvents()

    splash.set_status("Loading configuration…")
    container = build_container(config_path)
    if not start_in_tray:
        app.processEvents()

    if container.config.auto_start_at_login and not is_auto_start_enabled():
        try:
            enable_auto_start(tray_only=True)
        except OSError:
            pass

    splash.set_status("Starting background monitoring…")
    background_service = BackgroundMonitorService(container)
    if container.config.auto_monitor_enabled:
        background_service.start()
    if not start_in_tray:
        app.processEvents()

    splash.set_status("Starting AI assistant…")
    controller = DesktopController(container)
    controller.event_bridge.attach()
    shell = MainShell(controller, palette, background_service=background_service)
    tray = SystemTrayController(
        shell=shell,
        palette=palette,
        background_service=background_service,
        app=app,
    )
    shell.set_tray_controller(tray)

    def on_run_completed(payload: object) -> None:
        shell.on_run_completed(payload)  # type: ignore[arg-type]

    def on_slm(answer: str, sources: list[str]) -> None:
        shell.on_slm_completed(answer, sources)

    controller.on_run_completed = on_run_completed
    controller.on_slm_completed = on_slm

    def _show_main() -> None:
        splash.close()
        if start_in_tray or container.config.start_minimized_to_tray:
            tray.notify(
                "Smart Install AI",
                "Running in the system tray — automatic monitoring is active.",
            )
        else:
            shell.show()
            shell.raise_()
            shell.activateWindow()

    if start_in_tray:
        _show_main()
    else:
        splash.set_status("Preparing dashboard…")
        splash.finish_after(_show_main, ms=1200)
    return app.exec()


def main() -> None:
    start_in_tray = "--tray" in sys.argv
    raise SystemExit(run_desktop(start_in_tray=start_in_tray))


if __name__ == "__main__":
    main()
