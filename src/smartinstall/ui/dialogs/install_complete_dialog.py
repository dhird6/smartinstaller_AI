"""Single completion popup after an installation finishes."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QVBoxLayout

from smartinstall.ui.components.enterprise_button import hero_outline_button, hero_primary_button
from smartinstall.ui.theme.cctech_theme import CCTechPalette, body_stylesheet, heading_stylesheet


class InstallCompleteDialog(QDialog):
    """Shown once when a monitored installation completes successfully."""

    view_details = Signal()
    open_monitoring = Signal()

    def __init__(
        self,
        palette: CCTechPalette,
        *,
        installer_name: str,
        outcome: str,
        report_path: str,
        error_count: int = 0,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._palette = palette
        self.setWindowTitle("Installation Complete")
        self.setModal(True)
        self.resize(520, 260)
        self._build_ui(
            installer_name=installer_name,
            outcome=outcome,
            report_path=report_path,
            error_count=error_count,
        )

    def _build_ui(
        self,
        *,
        installer_name: str,
        outcome: str,
        report_path: str,
        error_count: int,
    ) -> None:
        p = self._palette
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        success = error_count == 0 and outcome.lower() in {"success", "completed"}
        if success:
            headline = QLabel("Installation Completed Successfully")
            body_text = (
                f"<b>{installer_name}</b> finished successfully.<br>"
                "Smart Installer monitored the installation and found no critical issues."
            )
        else:
            headline = QLabel("Installation Completed With Issues")
            body_text = (
                f"<b>{installer_name}</b> finished with outcome: <b>{outcome}</b>.<br>"
                f"Detected errors: <b>{error_count}</b><br>"
                "AI recommendations are available in the dashboard."
            )

        headline.setStyleSheet(heading_stylesheet(p, size_pt=14))
        layout.addWidget(headline)

        body = QLabel(body_text)
        body.setTextFormat(Qt.TextFormat.RichText)
        body.setWordWrap(True)
        body.setStyleSheet(body_stylesheet(p))
        layout.addWidget(body)

        if report_path:
            report_lbl = QLabel(f"Report: {report_path}")
            report_lbl.setWordWrap(True)
            report_lbl.setStyleSheet(body_stylesheet(p))
            layout.addWidget(report_lbl)

        layout.addStretch(1)
        actions = QHBoxLayout()
        actions.addStretch(1)
        close_btn = hero_outline_button("Close", p, parent=self)
        close_btn.clicked.connect(self.accept)
        details_btn = hero_primary_button("View Details", p, parent=self)
        details_btn.clicked.connect(self._emit_details)
        actions.addWidget(close_btn)
        actions.addWidget(details_btn)
        layout.addLayout(actions)

    def _emit_details(self) -> None:
        self.view_details.emit()
        self.accept()
