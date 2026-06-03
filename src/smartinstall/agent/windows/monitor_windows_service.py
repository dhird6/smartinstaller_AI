"""Windows Service (SCM) host for background installer monitoring."""

from __future__ import annotations

import sys
import threading

import structlog

logger = structlog.get_logger(__name__)

_SERVICE_NAME = "SmartInstallAIMonitor"
_SERVICE_DISPLAY = "Smart Install AI Monitoring Service"
_SERVICE_DESCRIPTION = (
    "Detects software installations launched on Windows and collects troubleshooting evidence."
)


def _run_monitor_loop(stop_event: threading.Event) -> None:
    from smartinstall.agent.di.container import build_container
    from smartinstall.agent.services.background_monitor_service import BackgroundMonitorService

    container = build_container()
    monitor = BackgroundMonitorService(container)
    monitor.start()
    logger.info("windows_service_monitor_started")
    try:
        while not stop_event.is_set():
            stop_event.wait(1.0)
    finally:
        monitor.stop()
        logger.info("windows_service_monitor_stopped")


if sys.platform == "win32":
    import servicemanager
    import win32event
    import win32service
    import win32serviceutil

    class SmartInstallMonitorService(win32serviceutil.ServiceFramework):
        """SCM-hosted background monitoring (runs without desktop UI)."""

        _svc_name_ = _SERVICE_NAME
        _svc_display_name_ = _SERVICE_DISPLAY
        _svc_description_ = _SERVICE_DESCRIPTION

        def __init__(self, args) -> None:
            super().__init__(args)
            self._stop_event = win32event.CreateEvent(None, 0, 0, None)
            self._worker_stop = threading.Event()

        def SvcStop(self) -> None:
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            self._worker_stop.set()
            win32event.SetEvent(self._stop_event)

        def SvcDoRun(self) -> None:
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STARTED,
                (self._svc_name_, ""),
            )
            worker = threading.Thread(
                target=_run_monitor_loop,
                args=(self._worker_stop,),
                name="ServiceMonitorLoop",
                daemon=True,
            )
            worker.start()
            win32event.WaitForSingleObject(self._stop_event, win32event.INFINITE)
            worker.join(timeout=30)
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STOPPED,
                (self._svc_name_, ""),
            )


def handle_service_command_line() -> None:
    """Entry point for `python smartinstall_service.py <install|start|...>`."""
    if sys.platform != "win32":
        print("Windows Service is only supported on Windows.", file=sys.stderr)
        raise SystemExit(1)
    import win32serviceutil

    win32serviceutil.HandleCommandLine(SmartInstallMonitorService)
