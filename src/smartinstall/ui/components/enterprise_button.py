"""Consistent enterprise button styles."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton

from smartinstall.ui.theme.cctech_theme import CCTechPalette


def primary_button(text: str, palette: CCTechPalette, *, parent=None) -> QPushButton:
    btn = QPushButton(text)
    btn.setObjectName("primaryBtn")
    btn.setMinimumHeight(44)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setProperty("loading", False)
    return btn


def secondary_button(text: str, palette: CCTechPalette, *, parent=None) -> QPushButton:
    btn = QPushButton(text)
    btn.setObjectName("secondaryBtn")
    btn.setMinimumHeight(44)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    return btn


def hero_primary_button(text: str, palette: CCTechPalette, *, parent=None) -> QPushButton:
    """Primary CTA for dark hero panels — inline styles avoid global QPushButton bleed."""
    p = palette
    btn = QPushButton(text, parent)
    btn.setObjectName("heroPrimary")
    btn.setMinimumHeight(44)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setStyleSheet(
        f"""
        QPushButton {{
            background-color: {p.blue_600};
            color: #ffffff;
            border: none;
            border-radius: 8px;
            padding: 11px 22px;
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
    btn.setMinimumHeight(44)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setStyleSheet(
        """
        QPushButton {
            background-color: transparent;
            color: #ffffff;
            border: 1.5px solid rgba(255, 255, 255, 0.55);
            border-radius: 8px;
            padding: 11px 22px;
            font-weight: 600;
        }
        QPushButton:hover {
            background-color: rgba(255, 255, 255, 0.1);
            border-color: #ffffff;
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
