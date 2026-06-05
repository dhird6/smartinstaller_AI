"""CI/CD-style live log viewer with pause, search, filter, and export."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QTimer
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

    _BATCH_MS = 150
    _MAX_BUFFER = 5000
    _TRIM_TO = 4000
    _MAX_VISIBLE = 800

    def __init__(self, palette: CCTechPalette, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._palette = palette
        self._auto_scroll = True
        self._buffer: list[str] = []
        self._pending_lines: list[str] = []
        self._flush_timer = QTimer(self)
        self._flush_timer.setInterval(self._BATCH_MS)
        self._flush_timer.timeout.connect(self._flush_pending)
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
        self._search.textChanged.connect(self._on_filter_changed)

        self._filter = QComboBox()
        self._filter.addItems(["All", "Errors", "Warnings", "Info"])
        self._filter.currentTextChanged.connect(self._on_filter_changed)

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
        if len(self._buffer) > self._MAX_BUFFER:
            self._buffer = self._buffer[-self._TRIM_TO :]
        if self._pause_btn.isChecked():
            return
        if self._needs_full_refresh():
            if not self._flush_timer.isActive():
                self._flush_timer.start()
            self._pending_lines.append(line)
            return
        self._pending_lines.append(line)
        if not self._flush_timer.isActive():
            self._flush_timer.start()

    def clear(self) -> None:
        self._buffer.clear()
        self._pending_lines.clear()
        self._flush_timer.stop()
        self._log_view.clear()

    def _on_pause_toggled(self, paused: bool) -> None:
        self._auto_scroll = not paused
        self._pause_btn.setText("Resume" if paused else "Pause")
        if not paused:
            self._refresh_view()

    def _on_filter_changed(self, *_args: object) -> None:
        self._pending_lines.clear()
        self._flush_timer.stop()
        self._refresh_view()

    def _needs_full_refresh(self) -> bool:
        return bool(self._search.text().strip()) or self._filter.currentText() != "All"

    def _flush_pending(self) -> None:
        if not self._pending_lines:
            self._flush_timer.stop()
            return
        if self._needs_full_refresh():
            self._pending_lines.clear()
            self._refresh_view()
            self._flush_timer.stop()
            return

        cursor = self._log_view.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        batch = self._pending_lines
        self._pending_lines = []
        for line in batch:
            fmt = self._format_for_line(line)
            cursor.insertText(line + "\n", fmt)
        if self._auto_scroll:
            self._log_view.moveCursor(QTextCursor.MoveOperation.End)
        self._trim_visible_lines()
        if not self._pending_lines:
            self._flush_timer.stop()

    def _trim_visible_lines(self) -> None:
        doc = self._log_view.document()
        if doc.blockCount() <= self._MAX_VISIBLE + 50:
            return
        cursor = QTextCursor(doc)
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        excess = doc.blockCount() - self._MAX_VISIBLE
        for _ in range(excess):
            cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
            cursor.removeSelectedText()
            cursor.deleteChar()

    def _format_for_line(self, line: str) -> QTextCharFormat:
        fmt = QTextCharFormat()
        lower = line.lower()
        if any(tok in lower for tok in ("error", "failed", "fatal")):
            fmt.setForeground(QColor(self._palette.error))
        elif "warn" in lower:
            fmt.setForeground(QColor(self._palette.warning))
        return fmt

    def _line_matches_filter(self, line: str) -> bool:
        lower = line.lower()
        mode = self._filter.currentText()
        if mode == "Errors" and not any(tok in lower for tok in ("error", "failed", "fatal")):
            return False
        if mode == "Warnings" and "warn" not in lower:
            return False
        if mode == "Info" and any(tok in lower for tok in ("error", "failed", "fatal", "warn")):
            return False
        query = self._search.text().strip().lower()
        if query and query not in lower:
            return False
        return True

    def _refresh_view(self) -> None:
        lines = [line for line in self._buffer if self._line_matches_filter(line)]
        self._log_view.clear()
        cursor = self._log_view.textCursor()
        for line in lines[-self._MAX_VISIBLE :]:
            cursor.insertText(line + "\n", self._format_for_line(line))
        if self._auto_scroll:
            self._log_view.moveCursor(QTextCursor.MoveOperation.End)

    def export_logs_dialog(self) -> None:
        """Open save dialog and export the live log buffer."""
        self._export_logs()

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
