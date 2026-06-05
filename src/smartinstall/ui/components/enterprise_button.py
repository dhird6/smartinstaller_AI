"""Consistent enterprise button styles."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton

from smartinstall.ui.theme.cctech_theme import CCTechPalette

_COMPACT_BTN_HEIGHT = 36


def primary_button(text: str, palette: CCTechPalette, *, parent=None) -> QPushButton:
    btn = QPushButton(text, parent)
    btn.setObjectName("primaryBtn")
    btn.setMinimumHeight(_COMPACT_BTN_HEIGHT)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setProperty("loading", False)
    return btn


def secondary_button(text: str, palette: CCTechPalette, *, parent=None) -> QPushButton:
    btn = QPushButton(text, parent)
    btn.setObjectName("secondaryBtn")
    btn.setMinimumHeight(_COMPACT_BTN_HEIGHT)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    return btn


def page_primary_button(text: str, palette: CCTechPalette, *, parent=None) -> QPushButton:
    """Filled primary action on light section cards."""
    return primary_button(text, palette, parent=parent)


def page_secondary_button(text: str, palette: CCTechPalette, *, parent=None) -> QPushButton:
    """Outlined secondary action on light section cards."""
    return secondary_button(text, palette, parent=parent)


def hero_primary_button(text: str, palette: CCTechPalette, *, parent=None) -> QPushButton:
    """Primary CTA for dark hero panels — inline styles avoid global QPushButton bleed."""
    p = palette
    btn = QPushButton(text, parent)
    btn.setObjectName("heroPrimary")
    btn.setMinimumHeight(_COMPACT_BTN_HEIGHT)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setStyleSheet(
        f"""
        QPushButton {{
            background-color: {p.blue_600};
            color: #ffffff;
            border: none;
            border-radius: 8px;
            padding: 7px 16px;
            font-size: 9.5pt;
            font-weight: 700;
        }}
        QPushButton:hover {{ background-color: {p.blue_500}; }}
        QPushButton:pressed {{ background-color: #1848cc; }}
        """
    )
    return btn


def hero_outline_button(text: str, palette: CCTechPalette, *, parent=None) -> QPushButton:
    """Secondary CTA for dark hero panels."""
    btn = QPushButton(text, parent)
    btn.setObjectName("heroOutline")
    btn.setMinimumHeight(_COMPACT_BTN_HEIGHT)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setStyleSheet(
        """
        QPushButton#heroOutline {
            background-color: rgba(255, 255, 255, 0.14);
            color: #ffffff;
            border: 1.5px solid rgba(255, 255, 255, 0.82);
            border-radius: 8px;
            padding: 7px 16px;
            font-size: 9.5pt;
            font-weight: 700;
        }
        QPushButton#heroOutline:hover {
            background-color: rgba(255, 255, 255, 0.22);
            border-color: #ffffff;
            color: #ffffff;
        }
        QPushButton#heroOutline:pressed {
            background-color: rgba(255, 255, 255, 0.3);
        }
        """
    )
    return btn


def ghost_button(text: str, *, parent=None) -> QPushButton:
    btn = QPushButton(text)
    btn.setObjectName("ghostBtn")
    btn.setMinimumHeight(40)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    return btn


def set_button_loading(btn: QPushButton, loading: bool) -> None:
    btn.setProperty("loading", loading)
    btn.setEnabled(not loading)
    if loading:
        btn.setText("Please wait…")
    style = btn.style()
    if style is not None:
        style.unpolish(btn)
        style.polish(btn)
