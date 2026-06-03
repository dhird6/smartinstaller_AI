#!/usr/bin/env python3
"""Windows SCM service control — install, remove, start, stop (run as Administrator)."""

from __future__ import annotations

from smartinstall.agent.windows.monitor_windows_service import handle_service_command_line

if __name__ == "__main__":
    handle_service_command_line()
