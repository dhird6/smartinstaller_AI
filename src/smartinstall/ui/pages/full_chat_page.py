"""Full-page ChatGPT-style AI workspace."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

from smartinstall.ui.components.ui_card import PAGE_MARGIN, apply_card_style
from smartinstall.ui.layout.responsive import configure_page_container
from smartinstall.ui.resources.brand_assets import load_brand_logo_pixmap
from smartinstall.ui.theme.cctech_theme import CCTechPalette, body_stylesheet, heading_stylesheet
from smartinstall.ui.widgets.chat_panel import ChatPanel


class FullChatPage(QWidget):
    """Dedicated conversational workspace — ask questions, review errors, get AI help."""

    def __init__(self, palette: CCTechPalette, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._palette = palette
        self._chat: ChatPanel | None = None
        self._chat_slot: QVBoxLayout | None = None
        self.setObjectName("fullChatPage")
        configure_page_container(self)
        self._build_ui()

    def _build_ui(self) -> None:
        p = self._palette
        self.setStyleSheet(f"QWidget#fullChatPage {{ background: {p.canvas}; }}")

        root = QVBoxLayout(self)
        root.setContentsMargins(PAGE_MARGIN, PAGE_MARGIN, PAGE_MARGIN, PAGE_MARGIN)
        root.setSpacing(12)

        header = QFrame()
        header.setMinimumWidth(0)
        header.setObjectName("fullChatHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(4, 0, 4, 0)
        header_layout.setSpacing(14)

        logo = QLabel()
        logo.setPixmap(load_brand_logo_pixmap(40))
        logo.setFixedSize(40, 40)
        logo.setStyleSheet("background: transparent;")
        header_layout.addWidget(logo, alignment=Qt.AlignmentFlag.AlignVCenter)

        titles = QVBoxLayout()
        titles.setSpacing(2)
        title = QLabel("AI Assistant")
        title.setStyleSheet(heading_stylesheet(p, size_pt=16))
        sub = QLabel(
            "Conversational support for installation monitoring, error analysis, "
            "and knowledge-base troubleshooting."
        )
        sub.setWordWrap(True)
        sub.setStyleSheet(body_stylesheet(p))
        titles.addWidget(title)
        titles.addWidget(sub)
        header_layout.addLayout(titles, stretch=1)
        root.addWidget(header)

        self._error_banner = QFrame()
        self._error_banner.setObjectName("fullChatError")
        self._error_banner.hide()
        err_layout = QHBoxLayout(self._error_banner)
        err_layout.setContentsMargins(14, 12, 14, 12)
        self._error_label = QLabel()
        self._error_label.setWordWrap(True)
        self._error_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        err_layout.addWidget(self._error_label)
        root.addWidget(self._error_banner)

        self._session_label = QLabel("Ready — send a message to begin")
        self._session_label.setWordWrap(True)
        self._session_label.setStyleSheet(
            f"""
            color: {p.text_secondary};
            background: {p.surface_muted};
            border: 1px solid {p.border};
            border-radius: 8px;
            padding: 8px 14px;
            font-size: 9.5pt;
            """
        )
        root.addWidget(self._session_label)

        self._chat_frame = QFrame()
        apply_card_style(self._chat_frame, p, object_name="fullChatFrame")
        self._chat_frame.setMinimumHeight(240)
        self._chat_frame.setMinimumWidth(0)
        self._chat_frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        chat_outer = QVBoxLayout(self._chat_frame)
        chat_outer.setContentsMargins(0, 0, 0, 0)
        chat_outer.setSpacing(0)
        self._chat_slot = chat_outer
        root.addWidget(self._chat_frame, stretch=1)

        self._apply_error_banner_style()

    def _apply_error_banner_style(self) -> None:
        p = self._palette
        self._error_banner.setStyleSheet(
            f"""
            QFrame#fullChatError {{
                background: {p.error_bg};
                border: 1px solid {p.error_border};
                border-radius: 10px;
            }}
            QLabel {{
                color: {p.error};
                font-size: 10pt;
                background: transparent;
            }}
            """
        )

    def attach_chat(self, panel: ChatPanel) -> None:
        if self._chat_slot is None:
            return
        if self._chat is not None:
            self.detach_chat()
        self._chat = panel
        panel.set_variant_light()
        panel.setParent(self._chat_frame)
        panel.setStyleSheet(f"background: {self._palette.surface};")
        self._chat_slot.addWidget(panel, stretch=1)
        panel.show()

    def detach_chat(self) -> ChatPanel | None:
        if self._chat is None or self._chat_slot is None:
            return None
        self._chat_slot.removeWidget(self._chat)
        self._chat.setParent(None)
        chat = self._chat
        self._chat = None
        return chat

    def set_context(self, text: str) -> None:
        self._session_label.setText(f"Session: {text}")

    def show_error_notice(self, message: str) -> None:
        """Display install / diagnostic errors at the top of the chat workspace."""
        self._error_label.setText(message)
        self._error_banner.show()

    def clear_error_notice(self) -> None:
        self._error_banner.hide()
