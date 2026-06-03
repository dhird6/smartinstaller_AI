"""Branded startup splash screen."""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QHBoxLayout, QLabel, QProgressBar, QVBoxLayout, QWidget

from smartinstall.ui.resources.brand_assets import load_brand_logo_pixmap
from smartinstall.ui.theme.cctech_theme import CCTechPalette


class SplashScreen(QWidget):
    """Short-lived loading splash with CCTech branding."""

    def __init__(self, palette: CCTechPalette, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.SplashScreen | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setFixedSize(480, 300)
        self._palette = palette
        self._build_ui()

    def _build_ui(self) -> None:
        p = self._palette
        self.setStyleSheet(
            f"""
            QWidget {{
                background: {p.panel_dark};
                border: 1px solid {p.panel_dark_border};
                border-radius: 12px;
            }}
            QLabel {{ color: {p.text_inverse}; }}
            QProgressBar {{
                border: none;
                background: rgba(255,255,255,0.12);
                border-radius: 4px;
                height: 6px;
            }}
            QProgressBar::chunk {{
                background: {p.blue_600};
                border-radius: 4px;
            }}
            """
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 36, 40, 32)
        layout.setSpacing(12)

        logo = QLabel()
        logo.setPixmap(load_brand_logo_pixmap(72))
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(logo, alignment=Qt.AlignmentFlag.AlignHCenter)

        company = QLabel("CCTech")
        company.setAlignment(Qt.AlignmentFlag.AlignCenter)
        company.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        layout.addWidget(company)

        product = QLabel("Smart Installer AI")
        product.setAlignment(Qt.AlignmentFlag.AlignCenter)
        product.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        layout.addWidget(product)

        tag = QLabel("Enterprise installation intelligence platform")
        tag.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tag.setStyleSheet(f"color: {p.text_on_dark_muted}; font-size: 10pt;")
        layout.addWidget(tag)
        layout.addStretch(1)

        self._bar = QProgressBar()
        self._bar.setRange(0, 0)
        layout.addWidget(self._bar)

        self._status = QLabel("Initializing…")
        self._status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status.setStyleSheet(f"color: {p.text_on_dark_muted}; font-size: 9pt;")
        layout.addWidget(self._status)

    def set_status(self, text: str) -> None:
        self._status.setText(text)

    def finish_after(self, callback, *, ms: int = 1400) -> None:
        QTimer.singleShot(ms, callback)
