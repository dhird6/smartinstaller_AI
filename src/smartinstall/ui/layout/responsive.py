"""Screen-aware sizing helpers for responsive desktop layouts."""

from __future__ import annotations

from PySide6.QtCore import QRect, Qt
from PySide6.QtWidgets import QApplication, QFrame, QMainWindow, QScrollArea, QWidget


def available_screen_geometry(widget: QWidget | None = None) -> QRect:
    """Return available desktop geometry for *widget* or the primary screen."""
    if widget is not None:
        screen = widget.screen()
        if screen is not None:
            return screen.availableGeometry()
    app = QApplication.instance()
    if app is not None:
        screen = app.primaryScreen()
        if screen is not None:
            return screen.availableGeometry()
    return QRect(0, 0, 1280, 800)


def configure_page_scroll(scroll: QScrollArea) -> None:
    """Standard scroll policy: vertical when needed, never horizontal."""
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)


def fit_main_window(window: QMainWindow, *, width_ratio: float = 0.92, height_ratio: float = 0.90) -> None:
    """Size and center *window* within the available screen, clamped to safe bounds."""
    geom = available_screen_geometry(window)
    sw, sh = geom.width(), geom.height()

    min_w = max(640, min(800, int(sw * 0.70)))
    min_h = max(480, min(560, int(sh * 0.65)))
    window.setMinimumSize(min_w, min_h)

    w = min(int(sw * width_ratio), sw - 16)
    h = min(int(sh * height_ratio), sh - 16)
    w = max(min_w, w)
    h = max(min_h, h)

    window.resize(w, h)
    window.move(
        geom.x() + max(0, (sw - w) // 2),
        geom.y() + max(0, (sh - h) // 2),
    )


def clamp_window_to_screen(window: QMainWindow) -> None:
    """Ensure the window frame stays fully inside the available screen area."""
    geom = available_screen_geometry(window)
    frame = window.frameGeometry()
    if frame.width() > geom.width():
        window.resize(max(window.minimumWidth(), geom.width() - 16), frame.height())
    if frame.height() > geom.height():
        window.resize(window.width(), max(window.minimumHeight(), geom.height() - 16))
    frame = window.frameGeometry()
    x = min(max(frame.x(), geom.x()), geom.right() - frame.width() + 1)
    y = min(max(frame.y(), geom.y()), geom.bottom() - frame.height() + 1)
    window.move(x, y)
