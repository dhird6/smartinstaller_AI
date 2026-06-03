"""Chat assistant icon for FAB and launcher buttons."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

from smartinstall.ui.resources import icons_dir

_CHATBOT_SVG = icons_dir() / "chatbot.svg"


def chatbot_icon(size: int = 32) -> QIcon:
    """Return the standard chatbot icon (not the company logo)."""
    pixmap = chatbot_pixmap(size)
    return QIcon(pixmap)


def chatbot_pixmap(size: int) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    if not _CHATBOT_SVG.is_file():
        return pixmap
    renderer = QSvgRenderer(str(_CHATBOT_SVG))
    if renderer.isValid():
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
    return pixmap
