"""Tests for Qt event bridge attach/detach reference counting."""

from __future__ import annotations

import sys

import pytest
from PySide6.QtWidgets import QApplication

from smartinstall.agent.infrastructure.event_bus import AgentEvent, EventBus
from smartinstall.ui.bridge.event_bridge import QtEventBridge


@pytest.fixture
def qt_app():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def test_detach_does_not_drop_shared_subscription(qt_app: QApplication) -> None:
    bus = EventBus()
    bridge = QtEventBridge(bus)
    bridge.attach()
    bridge.attach()
    bridge.detach()
    received: list[str] = []
    bridge.status_update.connect(received.append)
    bus.publish(
        AgentEvent.INSTALLER_LAUNCHED,
        {"mode": "manual", "installerName": "setup.exe"},
    )
    qt_app.processEvents()
    assert received == ["Live monitoring started for setup.exe. Capturing install progress…"]
    bridge.detach()
    qt_app.processEvents()
