"""Capability card — enterprise feature showcase."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout

from smartinstall.ui.components.ui_card import apply_card_style
from smartinstall.ui.theme.cctech_theme import (
    CCTechPalette,
    body_stylesheet,
    heading_stylesheet,
    label_transparent,
)


class FeatureCard(QFrame):
    """Icon + headline + description capability card."""

    def __init__(
        self,
        *,
        icon: str,
        title: str,
        description: str,
        palette: CCTechPalette,
        parent=None,
    ) -> None:
        super().__init__(parent)
        p = palette
        apply_card_style(self, p, object_name="featureCard")
        self.setMinimumHeight(132)
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        root = QHBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(14)

        icon_wrap = QFrame()
        icon_wrap.setFixedSize(44, 44)
        icon_wrap.setStyleSheet(
            f"""
            QFrame {{
                background: {p.info_bg};
                border: 1px solid {p.info_border};
                border-radius: 10px;
            }}
            """
        )
        icon_layout = QVBoxLayout(icon_wrap)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_lbl = QLabel(icon)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet(label_transparent("font-size: 20pt;"))
        icon_layout.addWidget(icon_lbl)

        text_col = QVBoxLayout()
        text_col.setSpacing(6)

        title_lbl = QLabel(title)
        title_lbl.setWordWrap(True)
        title_lbl.setStyleSheet(heading_stylesheet(p, size_pt=11))

        body_lbl = QLabel(description)
        body_lbl.setWordWrap(True)
        body_lbl.setStyleSheet(body_stylesheet(p))

        text_col.addWidget(title_lbl)
        text_col.addWidget(body_lbl)
        text_col.addStretch(1)

        root.addWidget(icon_wrap, alignment=Qt.AlignmentFlag.AlignTop)
        root.addLayout(text_col, stretch=1)
