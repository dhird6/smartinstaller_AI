"""Full installation diagnostics — summary, logs, errors, and AI analysis."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QFrame, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout

from smartinstall.agent.orchestration.automated_run_orchestrator import AutomatedRunResult
from smartinstall.ui.components.enterprise_button import hero_outline_button, hero_primary_button
from smartinstall.ui.services.slm_response_parser import partition_slm_answer
from smartinstall.ui.theme.cctech_theme import CCTechPalette, body_stylesheet, heading_stylesheet, muted_stylesheet


class InstallationDetailsDialog(QDialog):
    """View Details screen for a completed or in-progress installation session."""

    def __init__(
        self,
        palette: CCTechPalette,
        *,
        run_result: AutomatedRunResult,
        slm_answer: str = "",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._palette = palette
        self.setWindowTitle("Installation Details")
        self.setModal(True)
        self.resize(720, 640)
        self._build_ui(run_result=run_result, slm_answer=slm_answer)

    def _build_ui(self, *, run_result: AutomatedRunResult, slm_answer: str) -> None:
        p = self._palette
        report = run_result.report
        status = report.status
        installer = status.installer
        slm = partition_slm_answer(slm_answer)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 20, 20, 20)
        outer.setSpacing(10)

        headline = QLabel("Installation Summary")
        headline.setStyleSheet(heading_stylesheet(p, size_pt=14))
        outer.addWidget(headline)

        summary = QLabel(
            f"<b>Installer</b> {installer.installer_name}<br/>"
            f"<b>Outcome</b> {status.installation_outcome}<br/>"
            f"<b>Start</b> {status.start_timestamp}<br/>"
            f"<b>End</b> {status.end_timestamp or '—'}<br/>"
            f"<b>Duration</b> {status.duration_seconds or '—'} s<br/>"
            f"<b>Status</b> {'Completed' if status.installation_completed else 'Incomplete'}"
        )
        summary.setTextFormat(Qt.TextFormat.RichText)
        summary.setWordWrap(True)
        summary.setStyleSheet(body_stylesheet(p))
        outer.addWidget(summary)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        body_host = QWidget()
        body_layout = QVBoxLayout(body_host)
        body_layout.setSpacing(14)

        body_layout.addWidget(self._section(p, "Captured Logs", self._load_session_logs(run_result)))
        body_layout.addWidget(
            self._section(
                p,
                "Errors",
                self._format_errors(report.errors) if report.errors else "No errors recorded.",
            )
        )
        warnings = [
            e for e in report.errors if str(getattr(e, "category", "")).lower() == "warning"
        ]
        body_layout.addWidget(
            self._section(
                p,
                "Warnings",
                self._format_errors(warnings) if warnings else "No warnings recorded.",
            )
        )
        ai_text = slm.full_text or "AI analysis not available for this session."
        body_layout.addWidget(self._section(p, "AI Analysis", ai_text))
        fix_text = slm.recommended_fix or slm.root_cause or "No suggested resolution generated."
        body_layout.addWidget(self._section(p, "Suggested Resolution", fix_text))
        body_layout.addStretch(1)

        scroll.setWidget(body_host)
        outer.addWidget(scroll, stretch=1)

        actions = QHBoxLayout()
        actions.addStretch(1)
        close_btn = hero_outline_button("Close", p, parent=self)
        close_btn.clicked.connect(self.accept)
        report_btn = hero_primary_button("Open Report Folder", p, parent=self)
        report_btn.clicked.connect(lambda: self._open_report_parent(run_result.report_path))
        actions.addWidget(close_btn)
        actions.addWidget(report_btn)
        outer.addLayout(actions)

    def _section(self, palette: CCTechPalette, title: str, body: str) -> QLabel:
        block = QLabel(f"<b style='font-size:11pt'>{title}</b><br/>{body}")
        block.setWordWrap(True)
        block.setTextFormat(Qt.TextFormat.RichText)
        block.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        block.setStyleSheet(body_stylesheet(palette) + " " + muted_stylesheet(palette))
        return block

    @staticmethod
    def _format_errors(errors: list[object]) -> str:
        lines = []
        for err in errors[:30]:
            code = str(getattr(err, "code", ""))
            message = str(getattr(err, "message", ""))
            category = str(getattr(err, "category", ""))
            lines.append(f"• [{category}] {code}: {message[:400]}")
        return "<br/>".join(lines) if lines else "None"

    @staticmethod
    def _load_session_logs(run_result: AutomatedRunResult) -> str:
        artifact = Path(run_result.report.status.artifact_directory)
        chunks: list[str] = []
        for name in ("stdout.log", "stderr.log", "stdout_passive.log", "stderr_passive.log"):
            path = artifact / name
            if path.is_file():
                try:
                    text = path.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
                if text.strip():
                    chunks.append(f"--- {name} ---\n{text[-8000:]}")
        return "\n\n".join(chunks) if chunks else "No captured stdout/stderr logs in session artifacts."

    @staticmethod
    def _open_report_parent(report_path: Path) -> None:
        import os

        folder = report_path.parent
        if folder.is_dir():
            os.startfile(str(folder))  # noqa: S606 — Windows folder open


def _heuristic_fix(message: str) -> str:
    lowered = message.lower()
    if "access denied" in lowered or "elevation" in lowered:
        return "Run the installer as Administrator."
    if "visual c++" in lowered or "vcruntime" in lowered or "msvcp" in lowered:
        return "Install Microsoft Visual C++ Redistributable."
    if ".net" in lowered:
        return "Install the required .NET Framework runtime."
    if "1618" in lowered:
        return "Wait for other MSI installations to finish, then retry."
    if "download" in lowered or "network" in lowered:
        return "Check network connectivity and proxy settings, then retry."
    return "Review Troubleshooting for full AI-guided steps."
