"""Standard content card (legacy name retained for imports)."""

from __future__ import annotations

from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout

from smartinstall.ui.components.ui_card import apply_card_style
from smartinstall.ui.theme.cctech_theme import CCTechPalette, heading_stylesheet


class GlassCard(QFrame):
    """Light surface card with title and body slot."""

    def __init__(
        self,
        *,
        title: str,
        palette: CCTechPalette,
        parent=None,
    ) -> None:
        super().__init__(parent)
        apply_card_style(self, palette, object_name="glassCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        heading = QLabel(title)
        heading.setStyleSheet(heading_stylesheet(palette, size_pt=11))
        layout.addWidget(heading)
        self._body_layout = QVBoxLayout()
        self._body_layout.setSpacing(8)
        layout.addLayout(self._body_layout)

    def add_body_widget(self, widget) -> None:
        self._body_layout.addWidget(widget)
