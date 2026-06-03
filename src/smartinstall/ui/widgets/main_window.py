"""Main desktop window — Windows 11 Fluent layout."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from smartinstall.ui.controllers.desktop_controller import DesktopController
from smartinstall.ui.models.chat_message import ChatMessage, ChatRole
from smartinstall.ui.theme.windows_theme import WindowsPalette
from smartinstall.ui.resources.brand_assets import load_brand_logo_pixmap
from smartinstall.ui.widgets.avatar_label import icon_pixmap
from smartinstall.ui.widgets.chat_panel import ChatPanel


class MainWindow(QMainWindow):
    """Primary SmartInstall AI desktop shell."""

    def __init__(self, controller: DesktopController, palette: WindowsPalette) -> None:
        super().__init__()
        self._controller = controller
        self._palette = palette
        self._chat = ChatPanel(palette)
        self._status_label: QLabel
        self._build_ui()
        self._wire_events()
        controller.show_welcome()

    def _build_ui(self) -> None:
        self.setWindowTitle("SmartInstall AI")
        self.resize(1100, 760)
        self.setMinimumSize(900, 600)
        self.setWindowIcon(QIcon(load_brand_logo_pixmap(32)))

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_header())

        body = QHBoxLayout()
        body.setSpacing(0)
        body.setContentsMargins(0, 0, 0, 0)
        body.addWidget(self._build_sidebar())
        body.addWidget(self._build_chat_area(), stretch=1)
        root.addLayout(body, stretch=1)

        self._build_menu()

    def _build_header(self) -> QFrame:
        header = QFrame()
        header.setObjectName("appHeader")
        header.setFixedHeight(64)
        layout = QHBoxLayout(header)
        layout.setContentsMargins(20, 10, 20, 10)
        layout.setSpacing(14)

        logo = QLabel()
        logo.setPixmap(load_brand_logo_pixmap(40))
        logo.setFixedSize(40, 40)
        layout.addWidget(logo)

        titles = QVBoxLayout()
        titles.setSpacing(0)
        title = QLabel("SmartInstall AI")
        title.setObjectName("appTitle")
        subtitle = QLabel("Intelligent installation assistant for Windows")
        subtitle.setObjectName("appSubtitle")
        titles.addWidget(title)
        titles.addWidget(subtitle)
        layout.addLayout(titles)
        layout.addStretch(1)

        self._status_label = QLabel("Ready")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._status_label.setStyleSheet(
            f"color: {self._palette.text_secondary}; font-size: 9pt; padding: 6px 12px;"
            f"background: {self._palette.accent_light}; border-radius: 12px;"
        )
        layout.addWidget(self._status_label)
        return header

    def _build_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(220)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(16, 20, 16, 20)
        layout.setSpacing(8)

        section = QLabel("ACTIONS")
        section.setObjectName("sidebarTitle")
        layout.addWidget(section)

        browse = QPushButton("  Browse installer…")
        browse.setObjectName("primaryButton")
        browse.setCursor(Qt.CursorShape.PointingHandCursor)
        browse.clicked.connect(lambda: self._controller.browse_and_install(self))
        layout.addWidget(browse)

        list_btn = QPushButton("  List installers")
        list_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        list_btn.clicked.connect(lambda: self._controller.handle_user_input("list", self))
        layout.addWidget(list_btn)

        layout.addSpacing(16)
        tips_title = QLabel("QUICK COMMANDS")
        tips_title.setObjectName("sidebarTitle")
        layout.addWidget(tips_title)

        tips = QLabel(
            "• install mingw-get-setup.exe\n"
            "• list\n"
            "• Use the chat box below"
        )
        tips.setWordWrap(True)
        tips.setStyleSheet(
            f"color: {self._palette.text_secondary}; font-size: 9pt; line-height: 1.5;"
        )
        layout.addWidget(tips)
        layout.addStretch(1)

        version = QLabel("Local AI • Ollama")
        version.setStyleSheet(f"color: {self._palette.text_secondary}; font-size: 8pt;")
        layout.addWidget(version)
        return sidebar

    def _build_chat_area(self) -> QFrame:
        surface = QFrame()
        surface.setObjectName("chatSurface")
        layout = QVBoxLayout(surface)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._chat)
        return surface

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("&File")
        quit_action = QAction("E&xit", self)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        help_menu = self.menuBar().addMenu("&Help")
        about_action = QAction("&About SmartInstall AI", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _wire_events(self) -> None:
        self._controller.on_message = self._on_chat_message
        self._chat.message_submitted.connect(self._on_user_message)
        self._controller.event_bridge.status_update.connect(self._on_status_update)

    def _on_status_update(self, message: str) -> None:
        self._status_label.setText(message[:80])

    def _on_user_message(self, text: str) -> None:
        self._append_user_message(text)
        self._status_label.setText("Working…")
        self._controller.handle_user_input(text, self)
        self._chat.set_input_enabled(not self._controller.is_busy)

    def _on_chat_message(self, message: ChatMessage) -> None:
        self._chat.append_message(message)
        self._chat.set_input_enabled(not self._controller.is_busy)
        if message.role is ChatRole.ASSISTANT and message.title:
            self._status_label.setText("Ready")

    def _append_user_message(self, text: str) -> None:
        self._chat.append_message(ChatMessage(role=ChatRole.USER, content=text))

    def _show_about(self) -> None:
        self._chat.append_message(
            ChatMessage(
                role=ChatRole.ASSISTANT,
                title="About SmartInstall AI",
                content=(
                    "Monitor Windows installations, collect diagnostics, "
                    "and get local AI-powered troubleshooting.\n\n"
                    "Powered by your unified JSON reports and Ollama SLM."
                ),
            )
        )
