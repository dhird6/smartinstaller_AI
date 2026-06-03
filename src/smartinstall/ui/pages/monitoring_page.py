"""Real-time installation monitoring workspace."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from smartinstall.agent.orchestration.automated_run_orchestrator import AutomatedRunResult
from smartinstall.ui.components.install_visualizer import InstallVisualizer, InstallVisualState
from smartinstall.ui.components.ui_card import PAGE_MARGIN, PAGE_SPACING, section_card
from smartinstall.ui.theme.cctech_theme import CCTechPalette, body_stylesheet, heading_stylesheet, muted_stylesheet
from smartinstall.ui.widgets.live_log_viewer import LiveLogViewer


class MonitoringPage(QScrollArea):
    """Installation progress, timeline, live logs, and status orb."""

    def __init__(self, palette: CCTechPalette, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._palette = palette
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        container.setObjectName("monContainer")
        container.setStyleSheet(
            f"QWidget#monContainer {{ background: {palette.canvas}; }}"
        )
        self.setWidget(container)

        root = QVBoxLayout(container)
        root.setContentsMargins(PAGE_MARGIN, PAGE_MARGIN, PAGE_MARGIN, PAGE_MARGIN)
        root.setSpacing(PAGE_SPACING)

        hero_card, hero_outer = section_card(palette, object_name="monCard")
        hero_layout = QHBoxLayout()
        hero_layout.setSpacing(24)
        hero_layout.setContentsMargins(0, 0, 0, 0)

        self._visualizer = InstallVisualizer(palette, size=160)
        hero_layout.addWidget(self._visualizer, alignment=Qt.AlignmentFlag.AlignTop)

        status_col = QVBoxLayout()
        status_col.setSpacing(10)

        self._status_label = QLabel("No active installation")
        self._status_label.setWordWrap(True)
        self._status_label.setStyleSheet(heading_stylesheet(palette, size_pt=14))

        self._stage_label = QLabel("Stage: idle")
        self._stage_label.setStyleSheet(muted_stylesheet(palette))

        self._process_label = QLabel("Process: —")
        self._process_label.setStyleSheet(body_stylesheet(palette))

        self._duration_label = QLabel("Duration: —")
        self._duration_label.setStyleSheet(body_stylesheet(palette))

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setTextVisible(False)

        progress_caption = QLabel("Workflow progress")
        progress_caption.setStyleSheet(muted_stylesheet(palette))

        status_col.addWidget(self._status_label)
        status_col.addWidget(self._stage_label)
        status_col.addWidget(self._process_label)
        status_col.addWidget(self._duration_label)
        status_col.addWidget(self._progress)
        status_col.addWidget(progress_caption)
        status_col.addStretch(1)
        hero_layout.addLayout(status_col, stretch=1)
        hero_outer.addLayout(hero_layout)
        root.addWidget(hero_card)

        self._timeline_label = QLabel("Waiting for installation workflow…")
        self._timeline_label.setWordWrap(True)
        self._timeline_label.setStyleSheet(body_stylesheet(palette))
        root.addWidget(self._titled_card("Installation timeline", self._timeline_label))

        self._live_logs = LiveLogViewer(palette)
        root.addWidget(self._titled_card("Live log stream", self._live_logs))
        root.addStretch(1)

    def _titled_card(self, title: str, content: QWidget) -> QFrame:
        p = self._palette
        card, layout = section_card(p, object_name="monCard")
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(heading_stylesheet(p, size_pt=12))
        layout.addWidget(title_lbl)
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {p.border};")
        layout.addWidget(sep)
        layout.addWidget(content)
        return card

    def set_idle(self) -> None:
        self._visualizer.set_state(InstallVisualState.IDLE)
        p = self._palette
        self._status_label.setText("Ready — no active installation")
        self._status_label.setStyleSheet(heading_stylesheet(p, size_pt=14))
        self._stage_label.setText("Stage: idle")
        self._process_label.setText("Process: —")
        self._duration_label.setText("Duration: —")
        self._progress.setValue(0)
        self._progress.setStyleSheet("")
        self._timeline_label.setText(
            "1.  Pre-snapshot  (registry, filesystem, event log)\n"
            "2.  Run installer & monitor processes\n"
            "3.  Post-snapshot & evidence collection\n"
            "4.  AI diagnosis via local SLM"
        )

    def set_busy(self, message: str) -> None:
        self._visualizer.set_state(InstallVisualState.BUSY)
        p = self._palette
        self._status_label.setText(message)
        self._status_label.setStyleSheet(
            f"font-size: 14pt; font-weight: 700; color: {p.blue_600};"
        )
        current = self._progress.value()
        if current < 90:
            self._progress.setValue(min(90, current + 8 if current else 45))

    def set_stage(self, stage: str) -> None:
        self._stage_label.setText(f"Stage: {stage}")

    def set_process_info(self, text: str) -> None:
        self._process_label.setText(f"Process: {text}")

    def set_duration(self, seconds: float | None) -> None:
        if seconds is None:
            self._duration_label.setText("Duration: —")
        else:
            self._duration_label.setText(f"Duration: {seconds:.0f}s")

    def set_success(self, result: AutomatedRunResult) -> None:
        self._visualizer.set_state(InstallVisualState.SUCCESS)
        self.apply_run_result(result)
        p = self._palette
        self._status_label.setStyleSheet(
            f"font-size: 14pt; font-weight: 700; color: {p.success};"
        )
        self._progress.setStyleSheet(
            f"QProgressBar::chunk {{ background: {p.success}; border-radius: 4px; }}"
        )

    def set_error(self, result: AutomatedRunResult) -> None:
        self._visualizer.set_state(InstallVisualState.ERROR)
        self.apply_run_result(result)
        p = self._palette
        self._status_label.setStyleSheet(
            f"font-size: 14pt; font-weight: 700; color: {p.error};"
        )
        self._progress.setStyleSheet(
            f"QProgressBar::chunk {{ background: {p.error}; border-radius: 4px; }}"
        )
        self._live_logs.append_line(
            "Installation encountered errors — open Troubleshooting for AI analysis."
        )

    def append_log(self, line: str) -> None:
        self._live_logs.append_line(line)
        lower = line.lower()
        if any(tok in lower for tok in ("error", "failed", "exception", "fatal")):
            self._visualizer.set_state(InstallVisualState.ERROR)

    def apply_run_result(self, result: AutomatedRunResult | None) -> None:
        if result is None:
            self.set_idle()
            return
        report = result.report
        status = report.status
        self._status_label.setText(
            f"{status.installer.installer_name}  ·  {status.installation_outcome}"
        )
        self._progress.setValue(100 if status.installation_completed else 65)
        self._timeline_label.setText(
            f"Session ID    {status.session_id}\n"
            f"Duration      {status.duration_seconds or '—'} s\n"
            f"Exit code     {status.installer.exit_code}\n"
            f"Report path   {result.report_path}"
        )
        self.set_duration(status.duration_seconds)
        self._live_logs.clear()
        for error in report.errors[:40]:
            self._live_logs.append_line(f"[{error.category}]  {error.code}:  {error.message}")
