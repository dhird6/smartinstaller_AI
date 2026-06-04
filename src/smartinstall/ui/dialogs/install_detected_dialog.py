"""Non-blocking-style dialog when automatic monitoring starts."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QVBoxLayout

from smartinstall.ui.components.enterprise_button import hero_outline_button, hero_primary_button
from smartinstall.ui.theme.cctech_theme import CCTechPalette, body_stylesheet, heading_stylesheet


class InstallDetectedDialog(QDialog):
    """First popup when the user starts an installer — live monitoring is active."""

    view_monitoring = Signal()

    def __init__(
        self,
        palette: CCTechPalette,
        *,
        installer_name: str,
        detail: str = "",
        mode_label: str = "automatic",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._palette = palette
        self.setWindowTitle("SmartInstall AI — Live Monitoring")
        self.setModal(True)
        self.resize(500, 260)
        self._build_ui(
            installer_name=installer_name,
            detail=detail,
            mode_label=mode_label,
        )

    def _build_ui(self, *, installer_name: str, detail: str, mode_label: str) -> None:
        p = self._palette
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        headline = QLabel("Live monitoring is active")
        headline.setStyleSheet(heading_stylesheet(p, size_pt=14))
        layout.addWidget(headline)

        body = QLabel(
            "SmartInstall AI is now <b>live monitoring</b> your installation. "
            f"Installer: <b>{installer_name}</b><br>"
            "Process logs, registry changes, and evidence are being captured in real time."
        )
        body.setTextFormat(Qt.TextFormat.RichText)
        body.setWordWrap(True)
        body.setStyleSheet(body_stylesheet(p))
        layout.addWidget(body)

        mode_lbl = QLabel(f"Mode: {mode_label}")
        mode_lbl.setStyleSheet(body_stylesheet(p))
        layout.addWidget(mode_lbl)

        if detail:
            extra = QLabel(detail)
            extra.setWordWrap(True)
            extra.setStyleSheet(body_stylesheet(p))
            layout.addWidget(extra)

        layout.addStretch(1)
        actions = QHBoxLayout()
        actions.addStretch(1)
        dismiss = hero_outline_button("Continue in background", p, parent=self)
        dismiss.clicked.connect(self.reject)
        view = hero_primary_button("View Live Monitoring", p, parent=self)
        view.clicked.connect(self._open_monitoring)
        actions.addWidget(dismiss)
        actions.addWidget(view)
        layout.addLayout(actions)

    def _open_monitoring(self) -> None:
        self.view_monitoring.emit()
        self.accept()
