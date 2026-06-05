"""Light-theme floating chatbot — bottom-right launcher."""

from __future__ import annotations

from enum import Enum

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from PySide6.QtWidgets import QApplication

from smartinstall.ui.resources.brand_assets import load_brand_logo_pixmap
from smartinstall.ui.resources.chat_icon import chatbot_icon
from smartinstall.ui.theme.cctech_theme import CCTechPalette
from smartinstall.ui.widgets.chat_panel import ChatPanel

_COMPACT_W = 400
_COMPACT_H = 520
_MAX_W = 660
_MAX_H = 700
_FAB_SIZE = 56
_MARGIN = 20


def _available_screen_size() -> tuple[int, int]:
    screen = QApplication.primaryScreen()
    if screen is None:
        return 1920, 1080
    g = screen.availableGeometry()
    return g.width(), g.height()


class FloatingChatState(str, Enum):
    CLOSED = "closed"
    COMPACT = "compact"
    MAXIMIZED = "maximized"


class FloatingChatWidget(QWidget):
    """Overlay chatbot anchored to the bottom-right."""

    visibility_changed = Signal(bool)
    prompt_requested = Signal(str)

    def __init__(self, palette: CCTechPalette, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._palette = palette
        self._state = FloatingChatState.CLOSED
        self._chat: ChatPanel | None = None
        self._chat_slot: QVBoxLayout | None = None
        self._maximize_btn: QToolButton | None = None
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("background: transparent;")
        self._build_window()
        self._build_fab()
        self._fab.show()
        self._fab.raise_()

    def _build_window(self) -> None:
        p = self._palette
        self._window = QFrame(self)
        self._window.setObjectName("floatingChatWindow")
        self._window.hide()

        outer = QVBoxLayout(self._window)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        header = QFrame()
        header.setObjectName("floatingChatHeader")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(16, 14, 12, 12)
        hl.setSpacing(10)

        logo = QLabel()
        logo.setPixmap(load_brand_logo_pixmap(28))
        logo.setFixedSize(28, 28)
        logo.setStyleSheet("background: transparent;")
        hl.addWidget(logo, alignment=Qt.AlignmentFlag.AlignVCenter)

        titles = QVBoxLayout()
        titles.setSpacing(0)
        t1 = QLabel("Smart Installer AI")
        t1.setStyleSheet(
            f"color: {p.text_primary}; font-size: 11pt; font-weight: 600; background: transparent;"
        )
        t2 = QLabel("Ask anything about installs & errors")
        t2.setStyleSheet(
            f"color: {p.text_muted}; font-size: 8.5pt; background: transparent;"
        )
        titles.addWidget(t1)
        titles.addWidget(t2)
        hl.addLayout(titles, stretch=1)

        for symbol, tip, slot in (
            ("−", "Minimize", self.minimize),
            ("□", "Maximize", self.toggle_maximize),
            ("×", "Close", self.close_chat),
        ):
            btn = QToolButton()
            btn.setText(symbol)
            btn.setToolTip(tip)
            btn.setFixedSize(30, 28)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(slot)
            btn.setStyleSheet(self._chrome_btn_style(p))
            if tip == "Maximize":
                self._maximize_btn = btn
            hl.addWidget(btn, alignment=Qt.AlignmentFlag.AlignVCenter)

        outer.addWidget(header)

        self._context_label = QLabel("Ready for your questions")
        self._context_label.setWordWrap(True)
        self._context_label.setStyleSheet(
            f"""
            color: {p.text_secondary};
            background: {p.surface_muted};
            border: none;
            border-bottom: 1px solid {p.border};
            padding: 8px 16px;
            font-size: 9pt;
            """
        )
        outer.addWidget(self._context_label)

        self._chat_host = QWidget()
        self._chat_host.setStyleSheet(f"background: {p.surface};")
        self._chat_slot = QVBoxLayout(self._chat_host)
        self._chat_slot.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self._chat_host, stretch=1)

        self._window.setStyleSheet(
            f"""
            QFrame#floatingChatWindow {{
                background: {p.surface};
                border: 1px solid {p.border};
                border-radius: 14px;
            }}
            QFrame#floatingChatHeader {{
                background: {p.surface};
                border-bottom: 1px solid {p.border};
                border-top-left-radius: 14px;
                border-top-right-radius: 14px;
            }}
            """
        )

    def _build_fab(self) -> None:
        p = self._palette
        self._fab = QPushButton(self)
        self._fab.setObjectName("chatFab")
        self._fab.setFixedSize(_FAB_SIZE, _FAB_SIZE)
        self._fab.setIcon(chatbot_icon(34))
        self._fab.setIconSize(QSize(34, 34))
        self._fab.setToolTip("Open AI Assistant")
        self._fab.setCursor(Qt.CursorShape.PointingHandCursor)
        self._fab.clicked.connect(self.open_compact)
        self._fab.setStyleSheet(
            f"""
            QPushButton#chatFab {{
                background: {p.blue_600};
                border: 2px solid {p.blue_500};
                border-radius: 28px;
            }}
            QPushButton#chatFab:hover {{
                background: {p.blue_500};
                border-color: #5c8cff;
            }}
            QPushButton#chatFab:pressed {{
                background: #1848cc;
            }}
            """
        )

    @staticmethod
    def _chrome_btn_style(p: CCTechPalette) -> str:
        return f"""
            QToolButton {{
                background: {p.surface_muted};
                color: {p.text_primary};
                border: 1px solid {p.border};
                border-radius: 6px;
                font-size: 11pt;
                font-weight: 600;
            }}
            QToolButton:hover {{
                background: {p.surface_hover};
                border-color: {p.blue_600};
                color: {p.blue_600};
            }}
            """

    def attach_chat(self, chat: ChatPanel) -> None:
        if self._chat is chat:
            chat.show()
            return
        self.detach_chat()
        self._chat = chat
        chat.setParent(self._chat_host)
        chat.set_variant_light()
        chat.setStyleSheet(f"background: {self._palette.surface};")
        if self._chat_slot is not None:
            self._chat_slot.addWidget(chat, stretch=1)
        chat.show()

    def detach_chat(self) -> ChatPanel | None:
        chat = self._chat
        if chat is None:
            return None
        if self._chat_slot is not None:
            self._chat_slot.removeWidget(chat)
        chat.setParent(None)
        chat.hide()
        self._chat = None
        return chat

    @property
    def chat(self) -> ChatPanel | None:
        return self._chat

    @property
    def is_open(self) -> bool:
        return self._state is not FloatingChatState.CLOSED

    def open_compact(self) -> None:
        self._state = FloatingChatState.COMPACT
        sw, sh = _available_screen_size()
        w = min(_COMPACT_W, max(280, sw - _MARGIN * 4))
        h = min(_COMPACT_H, max(360, sh - _MARGIN * 8))
        self._resize_window(w, h)
        self._reposition()
        self._window.setWindowOpacity(1.0)
        self.visibility_changed.emit(True)

    def toggle_maximize(self) -> None:
        if self._state is FloatingChatState.MAXIMIZED:
            self.restore()
        else:
            self.maximize()

    def maximize(self) -> None:
        if self._state is FloatingChatState.CLOSED:
            self.open_compact()
        self._state = FloatingChatState.MAXIMIZED
        sw, sh = _available_screen_size()
        w = min(_MAX_W, max(340, sw - _MARGIN * 4))
        h = min(_MAX_H, max(420, sh - _MARGIN * 8))
        self._resize_window(w, h)
        self._reposition()
        if self._maximize_btn is not None:
            self._maximize_btn.setToolTip("Restore")
            self._maximize_btn.setText("❐")

    def restore(self) -> None:
        self._state = FloatingChatState.COMPACT
        sw, sh = _available_screen_size()
        w = min(_COMPACT_W, max(280, sw - _MARGIN * 4))
        h = min(_COMPACT_H, max(360, sh - _MARGIN * 8))
        self._resize_window(w, h)
        self._reposition()
        if self._maximize_btn is not None:
            self._maximize_btn.setToolTip("Maximize")
            self._maximize_btn.setText("□")

    def minimize(self) -> None:
        self.close_chat()

    def close_chat(self) -> None:
        self._state = FloatingChatState.CLOSED
        self._reposition()
        self.visibility_changed.emit(False)

    def set_context(self, text: str) -> None:
        self._context_label.setText(text)

    def reposition(self) -> None:
        self._reposition()

    def _reposition(self) -> None:
        parent = self.parentWidget()
        if parent is None:
            return

        pw = max(parent.width(), 1)
        ph = max(parent.height(), 1)

        if self._state is FloatingChatState.CLOSED:
            fab_x = max(0, pw - _FAB_SIZE - _MARGIN)
            fab_y = max(0, ph - _FAB_SIZE - _MARGIN)
            self.setGeometry(fab_x, fab_y, _FAB_SIZE, _FAB_SIZE)
            self._fab.setGeometry(0, 0, _FAB_SIZE, _FAB_SIZE)
            self._fab.show()
            self._fab.raise_()
            self._window.hide()
            return

        w = self._window.width()
        h = self._window.height()
        # Clamp so the panel never extends beyond parent bounds
        w = min(w, pw - _MARGIN * 2)
        h = min(h, ph - _MARGIN * 2)
        wx = max(0, pw - w - _MARGIN)
        wy = max(0, ph - h - _MARGIN)
        self.setGeometry(wx, wy, w, h)
        self._window.setGeometry(0, 0, w, h)
        self._window.show()
        self._window.raise_()
        self._fab.hide()

    def _resize_window(self, width: int, height: int) -> None:
        self._window.setFixedSize(width, height)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._reposition()
