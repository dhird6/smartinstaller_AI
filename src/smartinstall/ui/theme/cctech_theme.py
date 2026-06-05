"""CCTech enterprise design system — clean, professional, consistent."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

from smartinstall.ui.theme.fonts import FONT_FAMILY_CSS, app_font


@dataclass(frozen=True, slots=True)
class CCTechPalette:
    """Single source of truth for all design tokens."""

    # ── Brand ──────────────────────────────────────────────────────────────
    navy_950: str = "#070e1c"
    navy_900: str = "#0b1628"
    navy_800: str = "#0f2340"
    navy_700: str = "#163558"
    blue_600: str = "#1e5bff"
    blue_500: str = "#4379ff"
    cyan_500: str = "#06b6d4"
    cyan_400: str = "#22d3ee"
    cyan_300: str = "#67e8f9"
    orange_500: str = "#f97316"
    orange_400: str = "#fb923c"

    # ── Surfaces ───────────────────────────────────────────────────────────
    canvas: str = "#f0f4fa"          # page background
    surface: str = "#ffffff"         # card / panel background
    surface_muted: str = "#f8fafc"   # subtle hover / alt row
    surface_hover: str = "#f1f5f9"   # interactive hover

    # ── Text ───────────────────────────────────────────────────────────────
    text_primary: str = "#0d1526"    # headings, important values
    text_secondary: str = "#4a5568"  # body copy
    text_muted: str = "#8a9ab3"      # captions, metadata
    text_inverse: str = "#f8fafc"    # on dark backgrounds
    text_on_dark_muted: str = "#c5d4e8"  # body copy on dark panels (readable)
    text_muted_inverse: str = "#9eb3d0"  # captions on dark panels

    # ── Semantic ────────────────────────────────────────────────────────────
    success: str = "#059669"
    success_bg: str = "#ecfdf5"
    success_border: str = "#6ee7b7"
    warning: str = "#d97706"
    warning_bg: str = "#fffbeb"
    warning_border: str = "#fcd34d"
    error: str = "#dc2626"
    error_bg: str = "#fef2f2"
    error_border: str = "#fca5a5"
    info: str = "#2563eb"
    info_bg: str = "#eff6ff"
    info_border: str = "#93c5fd"

    # ── Chrome ─────────────────────────────────────────────────────────────
    border: str = "#e2e8f0"
    border_strong: str = "#cbd5e1"
    border_focus: str = "#1e5bff"

    # ── Sidebar-only tokens ────────────────────────────────────────────────
    sidebar_bg: str = "#0b1628"
    sidebar_surface: str = "#111e33"   # slightly lighter for hover
    sidebar_border: str = "#1a2d4a"
    sidebar_text: str = "#a8bbd6"      # inactive nav label
    sidebar_text_active: str = "#e8f0fe"  # active nav label
    sidebar_accent: str = "#1e5bff"    # active indicator (primary blue)

    # ── Dark panels (hero, splash) — solid brand navy, no gradients ───────
    panel_dark: str = "#0b1628"
    panel_dark_border: str = "#1a2d4a"
    assistant_panel_bg: str = "#0b1628"  # legacy alias for dark chat panels


def card_stylesheet(p: CCTechPalette, object_name: str = "enterpriseCard") -> str:
    """Standard light card: white surface, subtle border, no shadow."""
    return (
        f"QFrame#{object_name} {{"
        f" background: {p.surface};"
        f" border: 1px solid {p.border};"
        f" border-radius: 14px;"
        f"}}"
        f"QFrame#{object_name} QLabel {{"
        f" background: transparent;"
        f" background-color: transparent;"
        f"}}"
    )


def muted_stylesheet(p: CCTechPalette) -> str:
    return f"color: {p.text_muted}; font-size: 9pt; background: transparent;"


def label_transparent(extra: str = "") -> str:
    """Prefix for QLabel styles so palette fill does not paint white blocks."""
    base = "background: transparent; background-color: transparent; border: none;"
    return f"{base} {extra}".strip()


def heading_stylesheet(p: CCTechPalette, *, size_pt: int = 13) -> str:
    return label_transparent(
        f"color: {p.text_primary}; font-size: {size_pt}pt; font-weight: 700;"
    )


def body_stylesheet(p: CCTechPalette) -> str:
    return label_transparent(f"color: {p.text_secondary}; font-size: 10pt;")


def hero_panel_stylesheet(p: CCTechPalette) -> str:
    """Scoped styles for dark hero — prevents global QWidget/QPushButton bleed."""
    return f"""
    QFrame#dashHero, QFrame#fullChatHero {{
        background-color: {p.panel_dark};
        border: 1px solid {p.panel_dark_border};
        border-radius: 12px;
    }}
    QFrame#dashHero QLabel, QFrame#fullChatHero QLabel {{
        background: transparent;
        background-color: transparent;
        border: none;
    }}
    QLabel#heroBadge {{
        color: {p.text_inverse};
        font-size: 8pt;
        font-weight: 600;
        letter-spacing: 1px;
        background-color: rgba(30, 91, 255, 0.22);
        border: 1px solid rgba(67, 121, 255, 0.45);
        border-radius: 6px;
        padding: 5px 12px;
    }}
    QLabel#heroTitle {{
        color: #ffffff;
        font-size: 26pt;
        font-weight: 700;
        padding: 0;
        margin: 0;
    }}
    QLabel#heroSubtitle {{
        color: {p.text_on_dark_muted};
        font-size: 10.5pt;
        line-height: 1.45;
        padding: 0;
    }}
    QLabel#heroLogo {{
        background: transparent;
        padding: 4px;
    }}
    QPushButton#heroPrimary {{
        background-color: {p.blue_600};
        color: #ffffff;
        border: none;
        border-radius: 8px;
        padding: 7px 16px;
        font-size: 9.5pt;
        font-weight: 700;
        min-height: 36px;
    }}
    QPushButton#heroPrimary:hover {{
        background-color: {p.blue_500};
    }}
    QPushButton#heroPrimary:pressed {{
        background-color: #1848cc;
    }}
    QPushButton#heroOutline {{
        background-color: rgba(255, 255, 255, 0.14);
        color: #ffffff;
        border: 1.5px solid rgba(255, 255, 255, 0.82);
        border-radius: 8px;
        padding: 7px 16px;
        font-size: 9.5pt;
        font-weight: 700;
        min-height: 36px;
    }}
    QPushButton#heroOutline:hover {{
        background-color: rgba(255, 255, 255, 0.22);
        border-color: #ffffff;
    }}
    """


def apply_cctech_theme(app: QApplication) -> CCTechPalette:
    """Apply CCTech corporate theme globally and return the palette."""
    palette = CCTechPalette()
    app.setFont(app_font(point_size=10))

    qt = QPalette()
    qt.setColor(QPalette.ColorRole.Window, QColor(palette.canvas))
    qt.setColor(QPalette.ColorRole.WindowText, QColor(palette.text_primary))
    qt.setColor(QPalette.ColorRole.Base, QColor(palette.surface))
    qt.setColor(QPalette.ColorRole.AlternateBase, QColor(palette.surface_muted))
    qt.setColor(QPalette.ColorRole.Text, QColor(palette.text_primary))
    qt.setColor(QPalette.ColorRole.Button, QColor(palette.surface))
    qt.setColor(QPalette.ColorRole.ButtonText, QColor(palette.text_primary))
    qt.setColor(QPalette.ColorRole.Highlight, QColor(palette.blue_600))
    qt.setColor(QPalette.ColorRole.HighlightedText, QColor(palette.text_inverse))
    qt.setColor(QPalette.ColorRole.PlaceholderText, QColor(palette.text_muted))
    app.setPalette(qt)
    app.setStyleSheet(_build_stylesheet(palette))
    return palette


def build_stylesheet(p: CCTechPalette) -> str:
    return _build_stylesheet(p)


def _build_stylesheet(p: CCTechPalette) -> str:  # noqa: PLR0915
    return f"""
/* ── Base ──────────────────────────────────────── */
QWidget {{
    font-family: {FONT_FAMILY_CSS};
    font-size: 10pt;
    color: {p.text_primary};
    background: transparent;
}}
QLabel {{
    background: transparent;
    background-color: transparent;
}}
QMainWindow, QDialog {{
    background: {p.canvas};
}}

/* ── Menu bar ──────────────────────────────────── */
QMenuBar {{
    background: {p.surface};
    border-bottom: 1px solid {p.border};
    padding: 2px 6px;
    font-size: 9.5pt;
    color: {p.text_secondary};
}}
QMenuBar::item {{
    padding: 5px 12px;
    border-radius: 5px;
    background: transparent;
}}
QMenuBar::item:selected {{
    background: {p.surface_hover};
    color: {p.text_primary};
}}
QMenu {{
    background: {p.surface};
    border: 1px solid {p.border};
    border-radius: 8px;
    padding: 6px 4px;
    font-size: 9.5pt;
}}
QMenu::item {{
    padding: 7px 20px 7px 14px;
    border-radius: 5px;
    color: {p.text_secondary};
}}
QMenu::item:selected {{
    background: {p.surface_hover};
    color: {p.text_primary};
}}
QMenu::separator {{
    height: 1px;
    background: {p.border};
    margin: 4px 8px;
}}

/* ── Scroll bars ────────────────────────────────── */
QScrollArea {{
    border: none;
    background: transparent;
}}
QScrollBar:vertical {{
    width: 7px;
    background: transparent;
    margin: 4px 1px;
}}
QScrollBar::handle:vertical {{
    background: {p.border_strong};
    border-radius: 3px;
    min-height: 36px;
}}
QScrollBar::handle:vertical:hover {{
    background: #94a3b8;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar:horizontal {{
    height: 7px;
    background: transparent;
    margin: 1px 4px;
}}
QScrollBar::handle:horizontal {{
    background: {p.border_strong};
    border-radius: 3px;
    min-width: 36px;
}}
QScrollBar::handle:horizontal:hover {{
    background: #94a3b8;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

/* ── Input fields ───────────────────────────────── */
QLineEdit, QTextEdit, QPlainTextEdit {{
    background: {p.surface};
    border: 1.5px solid {p.border};
    border-radius: 8px;
    padding: 9px 13px;
    color: {p.text_primary};
    selection-background-color: {p.blue_600};
    selection-color: {p.text_inverse};
}}
QLineEdit:hover, QTextEdit:hover, QPlainTextEdit:hover {{
    border-color: {p.border_strong};
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border: 2px solid {p.border_focus};
    outline: none;
}}
QLineEdit:disabled, QTextEdit:disabled {{
    background: {p.surface_muted};
    color: {p.text_muted};
    border-color: {p.border};
}}

/* ── Buttons ─────────────────────────────────────── */
QPushButton {{
    background: {p.surface};
    border: 1.5px solid {p.border};
    border-radius: 8px;
    padding: 9px 18px;
    font-size: 10pt;
    font-weight: 600;
    color: {p.text_secondary};
}}
QPushButton:hover {{
    background: {p.surface_hover};
    border-color: {p.border_strong};
    color: {p.text_primary};
}}
QPushButton:pressed {{
    background: #e9eef6;
    border-color: {p.border_strong};
}}
QPushButton:disabled {{
    background: {p.surface_muted};
    color: {p.text_muted};
    border-color: {p.border};
}}
QPushButton#primaryBtn {{
    background: {p.blue_600};
    color: {p.text_inverse};
    border: none;
    border-radius: 8px;
    padding: 7px 16px;
    font-size: 9.5pt;
    font-weight: 700;
    min-height: 36px;
}}
QPushButton#primaryBtn:hover {{
    background: {p.blue_500};
}}
QPushButton#primaryBtn:pressed {{
    background: #1848cc;
}}
QPushButton#primaryBtn:disabled {{
    background: {p.border};
    color: {p.text_muted};
}}
QPushButton#secondaryBtn {{
    background: {p.surface};
    color: {p.blue_600};
    border: 1.5px solid {p.blue_600};
    border-radius: 8px;
    font-size: 9.5pt;
    font-weight: 700;
    padding: 7px 16px;
    min-height: 36px;
}}
QPushButton#secondaryBtn:hover {{
    background: #eff4ff;
    border-color: {p.blue_500};
}}
QPushButton#secondaryHeroBtn {{
    background: transparent;
    color: {p.text_inverse};
    border: 1.5px solid rgba(255,255,255,0.35);
    border-radius: 8px;
    padding: 10px 22px;
    font-weight: 600;
}}
QPushButton#secondaryHeroBtn:hover {{
    background: rgba(255,255,255,0.08);
    border-color: rgba(255,255,255,0.55);
}}
QPushButton#ghostBtn {{
    background: transparent;
    border: 1.5px solid {p.border};
    color: {p.text_muted};
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: 500;
}}
QPushButton#ghostBtn:hover {{
    border-color: {p.border_strong};
    color: {p.text_secondary};
    background: {p.surface_muted};
}}
QPushButton[loading="true"] {{
    background: {p.surface_muted};
    color: {p.text_muted};
    border-color: {p.border};
}}
QPushButton#chatFab {{
    background: {p.blue_600};
    color: {p.text_inverse};
    border: 1px solid {p.blue_500};
    border-radius: 31px;
    padding: 0;
    min-width: 62px;
    max-width: 62px;
    min-height: 62px;
    max-height: 62px;
}}
QPushButton#chatFab:hover {{
    background: {p.blue_500};
}}

/* ── Progress bar ────────────────────────────────── */
QProgressBar {{
    border: none;
    background: {p.border};
    border-radius: 4px;
    max-height: 7px;
    min-height: 7px;
    text-align: center;
    color: transparent;
}}
QProgressBar::chunk {{
    background: {p.blue_600};
    border-radius: 4px;
}}

/* ── Tool button ─────────────────────────────────── */
QToolButton {{
    background: transparent;
    border: none;
    border-radius: 6px;
    padding: 6px;
    color: {p.text_secondary};
}}
QToolButton:hover {{
    background: {p.surface_hover};
    color: {p.text_primary};
}}

/* ── Tooltip ─────────────────────────────────────── */
QToolTip {{
    background: {p.navy_900};
    color: {p.text_inverse};
    border: 1px solid {p.sidebar_border};
    border-radius: 6px;
    padding: 5px 10px;
    font-size: 9pt;
}}

/* ── Splitter ─────────────────────────────────────── */
QSplitter::handle {{
    background: {p.border};
    width: 1px;
    height: 1px;
}}
"""
