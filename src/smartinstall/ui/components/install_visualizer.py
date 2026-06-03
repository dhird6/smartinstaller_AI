"""Installation progress indicator — minimal rings, low CPU use."""

from __future__ import annotations

from enum import Enum

from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

from smartinstall.ui.theme.cctech_theme import CCTechPalette


class InstallVisualState(str, Enum):
    IDLE = "idle"
    BUSY = "busy"
    SUCCESS = "success"
    ERROR = "error"


class InstallVisualizer(QWidget):
    """Simple status rings for install workflow feedback."""

    def __init__(self, palette: CCTechPalette, *, size: int = 200, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._palette = palette
        self._state = InstallVisualState.IDLE
        self._angle = 0.0
        self.setFixedSize(size, size)

        self._timer = QTimer(self)
        self._timer.setInterval(50)
        self._timer.timeout.connect(self._tick)

    def set_state(self, state: InstallVisualState) -> None:
        if state is self._state:
            return
        self._state = state
        if state is InstallVisualState.BUSY:
            if not self._timer.isActive():
                self._timer.start()
        else:
            self._timer.stop()
        self.update()

    def _tick(self) -> None:
        if self._state is InstallVisualState.BUSY:
            self._angle = (self._angle + 4.0) % 360.0
            self.update()

    def paintEvent(self, _event) -> None:  # noqa: N802
        p = self._palette
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        cx = self.width() / 2
        cy = self.height() / 2
        base = min(self.width(), self.height()) * 0.38

        if self._state is InstallVisualState.ERROR:
            accent = QColor(p.error)
        elif self._state is InstallVisualState.SUCCESS:
            accent = QColor(p.success)
        else:
            accent = QColor(p.blue_600)

        track = QColor(p.border)
        for index, scale in enumerate((1.0, 0.78, 0.56)):
            radius = base * scale
            ring_rect = QRectF(cx - radius, cy - radius, radius * 2, radius * 2)
            painter.setPen(QPen(track, 3.0 - index * 0.4))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(ring_rect)

            pen = QPen(accent, 3.0 - index * 0.4)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            span = 240 if self._state is InstallVisualState.BUSY else 120
            start = int((self._angle + index * 25) * 16)
            painter.drawArc(ring_rect, start, span * 16)

        core_r = base * 0.38
        core = QRectF(cx - core_r, cy - core_r, core_r * 2, core_r * 2)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(p.surface_muted))
        painter.drawEllipse(core)
        painter.setBrush(accent)
        painter.drawEllipse(core.adjusted(6, 6, -6, -6))

        painter.end()
