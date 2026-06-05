"""Real-time installation monitoring workspace."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from smartinstall.ui.layout.responsive import configure_page_scroll

from smartinstall.agent.orchestration.automated_run_orchestrator import AutomatedRunResult
from smartinstall.ui.components.enterprise_button import hero_outline_button, hero_primary_button
from smartinstall.ui.components.install_visualizer import InstallVisualizer, InstallVisualState
from smartinstall.ui.components.ui_card import PAGE_MARGIN, PAGE_SPACING, section_card
from smartinstall.ui.theme.cctech_theme import CCTechPalette, body_stylesheet, heading_stylesheet, muted_stylesheet
from smartinstall.ui.widgets.live_log_viewer import LiveLogViewer
from smartinstall.ui.widgets.monitoring_assistance_panel import MonitoringAssistancePanel

# Progress tied to real workflow phases — not auto-incremented.
_STATUS_PROGRESS: dict[str, int] = {
    "Ready": 0,
    "Detected": 12,
    "Preparing": 28,
    "Running": 52,
    "Collecting": 72,
    "Diagnosing": 88,
    "Success": 100,
    "Failed": 100,
}


class MonitoringPage(QScrollArea):
    """Installation progress, timeline, live logs, and AI assistance."""

    view_details_requested = Signal()
    export_logs_requested = Signal()
    open_troubleshooting_requested = Signal()

    def __init__(self, palette: CCTechPalette, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._palette = palette
        self._installation_status = "Ready"
        self._is_terminal = False
        configure_page_scroll(self)

        container = QWidget()
        container.setObjectName("monContainer")
        container.setStyleSheet(
            f"QWidget#monContainer {{ background: {palette.canvas}; }}"
        )
        self.setWidget(container)

        root = QVBoxLayout(container)
        root.setContentsMargins(PAGE_MARGIN, PAGE_MARGIN - 8, PAGE_MARGIN, PAGE_MARGIN)
        root.setSpacing(PAGE_SPACING - 4)

        # Top row: overview (left) + live logs (right) — vertical page, no horizontal columns.
        top_row = QHBoxLayout()
        top_row.setSpacing(12)
        top_row.addWidget(self._build_overview_card(), stretch=2)
        self._live_logs = LiveLogViewer(palette)
        top_row.addWidget(self._titled_card("Live Activity", self._live_logs), stretch=3)
        root.addLayout(top_row)

        root.addWidget(self._build_timeline_card())

        self._assistance = MonitoringAssistancePanel(palette)
        self._assistance.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        root.addWidget(self._assistance)

        root.addWidget(self._build_summary_bar())

    def _build_overview_card(self) -> QFrame:
        p = self._palette
        hero_card, hero_outer = section_card(p, object_name="monCard")
        hero_layout = QHBoxLayout()
        hero_layout.setSpacing(16)
        hero_layout.setContentsMargins(0, 0, 0, 0)

        self._visualizer = InstallVisualizer(p, size=110)
        hero_layout.addWidget(self._visualizer, alignment=Qt.AlignmentFlag.AlignTop)

        status_col = QVBoxLayout()
        status_col.setSpacing(8)

        self._status_label = QLabel("No active installation")
        self._status_label.setWordWrap(True)
        self._status_label.setStyleSheet(heading_stylesheet(p, size_pt=12))

        self._phase_label = QLabel("Installation status: Ready")
        self._phase_label.setWordWrap(True)
        self._phase_label.setStyleSheet(muted_stylesheet(p))

        self._stage_label = QLabel("Current phase: idle")
        self._stage_label.setWordWrap(True)
        self._stage_label.setStyleSheet(muted_stylesheet(p))

        self._process_label = QLabel("Process: —")
        self._process_label.setWordWrap(True)
        self._process_label.setStyleSheet(body_stylesheet(p))

        self._duration_label = QLabel("Start time: —")
        self._duration_label.setWordWrap(True)
        self._duration_label.setStyleSheet(body_stylesheet(p))

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setTextVisible(True)
        self._progress.setFormat("%p%")

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
        if not self._is_terminal:
            self._apply_progress_for_status(status)
            if status in {"Running", "Preparing", "Detected", "Collecting", "Diagnosing"}:
                self._visualizer.set_state(InstallVisualState.BUSY)

    def _apply_progress_for_status(self, status: str) -> None:
        value = _STATUS_PROGRESS.get(status, self._progress.value())
        self._progress.setValue(value)

    def _mark_running(self) -> None:
        self._is_terminal = False
        self._visualizer.set_state(InstallVisualState.BUSY)

    def _mark_terminal_success(self) -> None:
        self._is_terminal = True
        self._visualizer.set_state(InstallVisualState.SUCCESS)
        self._progress.setValue(100)
        p = self._palette
        self._progress.setStyleSheet(
            f"QProgressBar::chunk {{ background: {p.success}; border-radius: 4px; }}"
        )

    def _mark_terminal_error(self) -> None:
        self._is_terminal = True
        self._visualizer.set_state(InstallVisualState.ERROR)
        self._progress.setValue(100)
        p = self._palette
        self._progress.setStyleSheet(
            f"QProgressBar::chunk {{ background: {p.error}; border-radius: 4px; }}"
        )

    def set_idle(self) -> None:
        self._is_terminal = False
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
        self._is_terminal = False
        self._assistance.reset_for_new_install(installer_name=installer_name)
        self._live_logs.clear()
        self._live_logs.append_line(f"Smart Installer detected: {installer_name}")
        if session_id:
            self._live_logs.append_line(f"Session ID: {session_id}")
        if pid:
            self.set_process_info(f"pid={pid}  ·  {mode}")
        self._status_label.setText(f"Monitoring: {installer_name}")
        p = self._palette
        self._status_label.setStyleSheet(
            f"font-size: 12pt; font-weight: 700; color: {p.blue_600};"
        )
        self.set_installation_status("Detected")
        self._mark_running()

    def set_busy(self, message: str) -> None:
        if self._is_terminal:
            return
        p = self._palette
        self._status_label.setText(message)
        self._status_label.setStyleSheet(
            f"font-size: 12pt; font-weight: 700; color: {p.blue_600};"
        )
        if self._installation_status in {"Ready", "Detected"}:
            self.set_installation_status("Running")
        else:
            self._mark_running()

    def set_stage(self, stage: str) -> None:
        if self._is_terminal:
            return
        self._stage_label.setText(f"Current phase: {stage}")
        self._append_timeline(stage)
        lowered = stage.lower()
        if any(tok in lowered for tok in ("snapshot", "evidence", "collect")):
            self.set_installation_status("Collecting")
        elif any(tok in lowered for tok in ("diagnos", "slm", "rag", "troubleshoot")):
            self.set_installation_status("Diagnosing")
        elif any(tok in lowered for tok in ("run", "install", "monitor", "execut")):
            self.set_installation_status("Running")
        elif any(tok in lowered for tok in ("prepar", "detect", "start")):
            self.set_installation_status("Preparing")

    def set_process_info(self, text: str) -> None:
        self._process_label.setText(f"Process: {text}")

    def set_start_time(self, timestamp: str) -> None:
        self._duration_label.setText(f"Start time: {timestamp or '—'}")

    def set_duration(self, seconds: float | None) -> None:
        if seconds is not None:
            self._duration_label.setText(f"Duration: {seconds:.0f}s")

    def set_success(self, result: AutomatedRunResult) -> None:
        self.set_installation_status("Success")
        self.apply_run_result(result, preserve_logs=True)
        p = self._palette
        self._status_label.setStyleSheet(
            f"font-size: 12pt; font-weight: 700; color: {p.success};"
        )
        self._status_label.setText(
            f"Installation complete — {result.discovered.file_name}"
        )
        self._mark_terminal_success()

    def set_error(self, result: AutomatedRunResult) -> None:
        self.set_installation_status("Failed")
        self.apply_run_result(result, preserve_logs=True)
        p = self._palette
        self._status_label.setStyleSheet(
            f"font-size: 12pt; font-weight: 700; color: {p.error};"
        )
        self._status_label.setText(
            f"Installation failed — {result.discovered.file_name}"
        )
        self._mark_terminal_error()
        self._live_logs.append_line(
            "Installation encountered errors — see AI Assistance and Troubleshooting."
        )

    def append_log(self, line: str) -> None:
        self._live_logs.append_line(line)

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
        outcome = status.installation_outcome.lower()

        if outcome in {"success", "completed"}:
            self._mark_terminal_success()
            self.set_installation_status("Success")
        elif outcome in {"failed", "failure", "error", "crashed", "timedout"}:
            self._mark_terminal_error()
            self.set_installation_status("Failed")
        elif not self._is_terminal:
            self._mark_running()

        self._status_label.setText(
            f"{status.installer.installer_name}  ·  {status.installation_outcome}"
        )
        if not self._is_terminal:
            self._progress.setValue(65 if status.installation_completed else _STATUS_PROGRESS.get("Running", 52))

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
