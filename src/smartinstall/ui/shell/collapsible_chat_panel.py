"""Enterprise AI assistant — docked, compact, fullscreen, and minimized modes."""

from __future__ import annotations

from enum import Enum

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from smartinstall.ui.resources.brand_assets import load_brand_logo_pixmap
from smartinstall.ui.theme.cctech_theme import CCTechPalette
from smartinstall.ui.widgets.avatar_label import AvatarLabel, icon_pixmap
from smartinstall.ui.widgets.chat_panel import ChatPanel

_ANIM_MS = 300
_WIDTH_DOCKED = 420
_WIDTH_COMPACT = 300


class ChatPanelMode(str, Enum):
    MINIMIZED = "minimized"
    COMPACT = "compact"
    DOCKED = "docked"
    FULLSCREEN = "fullscreen"


class CollapsibleChatPanel(QWidget):
    """Right-side AI workspace with enterprise display modes."""

    collapsed_changed = Signal(bool)
    prompt_requested = Signal(str)

    def __init__(
        self,
        palette: CCTechPalette,
        chat: ChatPanel,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._palette = palette
        self._chat = chat
        self._mode = ChatPanelMode.DOCKED
        self._overlay_host: QWidget | None = None
        self._fullscreen_backdrop: QFrame | None = None
        self._width_anim: QPropertyAnimation | None = None
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        self.setFixedWidth(_WIDTH_DOCKED)
        self._build_ui()
        self._build_fab()

    def _build_ui(self) -> None:
        p = self._palette
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self._panel = QFrame()
        self._panel.setObjectName("collapsibleChatPanel")
        layout = QVBoxLayout(self._panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QFrame()
        header.setObjectName("chatPanelHeader")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(16, 14, 10, 12)
        hl.setSpacing(8)

        logo = QLabel()
        logo.setPixmap(load_brand_logo_pixmap(36))
        logo.setFixedSize(36, 36)
        hl.addWidget(logo, alignment=Qt.AlignmentFlag.AlignTop)

        titles = QVBoxLayout()
        titles.setSpacing(0)
        t1 = QLabel("SmartInstall AI")
        t1.setStyleSheet(f"color: {p.text_inverse}; font-size: 12pt; font-weight: 700;")
        t2 = QLabel("CCTech Enterprise Assistant")
        t2.setStyleSheet(f"color: {p.text_muted_inverse}; font-size: 8.5pt;")
        titles.addWidget(t1)
        titles.addWidget(t2)
        hl.addLayout(titles, stretch=1)

        for tip, slot in (
            ("Compact", self.set_compact),
            ("Expand", self.set_docked),
            ("Full", self.set_fullscreen),
            ("−", self.collapse),
        ):
            btn = QToolButton()
            btn.setText(tip)
            btn.setToolTip(
                {"Compact": "Compact mode", "Expand": "Docked mode", "Full": "Fullscreen", "−": "Minimize"}[tip]
            )
            btn.setFixedSize(34, 30)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(slot)
            btn.setStyleSheet(self._chrome_btn_style(p))
            hl.addWidget(btn, alignment=Qt.AlignmentFlag.AlignTop)

        layout.addWidget(header)

        self._context_label = QLabel("Session: Ready")
        self._context_label.setWordWrap(True)
        self._context_label.setStyleSheet(
            f"""
            color: {p.cyan_300};
            background: rgba(34, 211, 238, 0.1);
            border: 1px solid rgba(34, 211, 238, 0.22);
            border-radius: 10px;
            padding: 8px 14px;
            margin: 0 12px 6px 12px;
            font-size: 9pt;
            """
        )
        layout.addWidget(self._context_label)

        self._chat.prompt_chosen.connect(self.prompt_requested.emit)
        self._chat.setStyleSheet("background: transparent;")
        layout.addWidget(self._chat, stretch=1)

        footer = QLabel("CCTech • Private local AI")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet(f"color: {p.text_muted_inverse}; font-size: 8pt; padding: 8px;")
        layout.addWidget(footer)

        self._panel.setStyleSheet(
            f"""
            QFrame#collapsibleChatPanel {{
                background: {p.assistant_panel_bg};
                border-left: 1px solid rgba(255,255,255,0.08);
            }}
            QFrame#chatPanelHeader {{
                background: rgba(0,0,0,0.14);
                border-bottom: 1px solid rgba(255,255,255,0.06);
            }}
            """
        )
        outer.addWidget(self._panel)

    @staticmethod
    def _chrome_btn_style(p: CCTechPalette) -> str:
        return f"""
            QToolButton {{
                background: rgba(255,255,255,0.08);
                color: {p.text_inverse};
                border: 1px solid rgba(255,255,255,0.12);
                border-radius: 7px;
                font-size: 9pt;
                font-weight: 600;
            }}
            QToolButton:hover {{ background: rgba(255,255,255,0.14); border-color: {p.blue_500}; }}
            """

    def _build_fab(self) -> None:
        p = self._palette
        self._fab = QPushButton()
        self._fab.setObjectName("chatFab")
        self._fab.setFixedSize(60, 60)
        from smartinstall.ui.resources.chat_icon import chatbot_icon

        self._fab.setIcon(chatbot_icon(36))
        self._fab.setIconSize(self._fab.size() * 0.55)
        self._fab.setToolTip("Open AI Assistant")
        self._fab.setCursor(Qt.CursorShape.PointingHandCursor)
        self._fab.clicked.connect(self.set_docked)
        self._fab.hide()
        self._fab.setStyleSheet("")

    def attach_overlay_host(self, host: QWidget) -> None:
        self._overlay_host = host
        self._fab.setParent(host)

    def reposition_fab(self) -> None:
        host = self._overlay_host
        if host is None or self._mode is not ChatPanelMode.MINIMIZED:
            self._fab.hide()
            return
        margin = 28
        x = host.width() - self._fab.width() - margin
        y = host.height() - self._fab.height() - margin
        self._fab.move(max(margin, x), max(margin, y))
        self._fab.raise_()
        self._fab.show()

    def collapse(self) -> None:
        self._exit_fullscreen()
        self._animate_width(0, on_finished=self._on_minimized)

    def expand(self) -> None:
        self.set_docked()

    def set_compact(self) -> None:
        self._exit_fullscreen()
        self._mode = ChatPanelMode.COMPACT
        self._fab.hide()
        self._panel.show()
        self._animate_width(_WIDTH_COMPACT, on_finished=lambda: self._finish_mode(ChatPanelMode.COMPACT))

    def set_docked(self) -> None:
        self._exit_fullscreen()
        self._mode = ChatPanelMode.DOCKED
        self._fab.hide()
        self._panel.show()
        if self.parentWidget() is not None:
            self.show()
        self._animate_width(_WIDTH_DOCKED, on_finished=lambda: self._finish_mode(ChatPanelMode.DOCKED))

    def set_fullscreen(self) -> None:
        host = self._overlay_host
        if host is None:
            return
        self._mode = ChatPanelMode.FULLSCREEN
        self.setFixedWidth(0)
        self.hide()
        if self._fullscreen_backdrop is None:
            self._fullscreen_backdrop = QFrame(host)
            self._fullscreen_backdrop.setObjectName("chatFullscreenBackdrop")
            self._fullscreen_backdrop.setStyleSheet("background: rgba(5, 13, 26, 0.55);")
            fl = QVBoxLayout(self._fullscreen_backdrop)
            fl.setContentsMargins(48, 36, 48, 36)
            self._panel.setParent(self._fullscreen_backdrop)
            fl.addWidget(self._panel)
        self._fullscreen_backdrop.setGeometry(host.rect())
        self._panel.show()
        self._fullscreen_backdrop.show()
        self._fullscreen_backdrop.raise_()
        self._fab.hide()
        self.collapsed_changed.emit(False)

    def _exit_fullscreen(self) -> None:
        if self._fullscreen_backdrop is not None:
            self._fullscreen_backdrop.hide()
        lay = self.layout()
        if self._panel.parent() is not self:
            self._panel.setParent(self)
        if lay is not None and lay.indexOf(self._panel) < 0:
            lay.addWidget(self._panel)
        self.show()

    def _on_minimized(self) -> None:
        self._mode = ChatPanelMode.MINIMIZED
        self._panel.hide()
        self.setFixedWidth(0)
        self.reposition_fab()
        self.collapsed_changed.emit(True)

    def _finish_mode(self, mode: ChatPanelMode) -> None:
        self._mode = mode
        self.collapsed_changed.emit(False)

    def _animate_width(self, target: int, *, on_finished) -> None:
        if self._width_anim is not None and self._width_anim.state() == QPropertyAnimation.State.Running:
            self._width_anim.stop()
        self.show()
        self._width_anim = QPropertyAnimation(self, b"maximumWidth", self)
        self._width_anim.setDuration(_ANIM_MS)
        self._width_anim.setStartValue(self.width())
        self._width_anim.setEndValue(target)
        self._width_anim.setEasingCurve(QEasingCurve.Type.InOutCubic)

        def _sync(v: float) -> None:
            self.setFixedWidth(max(0, int(v)))

        self._width_anim.valueChanged.connect(_sync)
        self._width_anim.finished.connect(on_finished)
        self._width_anim.start()

    @property
    def chat(self) -> ChatPanel:
        return self._chat

    @property
    def is_expanded(self) -> bool:
        return self._mode is not ChatPanelMode.MINIMIZED

    def set_context(self, text: str) -> None:
        self._context_label.setText(f"Session: {text}")
