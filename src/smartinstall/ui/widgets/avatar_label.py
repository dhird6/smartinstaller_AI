"""Circular avatar widget backed by SVG icons."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QLabel

from smartinstall.ui.resources import icons_dir


class AvatarLabel(QLabel):
    """Renders a round avatar from an SVG resource."""

    def __init__(self, icon_name: str, *, size: int = 40, parent=None) -> None:
        super().__init__(parent)
        self._size = size
        self.setFixedSize(size, size)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pixmap = _load_svg_icon(icons_dir() / icon_name, size)
        self.setPixmap(pixmap)
        self.setStyleSheet("background: transparent;")


def _load_svg_icon(path: Path, size: int) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    if not path.is_file():
        return pixmap
    renderer = QSvgRenderer(str(path))
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return pixmap


def icon_pixmap(icon_name: str, size: int) -> QPixmap:
    return _load_svg_icon(icons_dir() / icon_name, size)
