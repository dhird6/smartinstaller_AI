"""CI/CD-style live log viewer with pause, search, filter, and export."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from smartinstall.ui.theme.cctech_theme import CCTechPalette, muted_stylesheet


class LiveLogViewer(QWidget):
    """Enterprise live log panel with streaming, filtering, and export."""

    def __init__(self, palette: CCTechPalette, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._palette = palette
        self._auto_scroll = True
        self._buffer: list[str] = []
        self._build_ui()

    def _build_ui(self) -> None:
        p = self._palette
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search logs…")
        self._search.textChanged.connect(self._refresh_view)

        self._filter = QComboBox()
        self._filter.addItems(["All", "Errors", "Warnings", "Info"])
        self._filter.currentTextChanged.connect(self._refresh_view)

        self._pause_btn = QPushButton("Pause")
        self._pause_btn.setCheckable(True)
        self._pause_btn.toggled.connect(self._on_pause_toggled)

        export_btn = QPushButton("Export")
        export_btn.clicked.connect(self._export_logs)

        toolbar.addWidget(self._search, stretch=2)
        toolbar.addWidget(self._filter)
        toolbar.addWidget(self._pause_btn)
        toolbar.addWidget(export_btn)
        root.addLayout(toolbar)

        self._log_view = QTextEdit()
        self._log_view.setReadOnly(True)
        self._log_view.setMinimumHeight(220)
        self._log_view.setFont(QFont("Cascadia Code", 9))
        if not QFont("Cascadia Code", 9).exactMatch():
            self._log_view.setFont(QFont("Consolas", 9))
        self._log_view.setStyleSheet(
            f"QTextEdit {{ background: {p.surface_muted}; color: {p.text_primary};"
            f" border: 1px solid {p.border}; border-radius: 8px; padding: 10px; }}"
        )
        root.addWidget(self._log_view)

        hint = QLabel("Live stream · auto-scroll when not paused")
        hint.setStyleSheet(muted_stylesheet(p))
        root.addWidget(hint)

    def append_line(self, line: str) -> None:
        self._buffer.append(line)
        if len(self._buffer) > 5000:
            self._buffer = self._buffer[-4000:]
        if not self._pause_btn.isChecked():
            self._refresh_view()

    def clear(self) -> None:
        self._buffer.clear()
        self._log_view.clear()

    def _on_pause_toggled(self, paused: bool) -> None:
        self._auto_scroll = not paused
        self._pause_btn.setText("Resume" if paused else "Pause")
        if not paused:
            self._refresh_view()

    def _refresh_view(self) -> None:
        query = self._search.text().strip().lower()
        mode = self._filter.currentText()
        lines: list[str] = []
        for line in self._buffer:
            lower = line.lower()
            if mode == "Errors" and not any(tok in lower for tok in ("error", "failed", "fatal")):
                continue
            if mode == "Warnings" and "warn" not in lower:
                continue
            if mode == "Info" and any(tok in lower for tok in ("error", "failed", "fatal", "warn")):
                continue
            if query and query not in lower:
                continue
            lines.append(line)

        self._log_view.clear()
        cursor = self._log_view.textCursor()
        for line in lines[-800:]:
            fmt = QTextCharFormat()
            lower = line.lower()
            if any(tok in lower for tok in ("error", "failed", "fatal")):
                fmt.setForeground(QColor(self._palette.error))
            elif "warn" in lower:
                fmt.setForeground(QColor(self._palette.warning))
            cursor.insertText(line + "\n", fmt)

        if self._auto_scroll:
            self._log_view.moveCursor(QTextCursor.MoveOperation.End)

    def _export_logs(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export logs",
            "smartinstall-live.log",
            "Log files (*.log);;Text files (*.txt)",
        )
        if not path:
            return
        Path(path).write_text("\n".join(self._buffer), encoding="utf-8")
