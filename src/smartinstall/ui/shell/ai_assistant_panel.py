"""Persistent left-side AI Assistant panel."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

from smartinstall.ui.theme.cctech_theme import CCTechPalette
from smartinstall.ui.widgets.avatar_label import AvatarLabel, icon_pixmap
from smartinstall.ui.widgets.chat_panel import ChatPanel


class AiAssistantPanel(QFrame):
    """Full-height enterprise chatbot workspace."""

    def __init__(self, palette: CCTechPalette, chat: ChatPanel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._chat = chat
        self.setFixedWidth(400)
        self.setObjectName("aiAssistantPanel")
        self._build_ui(palette)

    def _build_ui(self, p: CCTechPalette) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QFrame()
        header.setObjectName("assistantHeader")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(20, 20, 20, 16)
        header_layout.setSpacing(10)

        brand_row = QWidget()
        brand_layout = QVBoxLayout(brand_row)
        brand_layout.setContentsMargins(0, 0, 0, 0)
        brand_layout.setSpacing(8)

        logo_row = QWidget()
        logo_h = QVBoxLayout(logo_row)
        logo_h.setContentsMargins(0, 0, 0, 0)
        icon = AvatarLabel("assistant.svg", size=48)
        logo_h.addWidget(icon, alignment=Qt.AlignmentFlag.AlignLeft)

        title = QLabel("SmartInstall AI Assistant")
        title.setStyleSheet(
            f"color: {p.text_inverse}; font-size: 14pt; font-weight: 700;"
        )
        subtitle = QLabel("Autonomous installation troubleshooting • Local SLM")
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(f"color: {p.text_muted_inverse}; font-size: 9pt;")
        brand_layout.addWidget(logo_row)
        brand_layout.addWidget(title)
        brand_layout.addWidget(subtitle)

        context = QLabel("Session context: Ready for commands")
        context.setObjectName("assistantContext")
        context.setWordWrap(True)
        context.setStyleSheet(
            f"""
            color: {p.cyan_300};
            background: rgba(34, 211, 238, 0.12);
            border: 1px solid rgba(34, 211, 238, 0.25);
            border-radius: 10px;
            padding: 10px 12px;
            font-size: 9pt;
            """
        )
        header_layout.addWidget(brand_row)
        header_layout.addWidget(context)
        self._context_label = context

        header.setStyleSheet("background: transparent;")
        layout.addWidget(header)

        self._chat.setStyleSheet("background: transparent;")
        layout.addWidget(self._chat, stretch=1)

        footer = QLabel("Powered by CCTech • Ollama • RAG")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet(
            f"color: {p.text_muted_inverse}; font-size: 8pt; padding: 8px;"
        )
        layout.addWidget(footer)

        self.setStyleSheet(
            f"""
            QFrame#aiAssistantPanel {{
                background: {p.assistant_panel_bg};
                border-right: 1px solid rgba(255,255,255,0.08);
            }}
            """
        )

    @property
    def chat(self) -> ChatPanel:
        return self._chat

    def set_context(self, text: str) -> None:
        self._context_label.setText(f"Session context: {text}")
