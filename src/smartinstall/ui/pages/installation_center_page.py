"""Manual installation monitoring — browse, upload, and start workflows."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QComboBox, QFrame, QLabel, QVBoxLayout, QWidget

from smartinstall.ui.components.enterprise_button import hero_outline_button, hero_primary_button
from smartinstall.ui.components.ui_card import PAGE_MARGIN, PAGE_SPACING, section_card
from smartinstall.ui.theme.cctech_theme import CCTechPalette, body_stylesheet, heading_stylesheet, muted_stylesheet


class InstallationCenterPage(QWidget):
    """Dedicated page for manual (Mode 2) installer monitoring."""

    browse_requested = Signal()
    upload_requested = Signal()
    manual_monitor_requested = Signal()
    test_install_requested = Signal(str)

    def __init__(self, palette: CCTechPalette, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._palette = palette
        self.setObjectName("installCenterPage")
        self.setStyleSheet(f"QWidget#installCenterPage {{ background: {palette.canvas}; }}")
        self._build_ui()

    def _build_ui(self) -> None:
        p = self._palette
        root = QVBoxLayout(self)
        root.setContentsMargins(PAGE_MARGIN, PAGE_MARGIN, PAGE_MARGIN, PAGE_MARGIN)
        root.setSpacing(PAGE_SPACING)

        title = QLabel("Installation Center")
        title.setStyleSheet(heading_stylesheet(p, size_pt=16))
        root.addWidget(title)

        subtitle = QLabel(
            "Manual monitoring mode — browse or upload an installer, then start a "
            "fully monitored session. Automatic detection runs in the background when enabled."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(muted_stylesheet(p))
        root.addWidget(subtitle)

        card, layout = section_card(p)
        heading = QLabel("Manual monitoring (Mode 2)")
        heading.setStyleSheet(heading_stylesheet(p, size_pt=12))
        layout.addWidget(heading)

        browse = hero_primary_button("Browse installer", p, parent=card)
        browse.clicked.connect(self.browse_requested.emit)
        upload = hero_outline_button("Upload to installers folder", p, parent=card)
        upload.clicked.connect(self.upload_requested.emit)
        start = hero_outline_button("Start monitoring selected file", p, parent=card)
        start.clicked.connect(self.manual_monitor_requested.emit)

        for widget in (browse, upload, start):
            layout.addWidget(widget)

        note = QLabel(
            "Supported: .exe and .msi · Elevation and evidence collection match enterprise policy."
        )
        note.setWordWrap(True)
        note.setStyleSheet(body_stylesheet(p))
        layout.addWidget(note)
        root.addWidget(card)

        auto_card, auto_layout = section_card(p)
        auto_heading = QLabel("Automatic monitoring (Mode 1)")
        auto_heading.setStyleSheet(heading_stylesheet(p, size_pt=12))
        auto_layout.addWidget(auto_heading)
        auto_body = QLabel(
            "Launch installers from Windows Explorer — the background service detects "
            "setup processes and begins live monitoring without opening this page."
        )
        auto_body.setWordWrap(True)
        auto_body.setStyleSheet(body_stylesheet(p))
        auto_layout.addWidget(auto_body)
        root.addWidget(auto_card)

        test_card, test_layout = section_card(p)
        test_heading = QLabel("Bundled test installer (failure injection)")
        test_heading.setStyleSheet(heading_stylesheet(p, size_pt=12))
        test_layout.addWidget(test_heading)
        test_body = QLabel(
            "Run the bundled TestAppSetup.exe with a failure scenario. Smart Installer "
            "monitors the session so you can validate detection, RAG troubleshooting, and recovery."
        )
        test_body.setWordWrap(True)
        test_body.setStyleSheet(body_stylesheet(p))
        test_layout.addWidget(test_body)

        self._scenario_combo = QComboBox(parent=test_card)
        self._scenario_combo.setMinimumWidth(200)
        test_layout.addWidget(self._scenario_combo)

        test_btn = hero_primary_button("Run test install scenario", p, parent=test_card)
        test_btn.clicked.connect(self._emit_test_install)
        test_layout.addWidget(test_btn)
        root.addWidget(test_card)
        root.addStretch(1)

    def set_test_scenarios(self, scenarios: list[tuple[str, str]]) -> None:
        """Populate scenario picker with (id, label) pairs."""
        self._scenario_combo.clear()
        for scenario_id, label in scenarios:
            self._scenario_combo.addItem(label, scenario_id)

    def _emit_test_install(self) -> None:
        scenario_id = self._scenario_combo.currentData()
        if scenario_id:
            self.test_install_requested.emit(str(scenario_id))
