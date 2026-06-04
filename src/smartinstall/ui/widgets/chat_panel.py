"""Enterprise chat panel — welcome, prompts, timestamps, typing indicator."""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from smartinstall.ui.models.chat_message import ChatMessage, ChatRole, ChatSection
from smartinstall.ui.resources.brand_assets import load_brand_logo_pixmap
from smartinstall.ui.theme.cctech_theme import CCTechPalette
from smartinstall.ui.widgets.avatar_label import AvatarLabel, icon_pixmap

_SUGGESTED_PROMPTS = (
    "What went wrong with the last installation?",
    "Summarize errors from the latest run",
    "How do I fix exit code 1603?",
    "list available installers",
    "install mingw-get-setup.exe",
    "What can Smart Installer AI do?",
)


class ChatPanel(QWidget):
    """Scrollable chat with welcome screen, quick actions, and rich bubbles."""

    message_submitted = Signal(str)
    prompt_chosen = Signal(str)

    def __init__(
        self,
        palette: CCTechPalette,
        *,
        variant: str = "light",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("chatPanel")
        self._palette = palette
        self._variant = variant
        self._welcome_visible = True
        self._welcome_title: QLabel | None = None
        self._welcome_sub: QLabel | None = None
        self._welcome_prompts_label: QLabel | None = None
        self._composer: QFrame | None = None
        self._typing_row: QWidget | None = None
        self._typing_timer: QTimer | None = None
        self._typing_dots = 0
        self._build_ui()
        self._show_welcome()

    def _build_ui(self) -> None:
        p = self._palette
        dark = self._variant == "dark"
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._history_container = QWidget()
        self._history_layout = QVBoxLayout(self._history_container)
        self._history_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._history_layout.setSpacing(16)
        self._history_layout.setContentsMargins(14, 10, 14, 10)

        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll_area.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        self._history_container.setStyleSheet("background: transparent;")
        self._scroll_area.setWidget(self._history_container)
        root.addWidget(self._scroll_area, stretch=1)

        quick = QHBoxLayout()
        quick.setContentsMargins(14, 6, 14, 4)
        quick.setSpacing(6)
        for label in ("Install", "List", "Help"):
            chip = QPushButton(label)
            chip.setObjectName("promptChip")
            chip.setCursor(Qt.CursorShape.PointingHandCursor)
            chip.clicked.connect(lambda checked=False, t=label: self._quick_action(t))
            quick.addWidget(chip)
        quick.addStretch(1)
        root.addLayout(quick)

        composer = QFrame()
        self._composer = composer
        composer.setObjectName("composerBar")
        composer_layout = QHBoxLayout(composer)
        composer_layout.setContentsMargins(14, 12, 14, 14)
        composer_layout.setSpacing(10)

        self._input = QLineEdit()
        self._input.setObjectName("composerInput")
        self._input.setPlaceholderText("Message SmartInstall AI…")
        self._input.returnPressed.connect(self._submit)
        if dark:
            self._input.setStyleSheet(
                f"""
                QLineEdit {{
                    background: rgba(255,255,255,0.08);
                    border: 1px solid rgba(255,255,255,0.15);
                    border-radius: 22px;
                    padding: 11px 18px;
                    color: {p.text_inverse};
                    font-size: 10pt;
                }}
                """
            )
        composer_layout.addWidget(self._input, stretch=1)

        send_button = QPushButton()
        send_button.setObjectName("sendButton")
        send_button.setIcon(QIcon(icon_pixmap("send.svg", 20)))
        send_button.setIconSize(QSize(18, 18))
        send_button.setToolTip("Send")
        send_button.clicked.connect(self._submit)
        send_button.setCursor(Qt.CursorShape.PointingHandCursor)
        send_button.setStyleSheet(
            f"""
            QPushButton#sendButton {{
                background: {p.blue_600};
                border: none;
                border-radius: 22px;
                min-width: 44px; max-width: 44px;
                min-height: 44px; max-height: 44px;
            }}
            QPushButton#sendButton:hover {{
                background: {p.blue_500};
            }}
            """
        )
        composer_layout.addWidget(send_button)

        chip_style = (
            f"""
            QPushButton#promptChip {{
                background: rgba(255,255,255,0.08);
                color: {p.text_inverse};
                border: 1px solid rgba(255,255,255,0.22);
                border-radius: 14px;
                padding: 6px 14px;
                font-size: 9pt;
                font-weight: 600;
            }}
            QPushButton#promptChip:hover {{
                background: rgba(30, 91, 255, 0.18);
            }}
            """
            if dark
            else f"""
            QPushButton#promptChip {{
                background: {p.surface_muted};
                color: {p.blue_600};
                border: 1px solid {p.border};
                border-radius: 14px;
                padding: 6px 14px;
                font-weight: 600;
            }}
            """
        )
        self.setStyleSheet(self._panel_stylesheet(chip_style))

        if dark:
            composer.setStyleSheet(
                "background: rgba(0,0,0,0.18); border-top: 1px solid rgba(255,255,255,0.08);"
            )
        else:
            composer.setStyleSheet(f"background: {p.surface}; border-top: 1px solid {p.border};")
        root.addWidget(composer)

    def _show_welcome(self) -> None:
        p = self._palette
        dark = self._variant == "dark"
        card = QFrame()
        card.setObjectName("welcomeCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        logo_row = QHBoxLayout()
        logo_row.setSpacing(8)
        logo_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        co = QLabel()
        co.setPixmap(load_brand_logo_pixmap(48))
        logo_row.addWidget(co)
        layout.addLayout(logo_row)

        title = QLabel("Welcome to SmartInstall AI")
        self._welcome_title = title
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(self._welcome_title_style())

        sub = QLabel(
            "Ask questions about installation errors, diagnostics, and fixes. "
            "I can list installers, run monitored installs, and explain troubleshooting results."
        )
        self._welcome_sub = sub
        sub.setWordWrap(True)
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setStyleSheet(self._welcome_sub_style())

        layout.addWidget(title)
        layout.addWidget(sub)

        prompts_label = QLabel("Suggested prompts")
        self._welcome_prompts_label = prompts_label
        prompts_label.setStyleSheet(self._welcome_prompts_label_style())
        layout.addWidget(prompts_label)

        for prompt in _SUGGESTED_PROMPTS:
            btn = QPushButton(prompt)
            btn.setObjectName("suggestedPrompt")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked=False, t=prompt: self._use_prompt(t))
            btn.setStyleSheet(self._suggested_prompt_style_for(p, dark=dark))
            layout.addWidget(btn)

        self._welcome_card = card
        self._apply_welcome_card_style()
        self._history_layout.addWidget(card)

    def _hide_welcome(self) -> None:
        if self._welcome_visible and hasattr(self, "_welcome_card"):
            self._welcome_card.hide()
            self._welcome_visible = False

    def prefill_input(self, text: str) -> None:
        """Put text in the composer without sending — user can edit and press Enter."""
        self._hide_welcome()
        self._input.setText(text)
        self._input.setFocus()

    def _use_prompt(self, text: str) -> None:
        self.prefill_input(text)
        self.prompt_chosen.emit(text)

    def _quick_action(self, action: str) -> None:
        mapping = {"Install": "install", "List": "list", "Help": "help"}
        self._use_prompt(mapping.get(action, action))

    def append_message(self, message: ChatMessage) -> None:
        self._hide_welcome()
        self.hide_typing()
        row = self._create_message_row(message)
        self._history_layout.addWidget(row)
        self._scroll_to_bottom()

    def show_typing(self) -> None:
        self._hide_welcome()
        self.hide_typing()
        p = self._palette
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 40, 0)
        layout.addWidget(AvatarLabel("assistant.svg", size=32), alignment=Qt.AlignmentFlag.AlignTop)
        col = QVBoxLayout()
        name = QLabel("SmartInstall AI")
        name.setStyleSheet(self._name_style(accent=True))
        self._typing_label = QLabel("Thinking")
        self._typing_label.setStyleSheet(
            f"color: {p.text_muted_inverse}; font-style: italic; font-size: 9.5pt; "
            "background: rgba(255,255,255,0.06); border-radius: 12px; padding: 10px 14px;"
        )
        col.addWidget(name)
        col.addWidget(self._typing_label)
        layout.addLayout(col, stretch=1)
        self._typing_row = row
        self._history_layout.addWidget(row)
        self._typing_dots = 0
        self._typing_timer = QTimer(self)
        self._typing_timer.setInterval(400)
        self._typing_timer.timeout.connect(self._animate_typing)
        self._typing_timer.start()
        self._scroll_to_bottom()

    def hide_typing(self) -> None:
        if self._typing_timer is not None:
            self._typing_timer.stop()
            self._typing_timer = None
        if self._typing_row is not None:
            self._typing_row.deleteLater()
            self._typing_row = None

    def _animate_typing(self) -> None:
        self._typing_dots = (self._typing_dots + 1) % 4
        if hasattr(self, "_typing_label"):
            self._typing_label.setText("Thinking" + "." * self._typing_dots)

    def set_input_enabled(self, enabled: bool) -> None:
        self._input.setEnabled(enabled)
        if not enabled:
            self.show_typing()
        else:
            self.hide_typing()

    def set_variant_dark(self) -> None:
        self._apply_variant("dark")

    def set_variant_light(self) -> None:
        self._apply_variant("light")

    def _welcome_title_style(self) -> str:
        p = self._palette
        dark = self._variant == "dark"
        color = p.text_inverse if dark else p.text_primary
        return f"color: {color}; font-size: 13pt; font-weight: 700;"

    def _welcome_sub_style(self) -> str:
        p = self._palette
        dark = self._variant == "dark"
        color = p.text_muted_inverse if dark else p.text_secondary
        return f"color: {color}; font-size: 9.5pt;"

    def _welcome_prompts_label_style(self) -> str:
        p = self._palette
        dark = self._variant == "dark"
        color = p.blue_500 if dark else p.blue_600
        return f"color: {color}; font-weight: 600; font-size: 9pt;"

    def _apply_welcome_card_style(self) -> None:
        if not hasattr(self, "_welcome_card"):
            return
        p = self._palette
        dark = self._variant == "dark"
        self._welcome_card.setStyleSheet(
            "background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); border-radius: 16px;"
            if dark
            else f"background: {p.surface_muted}; border: 1px solid {p.border}; border-radius: 16px;"
        )

    def _refresh_welcome_theme(self) -> None:
        if self._welcome_title is not None:
            self._welcome_title.setStyleSheet(self._welcome_title_style())
        if self._welcome_sub is not None:
            self._welcome_sub.setStyleSheet(self._welcome_sub_style())
        if self._welcome_prompts_label is not None:
            self._welcome_prompts_label.setStyleSheet(self._welcome_prompts_label_style())
        self._apply_welcome_card_style()
        if hasattr(self, "_welcome_card"):
            for btn in self._welcome_card.findChildren(QPushButton):
                if btn.objectName() == "suggestedPrompt":
                    btn.setStyleSheet(self._suggested_prompt_style())

    @staticmethod
    def _suggested_prompt_style_for(p: CCTechPalette, *, dark: bool) -> str:
        return f"""
            QPushButton#suggestedPrompt {{
                background: rgba(30, 91, 255, 0.15);
                color: {p.text_inverse if dark else p.navy_800};
                border: 1px solid rgba(34, 211, 238, 0.25);
                border-radius: 10px;
                padding: 10px 12px;
                text-align: left;
                font-size: 9.5pt;
            }}
            QPushButton#suggestedPrompt:hover {{
                background: rgba(34, 211, 238, 0.2);
            }}
            """

    def _suggested_prompt_style(self) -> str:
        return self._suggested_prompt_style_for(self._palette, dark=self._variant == "dark")

    def _panel_stylesheet(self, chip_style: str) -> str:
        p = self._palette
        dark = self._variant == "dark"
        text_color = p.text_inverse if dark else p.text_primary
        return (
            f"QWidget#chatPanel {{ color: {text_color}; background: transparent; }}\n"
            f"{chip_style}"
        )

    def _apply_variant(self, variant: str) -> None:
        if self._variant == variant:
            return
        self._variant = variant
        p = self._palette
        dark = variant == "dark"
        if dark:
            self._input.setStyleSheet(
                f"""
                QLineEdit {{
                    background: rgba(255,255,255,0.08);
                    border: 1px solid rgba(255,255,255,0.15);
                    border-radius: 22px;
                    padding: 11px 18px;
                    color: {p.text_inverse};
                    font-size: 10pt;
                }}
                """
            )
            chip_style = f"""
            QPushButton#promptChip {{
                background: rgba(255,255,255,0.08);
                color: {p.text_inverse};
                border: 1px solid rgba(255,255,255,0.22);
                border-radius: 14px;
                padding: 6px 14px;
                font-size: 9pt;
                font-weight: 600;
            }}
            QPushButton#promptChip:hover {{
                background: rgba(30, 91, 255, 0.18);
            }}
            """
            if self._composer is not None:
                self._composer.setStyleSheet(
                    "background: rgba(0,0,0,0.18); border-top: 1px solid rgba(255,255,255,0.08);"
                )
        else:
            self._input.setStyleSheet(
                f"""
                QLineEdit {{
                    background: {p.surface};
                    border: 1.5px solid {p.border};
                    border-radius: 22px;
                    padding: 11px 18px;
                    color: {p.text_primary};
                    font-size: 10pt;
                }}
                QLineEdit:focus {{
                    border: 2px solid {p.border_focus};
                }}
                """
            )
            chip_style = f"""
            QPushButton#promptChip {{
                background: {p.surface_muted};
                color: {p.blue_600};
                border: 1px solid {p.border};
                border-radius: 14px;
                padding: 6px 14px;
                font-weight: 600;
            }}
            QPushButton#promptChip:hover {{
                background: {p.surface_hover};
            }}
            """
            if self._composer is not None:
                self._composer.setStyleSheet(
                    f"background: {p.surface}; border-top: 1px solid {p.border};"
                )
        self.setStyleSheet(self._panel_stylesheet(chip_style))
        self._refresh_welcome_theme()

    def _scroll_to_bottom(self) -> None:
        self._scroll_area.verticalScrollBar().setValue(
            self._scroll_area.verticalScrollBar().maximum()
        )

    def _submit(self) -> None:
        text = self._input.text().strip()
        if not text:
            return
        self._input.clear()
        self._hide_welcome()
        self.message_submitted.emit(text)

    def _format_time(self, message: ChatMessage) -> str:
        ts = message.timestamp or datetime.now()
        return ts.strftime("%H:%M")

    def _create_message_row(self, message: ChatMessage) -> QWidget:
        if message.role is ChatRole.SYSTEM:
            return self._create_system_row(message)
        if message.role is ChatRole.USER:
            return self._create_user_row(message)
        return self._create_assistant_row(message)

    def _meta_row(self, name: str, *, align_right: bool, accent: bool) -> QHBoxLayout:
        meta = QHBoxLayout()
        name_lbl = QLabel(name)
        name_lbl.setStyleSheet(self._name_style(accent=accent))
        time_lbl = QLabel(self._format_time(ChatMessage(role=ChatRole.USER, content="")))
        time_lbl.setStyleSheet(self._time_style())
        if align_right:
            meta.addStretch(1)
            meta.addWidget(name_lbl)
            meta.addWidget(time_lbl)
        else:
            meta.addWidget(name_lbl)
            meta.addWidget(time_lbl)
            meta.addStretch(1)
        return meta

    def _create_assistant_row(self, message: ChatMessage) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 28, 0)
        layout.setSpacing(10)
        layout.addWidget(AvatarLabel("assistant.svg", size=38), alignment=Qt.AlignmentFlag.AlignTop)
        column = QVBoxLayout()
        column.setSpacing(4)
        meta = QHBoxLayout()
        name = QLabel("SmartInstall AI")
        name.setStyleSheet(self._name_style(accent=True))
        t = QLabel(self._format_time(message))
        t.setStyleSheet(self._time_style())
        meta.addWidget(name)
        meta.addWidget(t)
        meta.addStretch(1)
        column.addLayout(meta)
        column.addWidget(self._create_bubble(message, "assistant"))
        layout.addLayout(column, stretch=1)
        return row

    def _create_user_row(self, message: ChatMessage) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(28, 0, 0, 0)
        layout.setSpacing(10)
        column = QVBoxLayout()
        column.setSpacing(4)
        meta = QHBoxLayout()
        meta.addStretch(1)
        t = QLabel(self._format_time(message))
        t.setStyleSheet(self._time_style())
        meta.addWidget(t)
        name = QLabel("You")
        name.setStyleSheet(self._name_style(accent=False))
        meta.addWidget(name)
        column.addLayout(meta)
        column.addWidget(self._create_bubble(message, "user"))
        layout.addLayout(column, stretch=1)
        layout.addWidget(AvatarLabel("user.svg", size=38), alignment=Qt.AlignmentFlag.AlignTop)
        return row

    def _create_system_row(self, message: ChatMessage) -> QWidget:
        row = QWidget()
        outer = QHBoxLayout(row)
        outer.addStretch(1)
        pill = QFrame()
        pill_layout = QHBoxLayout(pill)
        pill_layout.setContentsMargins(10, 5, 12, 5)
        pill_layout.addWidget(AvatarLabel("system.svg", size=20))
        label = QLabel(message.content)
        label.setWordWrap(True)
        label.setStyleSheet(self._muted_text_style())
        pill_layout.addWidget(label)
        pill.setStyleSheet(self._system_pill_style())
        pill.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
        outer.addWidget(pill)
        outer.addStretch(1)
        return row

    def _create_bubble(self, message: ChatMessage, role: str) -> QFrame:
        p = self._palette
        dark = self._variant == "dark"
        bubble = QFrame()
        bubble.setObjectName(f"{role}Bubble")
        layout = QVBoxLayout(bubble)
        layout.setContentsMargins(14, 11, 14, 11)
        layout.setSpacing(6)

        if message.title:
            title = QLabel(message.title)
            title.setWordWrap(True)
            title.setStyleSheet(
                f"font-weight: 600; font-size: 10pt; color: {p.text_inverse if dark else p.text_primary};"
            )
            layout.addWidget(title)

        if message.content.strip():
            body = QLabel(message.content)
            body.setWordWrap(True)
            body.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            body.setStyleSheet(
                f"color: {p.text_inverse if dark else p.text_primary}; font-size: 9.5pt; line-height: 1.45;"
            )
            layout.addWidget(body)

        for section in message.sections:
            layout.addWidget(self._create_section_card(section))

        if role == "assistant":
            bubble.setStyleSheet(
                "QFrame#assistantBubble { background: rgba(255,255,255,0.1); "
                "border: 1px solid rgba(255,255,255,0.12); border-radius: 14px; "
                "border-top-left-radius: 4px; }"
                if dark
                else f"QFrame#assistantBubble {{ background: {p.surface}; "
                f"border: 1px solid {p.border}; border-radius: 14px; border-top-left-radius: 4px; }}"
            )
        elif dark:
            bubble.setStyleSheet(
                "QFrame#userBubble { background: rgba(30, 91, 255, 0.38); "
                "border: 1px solid rgba(34, 211, 238, 0.35); border-radius: 14px; "
                "border-top-right-radius: 4px; }"
            )
        else:
            bubble.setStyleSheet(
                f"QFrame#userBubble {{ background: #e8f4fd; border: 1px solid {p.blue_600}; "
                "border-radius: 14px; border-top-right-radius: 4px; }"
            )
        return bubble

    def _create_section_card(self, section: ChatSection) -> QFrame:
        p = self._palette
        dark = self._variant == "dark"
        card = QFrame()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(8, 6, 8, 6)
        heading = QLabel(section.heading)
        heading.setStyleSheet(f"font-weight: 600; color: {p.blue_500}; font-size: 9pt;")
        body = QLabel(section.body)
        body.setWordWrap(True)
        body.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        body.setStyleSheet(
            f"color: {p.text_inverse if dark else p.text_secondary}; font-size: 9pt;"
        )
        layout.addWidget(heading)
        layout.addWidget(body)
        card.setStyleSheet(
            "background: rgba(34, 211, 238, 0.08); border-left: 2px solid #22d3ee; border-radius: 6px;"
            if dark
            else f"background: {p.surface_muted}; border-left: 3px solid {p.blue_600}; border-radius: 6px;"
        )
        return card

    def _name_style(self, *, accent: bool) -> str:
        p = self._palette
        if self._variant == "dark":
            color = p.blue_500 if accent else p.text_muted_inverse
        else:
            color = p.blue_600 if accent else p.text_secondary
        return f"color: {color}; font-weight: 600; font-size: 9pt;"

    def _time_style(self) -> str:
        p = self._palette
        color = p.text_muted_inverse if self._variant == "dark" else p.text_secondary
        return f"color: {color}; font-size: 8pt; padding: 0 6px;"

    def _muted_text_style(self) -> str:
        p = self._palette
        color = p.text_muted_inverse if self._variant == "dark" else p.text_secondary
        return f"color: {color}; font-size: 9pt;"

    def _system_pill_style(self) -> str:
        if self._variant == "dark":
            return (
                "background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.1); "
                "border-radius: 14px;"
            )
        return (
            f"background: {self._palette.surface_muted}; "
            f"border: 1px solid {self._palette.border}; border-radius: 14px;"
        )
