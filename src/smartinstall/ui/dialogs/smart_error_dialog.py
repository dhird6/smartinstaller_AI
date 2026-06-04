"""Lightweight troubleshooting popup for installation errors."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from smartinstall.ui.components.enterprise_button import hero_outline_button, hero_primary_button
from smartinstall.ui.theme.cctech_theme import CCTechPalette, body_stylesheet, heading_stylesheet


class SmartErrorDialog(QDialog):
    """Modal popup with AI-oriented troubleshooting summary."""

    open_dashboard = Signal(str)
    view_details = Signal()
    open_troubleshooting = Signal()

    def __init__(
        self,
        palette: CCTechPalette,
        *,
        title: str,
        error_code: str,
        error_message: str,
        root_cause: str,
        suggested_solution: str,
        confidence: float,
        session_id: str,
        slm_summary: str = "",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._palette = palette
        self._session_id = session_id
        self.setWindowTitle("Installation Error Detected")
        self.setModal(True)
        self.resize(520, 420)
        self._build_ui(
            title=title,
            error_code=error_code,
            error_message=error_message,
            root_cause=root_cause,
            suggested_solution=suggested_solution,
            confidence=confidence,
            slm_summary=slm_summary,
        )

    def _build_ui(
        self,
        *,
        title: str,
        error_code: str,
        error_message: str,
        root_cause: str,
        suggested_solution: str,
        confidence: float,
        slm_summary: str = "",
    ) -> None:
        p = self._palette
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        headline = QLabel("Installation Completed With Issues")
        headline.setStyleSheet(heading_stylesheet(p, size_pt=14))
        layout.addWidget(headline)

        rows: list[tuple[str, str]] = [
            ("Error", f"{error_code}: {error_message}" if error_code else error_message),
            ("Possible cause", root_cause or "Under analysis"),
            ("Suggested solution", suggested_solution),
            ("Confidence", f"{int(confidence * 100)}%"),
        ]
        if slm_summary.strip():
            rows.insert(3, ("AI troubleshooting (SLM)", slm_summary.strip()[:1200]))

        for label_text, value in rows:
            lbl = QLabel(f"<b>{label_text}</b>")
            lbl.setStyleSheet(body_stylesheet(p))
            val = QLabel(value)
            val.setWordWrap(True)
            val.setStyleSheet(body_stylesheet(p))
            layout.addWidget(lbl)
            layout.addWidget(val)

        layout.addStretch(1)
        actions = QHBoxLayout()
        actions.addStretch(1)
        details_btn = hero_outline_button("View Details", p, parent=self)
        details_btn.clicked.connect(self._emit_details)
        ts_btn = hero_primary_button("Open Troubleshooting", p, parent=self)
        ts_btn.clicked.connect(self._emit_troubleshooting)
        actions.addWidget(details_btn)
        actions.addWidget(ts_btn)
        layout.addLayout(actions)

    def _emit_details(self) -> None:
        self.view_details.emit()
        self.accept()

    def _emit_troubleshooting(self) -> None:
        self.open_troubleshooting.emit()
        self.open_dashboard.emit(self._session_id)
        self.accept()
