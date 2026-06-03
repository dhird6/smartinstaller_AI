"""Application typography — Poppins with sensible fallbacks."""

from __future__ import annotations

from PySide6.QtGui import QFont

FONT_FAMILY = '"Poppins", "Segoe UI", sans-serif'
FONT_FAMILY_CSS = "Poppins, Segoe UI, sans-serif"


def app_font(*, point_size: int = 10) -> QFont:
    font = QFont("Poppins", point_size)
    if not font.exactMatch():
        font = QFont("Segoe UI", point_size)
    font.setHintingPreference(QFont.HintingPreference.PreferFullHinting)
    return font
