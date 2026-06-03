"""Windows 11 Fluent-inspired theme (colors + global QSS)."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication


@dataclass(frozen=True, slots=True)
class WindowsPalette:
    """Fluent design tokens aligned with Windows 11 defaults."""

    window_bg: str = "#f3f3f3"
    surface: str = "#ffffff"
    surface_alt: str = "#fafafa"
    sidebar_bg: str = "#f9f9f9"
    border: str = "#e1e1e1"
    border_strong: str = "#c8c8c8"
    text_primary: str = "#1b1b1b"
    text_secondary: str = "#5c5c5c"
    text_on_accent: str = "#ffffff"
    accent: str = "#0078d4"
    accent_hover: str = "#106ebe"
    accent_pressed: str = "#005a9e"
    accent_light: str = "#deecf9"
    success: str = "#107c10"
    warning: str = "#ca5010"
    error: str = "#c42b1c"
    user_bubble: str = "#e8f4fd"
    assistant_bubble: str = "#ffffff"
    system_pill: str = "#edebe9"
    shadow: str = "rgba(0, 0, 0, 0.08)"


def apply_windows_theme(app: QApplication) -> WindowsPalette:
    """Apply global font, palette, and stylesheet to the application."""
    palette = WindowsPalette()
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    qt_palette = QPalette()
    qt_palette.setColor(QPalette.ColorRole.Window, QColor(palette.window_bg))
    qt_palette.setColor(QPalette.ColorRole.WindowText, QColor(palette.text_primary))
    qt_palette.setColor(QPalette.ColorRole.Base, QColor(palette.surface))
    qt_palette.setColor(QPalette.ColorRole.AlternateBase, QColor(palette.surface_alt))
    qt_palette.setColor(QPalette.ColorRole.Text, QColor(palette.text_primary))
    qt_palette.setColor(QPalette.ColorRole.Button, QColor(palette.surface))
    qt_palette.setColor(QPalette.ColorRole.ButtonText, QColor(palette.text_primary))
    qt_palette.setColor(QPalette.ColorRole.Highlight, QColor(palette.accent))
    qt_palette.setColor(QPalette.ColorRole.HighlightedText, QColor(palette.text_on_accent))
    app.setPalette(qt_palette)
    app.setStyleSheet(build_stylesheet(palette))
    return palette


def build_stylesheet(p: WindowsPalette) -> str:
    return f"""
    QMainWindow, QWidget {{
        background-color: {p.window_bg};
        color: {p.text_primary};
        font-family: "Segoe UI";
        font-size: 10pt;
    }}
    QFrame#appHeader {{
        background-color: {p.surface};
        border-bottom: 1px solid {p.border};
    }}
    QFrame#sidebar {{
        background-color: {p.sidebar_bg};
        border-right: 1px solid {p.border};
    }}
    QFrame#chatSurface {{
        background-color: {p.window_bg};
    }}
    QFrame#composerBar {{
        background-color: {p.surface};
        border-top: 1px solid {p.border};
    }}
    QLabel#appTitle {{
        font-size: 15pt;
        font-weight: 600;
        color: {p.text_primary};
    }}
    QLabel#appSubtitle {{
        font-size: 9pt;
        color: {p.text_secondary};
    }}
    QLabel#sidebarTitle {{
        font-size: 9pt;
        font-weight: 600;
        color: {p.text_secondary};
        padding: 4px 0;
    }}
    QPushButton {{
        background-color: {p.surface};
        color: {p.text_primary};
        border: 1px solid {p.border_strong};
        border-radius: 4px;
        padding: 8px 14px;
        min-height: 20px;
    }}
    QPushButton:hover {{
        background-color: {p.surface_alt};
        border-color: {p.accent};
    }}
    QPushButton:pressed {{
        background-color: {p.accent_light};
    }}
    QPushButton:disabled {{
        color: {p.text_secondary};
        background-color: {p.surface_alt};
    }}
    QPushButton#primaryButton {{
        background-color: {p.accent};
        color: {p.text_on_accent};
        border: 1px solid {p.accent};
        font-weight: 600;
    }}
    QPushButton#primaryButton:hover {{
        background-color: {p.accent_hover};
        border-color: {p.accent_hover};
    }}
    QPushButton#primaryButton:pressed {{
        background-color: {p.accent_pressed};
    }}
    QPushButton#sendButton {{
        background-color: {p.accent};
        color: {p.text_on_accent};
        border: none;
        border-radius: 18px;
        min-width: 36px;
        max-width: 36px;
        min-height: 36px;
        max-height: 36px;
        padding: 0;
    }}
    QPushButton#sendButton:hover {{
        background-color: {p.accent_hover};
    }}
    QLineEdit#composerInput {{
        background-color: {p.surface_alt};
        border: 1px solid {p.border};
        border-radius: 18px;
        padding: 10px 16px;
        color: {p.text_primary};
        selection-background-color: {p.accent};
    }}
    QLineEdit#composerInput:focus {{
        border: 2px solid {p.accent};
        padding: 9px 15px;
    }}
    QScrollArea {{
        border: none;
        background: transparent;
    }}
    QScrollBar:vertical {{
        background: transparent;
        width: 10px;
        margin: 4px;
    }}
    QScrollBar::handle:vertical {{
        background: {p.border_strong};
        border-radius: 5px;
        min-height: 24px;
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}
    QMenuBar {{
        background-color: {p.surface};
        border-bottom: 1px solid {p.border};
    }}
    QMenuBar::item:selected {{
        background-color: {p.accent_light};
    }}
    """
