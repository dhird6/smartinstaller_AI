"""Installation progress indicator — state-driven, no fake auto-animation."""

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
    """Status rings that animate only while an installation is actively running."""

    def __init__(self, palette: CCTechPalette, *, size: int = 120, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._palette = palette
        self._state = InstallVisualState.IDLE
        self._angle = 0.0
        self.setFixedSize(size, size)

        self._timer = QTimer(self)
        self._timer.setInterval(40)
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
            self._angle = 0.0
        self.update()

    def _tick(self) -> None:
        if self._state is InstallVisualState.BUSY:
            self._angle = (self._angle + 3.0) % 360.0
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
        elif self._state is InstallVisualState.BUSY:
            accent = QColor(p.blue_600)
        else:
            accent = QColor(p.text_muted)

        track = QColor(p.border)
        for index, scale in enumerate((1.0, 0.78, 0.56)):
            radius = base * scale
            ring_rect = QRectF(cx - radius, cy - radius, radius * 2, radius * 2)
            painter.setPen(QPen(track, 3.0 - index * 0.4))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(ring_rect)

            if self._state is InstallVisualState.BUSY:
                pen = QPen(accent, 3.0 - index * 0.4)
                pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                painter.setPen(pen)
                start = int((self._angle + index * 25) * 16)
                painter.drawArc(ring_rect, start, 200 * 16)
            elif self._state in (InstallVisualState.SUCCESS, InstallVisualState.ERROR):
                pen = QPen(accent, 3.0 - index * 0.4)
                pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                painter.setPen(pen)
                painter.drawArc(ring_rect, 45 * 16, 270 * 16)

        core_r = base * 0.38
        core = QRectF(cx - core_r, cy - core_r, core_r * 2, core_r * 2)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(p.surface_muted))
        painter.drawEllipse(core)
        painter.setBrush(accent)
        painter.drawEllipse(core.adjusted(6, 6, -6, -6))

        if self._state is InstallVisualState.SUCCESS:
            self._draw_check(painter, accent, cx, cy, core_r * 0.55)
        elif self._state is InstallVisualState.ERROR:
            self._draw_cross(painter, QColor(p.surface), cx, cy, core_r * 0.4)
        elif self._state is InstallVisualState.IDLE:
            painter.setBrush(QColor(p.border))
            painter.drawEllipse(core.adjusted(14, 14, -14, -14))

        painter.end()

    @staticmethod
    def _draw_check(painter: QPainter, color: QColor, cx: float, cy: float, size: float) -> None:
        pen = QPen(color, max(2.5, size * 0.18))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        x1, y1 = cx - size * 0.35, cy + size * 0.05
        x2, y2 = cx - size * 0.05, cy + size * 0.35
        x3, y3 = cx + size * 0.45, cy - size * 0.35
        painter.drawLine(int(x1), int(y1), int(x2), int(y2))
        painter.drawLine(int(x2), int(y2), int(x3), int(y3))

    @staticmethod
    def _draw_cross(painter: QPainter, color: QColor, cx: float, cy: float, size: float) -> None:
        pen = QPen(color, max(2.5, size * 0.2))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawLine(int(cx - size), int(cy - size), int(cx + size), int(cy + size))
        painter.drawLine(int(cx + size), int(cy - size), int(cx - size), int(cy + size))
