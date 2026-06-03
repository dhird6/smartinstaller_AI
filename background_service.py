#!/usr/bin/env python3
"""Standalone Windows background monitoring service entry point."""

from __future__ import annotations

import signal
import sys
import time

from smartinstall.agent.di.container import build_container
from smartinstall.agent.services.background_monitor_service import BackgroundMonitorService


def main() -> int:
    container = build_container()
    service = BackgroundMonitorService(container)
    service.start()

    def _shutdown(signum: int, frame: object) -> None:  # noqa: ARG001
        service.stop()
        raise SystemExit(0)

    signal.signal(signal.SIGINT, _shutdown)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _shutdown)

    print("Smart Installer background monitoring service running. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        service.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
