"""Subtle animated gradient orbs for SaaS-style page backgrounds."""

from __future__ import annotations

import math

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QRadialGradient
from PySide6.QtWidgets import QWidget

from smartinstall.ui.theme.cctech_theme import CCTechPalette


class AnimatedBackground(QWidget):
    """Low-opacity moving blobs behind dashboard content."""

    def __init__(self, palette: CCTechPalette, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._palette = palette
        self._phase = 0.0
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._timer = QTimer(self)
        self._timer.setInterval(40)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    def _tick(self) -> None:
        self._phase += 0.018
        self.update()

    def paintEvent(self, _event) -> None:  # noqa: N802
        p = self._palette
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        base = QLinearGradient(0, 0, self.width(), self.height())
        base.setColorAt(0.0, QColor(p.canvas))
        base.setColorAt(1.0, QColor("#e8eef8"))
        painter.fillRect(self.rect(), base)

        orbs = (
            (0.15, 0.2, 0.35, QColor(30, 91, 255, 28)),
            (0.75, 0.15, 0.28, QColor(34, 211, 238, 22)),
            (0.55, 0.72, 0.32, QColor(15, 39, 68, 18)),
        )
        for ox, oy, scale, color in orbs:
            cx = self.width() * (ox + 0.04 * math.sin(self._phase + ox * 5))
            cy = self.height() * (oy + 0.03 * math.cos(self._phase * 1.2 + oy * 4))
            radius = min(self.width(), self.height()) * scale
            grad = QRadialGradient(cx, cy, radius)
            grad.setColorAt(0, color)
            grad.setColorAt(1, QColor(0, 0, 0, 0))
            painter.setBrush(grad)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(int(cx - radius), int(cy - radius), int(radius * 2), int(radius * 2))
        painter.end()
