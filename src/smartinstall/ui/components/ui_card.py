"""Shared enterprise card styling — single design language across pages."""

from __future__ import annotations

from PySide6.QtWidgets import QFrame, QVBoxLayout, QWidget

from smartinstall.ui.theme.cctech_theme import CCTechPalette, card_stylesheet

# Layout tokens (use everywhere for alignment)
PAGE_MARGIN = 24
PAGE_SPACING = 16
CARD_PADDING = 20
CARD_INNER_SPACING = 12
GRID_GAP = 16
CARD_RADIUS = 12


def apply_card_style(frame: QFrame, palette: CCTechPalette, *, object_name: str = "enterpriseCard") -> None:
    """Apply consistent surface card chrome (border only, no shadow)."""
    frame.setObjectName(object_name)
    frame.setStyleSheet(card_stylesheet(palette, object_name))


def section_card(
    palette: CCTechPalette,
    *,
    object_name: str = "sectionCard",
    parent: QWidget | None = None,
) -> tuple[QFrame, QVBoxLayout]:
    """Create a padded section card with empty layout for content."""
    card = QFrame(parent)
    apply_card_style(card, palette, object_name=object_name)
    layout = QVBoxLayout(card)
    layout.setContentsMargins(CARD_PADDING, CARD_PADDING - 2, CARD_PADDING, CARD_PADDING)
    layout.setSpacing(CARD_INNER_SPACING)
    return card, layout
