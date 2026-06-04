"""Real-time installation monitoring workspace."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
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
from smartinstall.ui.components.enterprise_button import hero_outline_button, hero_primary_button
from smartinstall.ui.components.install_visualizer import InstallVisualizer, InstallVisualState
from smartinstall.ui.components.ui_card import PAGE_MARGIN, PAGE_SPACING, section_card
from smartinstall.ui.theme.cctech_theme import CCTechPalette, body_stylesheet, heading_stylesheet, muted_stylesheet
from smartinstall.ui.widgets.live_log_viewer import LiveLogViewer
from smartinstall.ui.widgets.monitoring_assistance_panel import MonitoringAssistancePanel


class MonitoringPage(QScrollArea):
    """Installation progress, timeline, live logs, and AI assistance."""

    view_details_requested = Signal()
    export_logs_requested = Signal()
    open_troubleshooting_requested = Signal()

    def __init__(self, palette: CCTechPalette, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._palette = palette
        self._installation_status = "Ready"
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

        workspace = QHBoxLayout()
        workspace.setSpacing(GRID_GAP := 16)

        left_col = QVBoxLayout()
        left_col.setSpacing(12)
        left_col.addWidget(self._build_overview_card())
        left_col.addWidget(self._build_timeline_card())
        workspace.addLayout(left_col, stretch=2)

        center_col = QVBoxLayout()
        self._live_logs = LiveLogViewer(palette)
        center_col.addWidget(self._titled_card("Live Activity", self._live_logs))
        workspace.addLayout(center_col, stretch=3)

        self._assistance = MonitoringAssistancePanel(palette)
        workspace.addWidget(self._assistance, stretch=2)

        root.addLayout(workspace, stretch=1)
        root.addWidget(self._build_summary_bar())

    def _build_overview_card(self) -> QFrame:
        p = self._palette
        hero_card, hero_outer = section_card(p, object_name="monCard")
        hero_layout = QHBoxLayout()
        hero_layout.setSpacing(16)
        hero_layout.setContentsMargins(0, 0, 0, 0)

        self._visualizer = InstallVisualizer(p, size=120)
        hero_layout.addWidget(self._visualizer, alignment=Qt.AlignmentFlag.AlignTop)

        status_col = QVBoxLayout()
        status_col.setSpacing(8)

        self._status_label = QLabel("No active installation")
        self._status_label.setWordWrap(True)
        self._status_label.setStyleSheet(heading_stylesheet(p, size_pt=12))

        self._phase_label = QLabel("Installation status: Ready")
        self._phase_label.setStyleSheet(muted_stylesheet(p))

        self._stage_label = QLabel("Current phase: idle")
        self._stage_label.setStyleSheet(muted_stylesheet(p))

        self._process_label = QLabel("Process: —")
        self._process_label.setStyleSheet(body_stylesheet(p))

        self._duration_label = QLabel("Start time: —")
        self._duration_label.setStyleSheet(body_stylesheet(p))

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setTextVisible(False)

        status_col.addWidget(self._status_label)
        status_col.addWidget(self._phase_label)
        status_col.addWidget(self._stage_label)
        status_col.addWidget(self._process_label)
        status_col.addWidget(self._duration_label)
        status_col.addWidget(self._progress)
        hero_layout.addLayout(status_col, stretch=1)
        hero_outer.addLayout(hero_layout)
        return hero_card

    def _build_timeline_card(self) -> QFrame:
        p = self._palette
        self._timeline_label = QLabel("Waiting for installation workflow…")
        self._timeline_label.setWordWrap(True)
        self._timeline_label.setStyleSheet(body_stylesheet(p))
        return self._titled_card("Installation timeline", self._timeline_label)

    def _build_summary_bar(self) -> QFrame:
        p = self._palette
        bar, layout = section_card(p, object_name="monSummaryBar")
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        self._summary_label = QLabel("Installation summary will appear when monitoring starts.")
        self._summary_label.setWordWrap(True)
        self._summary_label.setStyleSheet(body_stylesheet(p))
        row.addWidget(self._summary_label, stretch=1)

        details_btn = hero_outline_button("View Details", p, parent=bar)
        details_btn.clicked.connect(self.view_details_requested.emit)
        export_btn = hero_outline_button("Export Logs", p, parent=bar)
        export_btn.clicked.connect(self.export_logs_requested.emit)
        ts_btn = hero_primary_button("Open Troubleshooting", p, parent=bar)
        ts_btn.clicked.connect(self.open_troubleshooting_requested.emit)
        row.addWidget(details_btn)
        row.addWidget(export_btn)
        row.addWidget(ts_btn)
        layout.addLayout(row)
        return bar

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

    @property
    def assistance_panel(self) -> MonitoringAssistancePanel:
        return self._assistance

    def set_installation_status(self, status: str) -> None:
        self._installation_status = status
        self._phase_label.setText(f"Installation status: {status}")

    def set_idle(self) -> None:
        self._visualizer.set_state(InstallVisualState.IDLE)
        p = self._palette
        self.set_installation_status("Ready")
        self._status_label.setText("Ready — no active installation")
        self._status_label.setStyleSheet(heading_stylesheet(p, size_pt=12))
        self._stage_label.setText("Current phase: idle")
        self._process_label.setText("Process: —")
        self._duration_label.setText("Start time: —")
        self._progress.setValue(0)
        self._progress.setStyleSheet("")
        self._timeline_label.setText(
            "1.  Detected / Preparing\n"
            "2.  Running installer & monitoring processes\n"
            "3.  Post-snapshot & evidence collection\n"
            "4.  AI diagnosis (when errors occur)"
        )
        self._summary_label.setText("No active installation.")
        self._assistance.reset_for_new_install()

    def begin_monitoring(
        self,
        *,
        installer_name: str,
        session_id: str = "",
        pid: int = 0,
        mode: str = "manual",
    ) -> None:
        self._assistance.reset_for_new_install()
        self.set_installation_status("Detected")
        self._live_logs.clear()
        self._live_logs.append_line(f"Smart Installer detected: {installer_name}")
        if session_id:
            self._live_logs.append_line(f"Session ID: {session_id}")
        if pid:
            self.set_process_info(f"pid={pid}  ·  {mode}")
        self.set_busy(f"Monitoring: {installer_name}")
        self.set_installation_status("Preparing")

    def set_busy(self, message: str) -> None:
        self._visualizer.set_state(InstallVisualState.BUSY)
        p = self._palette
        self._status_label.setText(message)
        self._status_label.setStyleSheet(
            f"font-size: 12pt; font-weight: 700; color: {p.blue_600};"
        )
        if self._installation_status in {"Ready", "Detected"}:
            self.set_installation_status("Running")
        current = self._progress.value()
        if current < 90:
            self._progress.setValue(min(90, current + 8 if current else 45))

    def set_stage(self, stage: str) -> None:
        self._stage_label.setText(f"Current phase: {stage}")
        self._append_timeline(stage)

    def set_process_info(self, text: str) -> None:
        self._process_label.setText(f"Process: {text}")

    def set_start_time(self, timestamp: str) -> None:
        self._duration_label.setText(f"Start time: {timestamp or '—'}")

    def set_duration(self, seconds: float | None) -> None:
        if seconds is not None:
            self._duration_label.setText(f"Duration: {seconds:.0f}s")

    def set_success(self, result: AutomatedRunResult) -> None:
        self._visualizer.set_state(InstallVisualState.SUCCESS)
        self.set_installation_status("Success")
        self.apply_run_result(result, preserve_logs=True)
        p = self._palette
        self._status_label.setStyleSheet(
            f"font-size: 12pt; font-weight: 700; color: {p.success};"
        )
        self._progress.setValue(100)
        self._progress.setStyleSheet(
            f"QProgressBar::chunk {{ background: {p.success}; border-radius: 4px; }}"
        )

    def set_error(self, result: AutomatedRunResult) -> None:
        self._visualizer.set_state(InstallVisualState.ERROR)
        self.set_installation_status("Failed")
        self.apply_run_result(result, preserve_logs=True)
        p = self._palette
        self._status_label.setStyleSheet(
            f"font-size: 12pt; font-weight: 700; color: {p.error};"
        )
        self._progress.setStyleSheet(
            f"QProgressBar::chunk {{ background: {p.error}; border-radius: 4px; }}"
        )
        self._live_logs.append_line(
            "Installation encountered errors — see AI Assistance and Troubleshooting."
        )

    def append_log(self, line: str) -> None:
        self._live_logs.append_line(line)
        lower = line.lower()
        if any(tok in lower for tok in ("error", "failed", "exception", "fatal")):
            self._visualizer.set_state(InstallVisualState.ERROR)

    def apply_run_result(
        self,
        result: AutomatedRunResult | None,
        *,
        preserve_logs: bool = False,
    ) -> None:
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
        warn_count = sum(
            1 for e in report.errors if str(getattr(e, "category", "")).lower() == "warning"
        )
        self._summary_label.setText(
            f"{status.installer.installer_name} — {status.installation_outcome} "
            f"({len(report.errors)} issue(s), {warn_count} warning(s))"
        )
        self._assistance.apply_errors_from_report(report.errors)
        if not preserve_logs:
            self._live_logs.clear()
            for error in report.errors[:40]:
                self._live_logs.append_line(
                    f"[{error.category}]  {error.code}:  {error.message}"
                )

    def _append_timeline(self, stage: str) -> None:
        current = self._timeline_label.text()
        line = f"•  {stage}"
        if line not in current:
            self._timeline_label.setText(f"{current}\n{line}" if current else line)

    def export_logs_dialog(self) -> None:
        self._live_logs.export_logs_dialog()
