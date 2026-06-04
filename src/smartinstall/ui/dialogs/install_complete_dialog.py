"""Single completion popup after an installation finishes."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QVBoxLayout

from smartinstall.ui.components.enterprise_button import hero_outline_button, hero_primary_button
from smartinstall.ui.theme.cctech_theme import CCTechPalette, body_stylesheet, heading_stylesheet


class InstallCompleteDialog(QDialog):
    """Shown once when a monitored installation completes successfully."""

    open_monitoring = Signal()
    open_troubleshooting = Signal()

    def __init__(
        self,
        palette: CCTechPalette,
        *,
        installer_name: str,
        outcome: str,
        report_path: str,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._palette = palette
        self.setWindowTitle("Installation Complete")
        self.setModal(True)
        self.resize(480, 240)
        self._build_ui(
            installer_name=installer_name,
            outcome=outcome,
            report_path=report_path,
        )

    def _build_ui(self, *, installer_name: str, outcome: str, report_path: str) -> None:
        p = self._palette
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        headline = QLabel("Installation finished")
        headline.setStyleSheet(heading_stylesheet(p, size_pt=14))
        layout.addWidget(headline)

        body = QLabel(
            f"<b>{installer_name}</b> completed with outcome: <b>{outcome}</b>."
        )
        body.setTextFormat(Qt.TextFormat.RichText)
        body.setWordWrap(True)
        body.setStyleSheet(body_stylesheet(p))
        layout.addWidget(body)

        report_lbl = QLabel(f"Report: {report_path}")
        report_lbl.setWordWrap(True)
        report_lbl.setStyleSheet(body_stylesheet(p))
        layout.addWidget(report_lbl)

        layout.addStretch(1)
        actions = QHBoxLayout()
        actions.addStretch(1)
        dismiss = hero_outline_button("Dismiss", p, parent=self)
        dismiss.clicked.connect(self.accept)
        view = hero_primary_button("View Monitoring", p, parent=self)
        view.clicked.connect(self._emit_open)
        actions.addWidget(dismiss)
        actions.addWidget(view)
        layout.addLayout(actions)

    def _emit_open(self) -> None:
        self.open_monitoring.emit()
        self.accept()
