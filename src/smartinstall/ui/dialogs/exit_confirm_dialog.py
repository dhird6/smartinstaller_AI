"""Confirm exit when a monitored installation is still in progress."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QVBoxLayout

from smartinstall.ui.components.enterprise_button import hero_outline_button, hero_primary_button
from smartinstall.ui.theme.cctech_theme import CCTechPalette, body_stylesheet, heading_stylesheet


class ExitConfirmDialog(QDialog):
    """Ask the user to confirm quitting while monitoring or installation is active."""

    def __init__(
        self,
        palette: CCTechPalette,
        *,
        detail: str,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._palette = palette
        self.setWindowTitle("Exit SmartInstall AI")
        self.setModal(True)
        self.resize(480, 220)
        self._build_ui(detail=detail)

    def _build_ui(self, *, detail: str) -> None:
        p = self._palette
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        heading = QLabel("Exit while installation is in progress?")
        heading.setStyleSheet(heading_stylesheet(p, size_pt=14))
        layout.addWidget(heading)

        body = QLabel(detail)
        body.setTextFormat(Qt.TextFormat.RichText)
        body.setWordWrap(True)
        body.setStyleSheet(body_stylesheet(p))
        layout.addWidget(body)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        stay_btn = hero_primary_button(p, "Stay")
        stay_btn.clicked.connect(self.reject)
        exit_btn = hero_outline_button(p, "Exit anyway")
        exit_btn.clicked.connect(self.accept)
        buttons.addWidget(stay_btn)
        buttons.addWidget(exit_btn)
        layout.addLayout(buttons)
