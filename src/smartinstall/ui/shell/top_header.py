"""Top navigation bar — page title only."""

from __future__ import annotations

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout

from smartinstall.ui.theme.cctech_theme import CCTechPalette, label_transparent


class TopHeader(QFrame):
    """Compact header with page title."""

    def __init__(self, palette: CCTechPalette, parent=None) -> None:
        super().__init__(parent)
        self._palette = palette
        self.setObjectName("topHeader")
        self.setFixedHeight(52)
        self._page_title = QLabel("Home Dashboard")
        self._build_ui()

    def _build_ui(self) -> None:
        p = self._palette
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 20, 0)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title_col.setContentsMargins(0, 0, 0, 0)

        breadcrumb = QLabel("Smart Installer AI")
        breadcrumb.setObjectName("headerBreadcrumb")
        self._page_title.setObjectName("headerTitle")
        title_col.addWidget(breadcrumb)
        title_col.addWidget(self._page_title)
        layout.addLayout(title_col)
        layout.addStretch(1)

        self.setStyleSheet(
            f"""
            QFrame#topHeader {{
                background: {p.surface};
                border-bottom: 1px solid {p.border};
            }}
            QLabel#headerBreadcrumb {{
                {label_transparent(f"color: {p.text_muted}; font-size: 8pt; font-weight: 500;")}
            }}
            QLabel#headerTitle {{
                {label_transparent(f"color: {p.text_primary}; font-size: 15pt; font-weight: 600;")}
            }}
            """
        )

    def set_page_title(self, title: str) -> None:
        self._page_title.setText(title)
