"""KPI metric card — clean enterprise stat display."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QSizePolicy, QVBoxLayout

from smartinstall.ui.components.ui_card import CARD_INNER_SPACING, apply_card_style
from smartinstall.ui.theme.cctech_theme import CCTechPalette, label_transparent, muted_stylesheet


class StatCard(QFrame):
    """Dashboard KPI card — title, large value, and subtitle."""

    def __init__(
        self,
        *,
        title: str,
        value: str,
        subtitle: str,
        palette: CCTechPalette,
        parent=None,
    ) -> None:
        super().__init__(parent)
        p = palette
        apply_card_style(self, p, object_name="statCard")
        self.setMinimumHeight(96)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(8)

        title_lbl = QLabel(title.upper())
        title_lbl.setStyleSheet(
            label_transparent(
                muted_stylesheet(p)
                + " font-weight: 700; letter-spacing: 0.8px; font-size: 8pt;"
            )
        )

        value_lbl = QLabel(value)
        value_lbl.setStyleSheet(
            label_transparent(
                f"color: {p.blue_600}; font-size: 28pt; font-weight: 700;"
            )
        )

        sub_lbl = QLabel(subtitle)
        sub_lbl.setWordWrap(True)
        sub_lbl.setStyleSheet(label_transparent(muted_stylesheet(p)))

        layout.addWidget(title_lbl)
        layout.addWidget(value_lbl)
        layout.addStretch(1)
        layout.addWidget(sub_lbl)
