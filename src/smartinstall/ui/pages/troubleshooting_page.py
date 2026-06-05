"""Installation failure analysis workspace — professional expandable sections."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from smartinstall.agent.orchestration.automated_run_orchestrator import AutomatedRunResult
from smartinstall.ui.components.ui_card import PAGE_MARGIN, PAGE_SPACING, apply_card_style
from smartinstall.ui.layout.responsive import configure_page_container, configure_page_scroll
from smartinstall.ui.services.slm_response_parser import partition_slm_answer
from smartinstall.ui.theme.cctech_theme import CCTechPalette, body_stylesheet, heading_stylesheet, muted_stylesheet

# (title, icon, semantic)
_SECTIONS: tuple[tuple[str, str, str], ...] = (
    ("Error logs & detection", "🔍", "error"),
    ("Root cause analysis", "🧠", "warning"),
    ("Similar incidents  ·  RAG retrieval", "📚", "info"),
    ("AI recommendations & resolution steps", "🤖", "success"),
)


class TroubleshootingPage(QScrollArea):
    """Expandable failure-analysis cards driven by run result and SLM output."""

    def __init__(self, palette: CCTechPalette, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._palette = palette
        configure_page_scroll(self)

        self._container = QWidget()
        self._container.setObjectName("tshootContainer")
        self._container.setStyleSheet(
            f"QWidget#tshootContainer {{ background: {palette.canvas}; }}"
        )
        configure_page_container(self._container)
        self.setWidget(self._container)

        self._layout = QVBoxLayout(self._container)
        self._layout.setContentsMargins(PAGE_MARGIN, PAGE_MARGIN, PAGE_MARGIN, PAGE_MARGIN)
        self._layout.setSpacing(PAGE_SPACING)

        self._history_bar = QFrame()
        self._history_bar.setObjectName("tshootHistoryBar")
        self._history_bar.hide()
        history_layout = QHBoxLayout(self._history_bar)
        history_layout.setContentsMargins(0, 0, 0, 0)
        history_layout.setSpacing(10)
        history_label = QLabel("Installation history")
        history_label.setStyleSheet(heading_stylesheet(palette, size_pt=10))
        self._history_combo = QComboBox()
        self._history_combo.setMinimumWidth(0)
        self._history_combo.currentIndexChanged.connect(self._on_history_selected)
        history_layout.addWidget(history_label)
        history_layout.addWidget(self._history_combo, stretch=1)
        self._layout.addWidget(self._history_bar)

        self._content_host = QWidget()
        self._content_layout = QVBoxLayout(self._content_host)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(PAGE_SPACING)
        self._layout.addWidget(self._content_host, stretch=1)

        self._placeholder = QLabel(
            "Run an installation to populate failure analysis, root cause diagnosis, "
            "vector-retrieved knowledge, and AI recommendations from SmartInstall AI."
        )
        self._placeholder.setWordWrap(True)
        self._placeholder.setStyleSheet(muted_stylesheet(palette) + " font-size: 11pt;")
        self._content_layout.addWidget(self._placeholder)
        self._content_layout.addStretch(1)

        self._run_history: list[AutomatedRunResult] = []
        self._history_slm: dict[str, tuple[str | None, list[str] | None, str]] = {}
        self._suppress_history_signal = False

    def set_run_history(
        self,
        runs: list[AutomatedRunResult],
        *,
        slm_by_session: dict[str, tuple[str | None, list[str] | None, str]] | None = None,
        selected_session_id: str | None = None,
    ) -> None:
        """Populate the session picker used when reviewing prior installs."""
        self._run_history = list(runs)
        if slm_by_session is not None:
            self._history_slm = dict(slm_by_session)

        self._suppress_history_signal = True
        self._history_combo.clear()
        if not runs:
            self._history_bar.hide()
            self._suppress_history_signal = False
            return

        for run in runs:
            status = run.report.status
            label = (
                f"{run.discovered.file_name} — {status.installation_outcome}"
                f"  ({status.end_timestamp or status.start_timestamp})"
            )
            self._history_combo.addItem(label, run.session.session_id)

        self._history_bar.show()
        target_index = 0
        if selected_session_id:
            for idx in range(self._history_combo.count()):
                if self._history_combo.itemData(idx) == selected_session_id:
                    target_index = idx
                    break
        self._history_combo.setCurrentIndex(target_index)
        self._suppress_history_signal = False

    def _on_history_selected(self, index: int) -> None:
        if self._suppress_history_signal or index < 0 or index >= len(self._run_history):
            return
        run = self._run_history[index]
        session_id = run.session.session_id
        slm_answer, slm_sources, slm_status = self._history_slm.get(session_id, (None, None, "none"))
        self.apply_run_result(
            run,
            slm_answer=slm_answer,
            slm_sources=slm_sources,
            slm_status=slm_status,
        )

    def apply_run_result(
        self,
        result: AutomatedRunResult | None,
        *,
        slm_answer: str | None = None,
        slm_sources: list[str] | None = None,
        slm_status: str = "none",
    ) -> None:
        """Populate all troubleshooting sections from report + optional SLM output."""
        self._clear()
        if result is None:
            self._content_layout.addWidget(self._placeholder)
            self._content_layout.addStretch(1)
            return

        report = result.report
        p = self._palette
        slm = partition_slm_answer(slm_answer or "")
        sources = list(slm_sources or [])
        outcome = report.status.installation_outcome
        failed = outcome.lower() in {"failed", "failure", "error"} or bool(report.errors)

        page_title = "Installation Troubleshooting" if failed else "Installation Analysis"
        heading = QLabel(page_title)
        heading.setStyleSheet(heading_stylesheet(p, size_pt=16))
        self._content_layout.addWidget(heading)

        sub = QLabel(
            f"Installer: <b>{report.status.installer.installer_name}</b>"
            f"  ·  Outcome: <b>{outcome}</b>"
            f"  ·  {len(report.errors)} error(s) in report"
        )
        sub.setTextFormat(Qt.TextFormat.RichText)
        sub.setWordWrap(True)
        sub.setStyleSheet(body_stylesheet(p))
        self._content_layout.addWidget(sub)

        self._content_layout.addWidget(self._slm_status_banner(slm_status, slm_answer, failed))

        meta = QLabel(
            f"Session: {report.status.session_id}  ·  Report: {result.report_path}"
        )
        meta.setWordWrap(True)
        meta.setStyleSheet(muted_stylesheet(p))
        self._content_layout.addWidget(meta)
        self._content_layout.addSpacing(6)

        # Section 0 — errors (report + SLM summary)
        errors_lines: list[str] = []
        if report.errors:
            errors_lines.extend(
                f"• [{e.category}]  {e.code}:  {e.message[:500]}"
                for e in report.errors[:25]
            )
        if slm.error_summary:
            errors_lines.append("")
            errors_lines.append("From AI error summary:")
            errors_lines.append(slm.error_summary)
        errors_text = "\n".join(errors_lines) or (
            "No errors recorded in this session."
            if not failed
            else "No structured errors in the report — see AI analysis below."
        )
        self._content_layout.addWidget(
            self._expandable(_SECTIONS[0][0], errors_text, icon=_SECTIONS[0][1], semantic=_SECTIONS[0][2])
        )

        # Section 1 — root cause (SLM preferred)
        root_cause = (
            slm.root_cause
            or report.status.failure_reason
            or (
                "No explicit failure reason in the report."
                if failed
                else "Installation completed without a recorded failure reason."
            )
        )
        self._content_layout.addWidget(
            self._expandable(_SECTIONS[1][0], root_cause, icon=_SECTIONS[1][1], semantic=_SECTIONS[1][2])
        )

        # Section 2 — RAG
        rag_lines: list[str] = []
        if sources:
            rag_lines.append("Retrieved knowledge documents:")
            rag_lines.extend(f"  •  {src}" for src in sources)
            rag_lines.append("")
        else:
            rag_lines.append(
                "No RAG document sources returned yet. "
                "Sources appear after local SLM diagnosis (Ollama + rag_docs/)."
            )
            rag_lines.append("")
        rag_lines.append(
            f"Evidence collected:  {len(report.evidence.event_logs)} event log(s)  ·  "
            f"{len(report.evidence.installer_log_files)} installer log(s)  ·  "
            f"{len(report.evidence.registry_changes)} registry change(s)  ·  "
            f"{len(report.evidence.filesystem_changes)} filesystem change(s)"
        )
        self._content_layout.addWidget(
            self._expandable(
                _SECTIONS[2][0],
                "\n".join(rag_lines),
                icon=_SECTIONS[2][1],
                semantic=_SECTIONS[2][2],
            )
        )

        # Section 3 — AI recommendations (always show full SLM when available)
        ai_body = _format_ai_section(slm, slm_status=slm_status, failed=failed)
        self._content_layout.addWidget(
            self._expandable(
                _SECTIONS[3][0],
                ai_body,
                icon=_SECTIONS[3][1],
                semantic=_SECTIONS[3][2],
                expanded=True,
            )
        )

        self._content_layout.addStretch(1)
        self.verticalScrollBar().setValue(0)

    def _slm_status_banner(
        self,
        slm_status: str,
        slm_answer: str | None,
        failed: bool,
    ) -> QFrame:
        p = self._palette
        banner = QFrame()
        banner.setObjectName("slmBanner")
        if slm_answer and slm_answer.strip():
            bg = p.success_bg
            border = p.success
            text = "AI diagnosis complete — recommendations are shown below."
        elif slm_status == "running":
            bg = p.info_bg
            border = p.info
            text = "Running local AI troubleshooting (Ollama SLM)…"
        elif failed:
            bg = p.warning_bg
            border = p.warning
            text = (
                "AI diagnosis pending. Ensure Ollama is running with phi3:mini and "
                "nomic-embed-text, and autoRunSlm is enabled in config."
            )
        else:
            bg = p.surface_muted
            border = p.border
            text = "No AI diagnosis required for this successful installation."

        banner.setStyleSheet(
            f"QFrame#slmBanner {{ background: {bg}; border: 1px solid {border};"
            f" border-radius: 8px; padding: 4px; }}"
        )
        layout = QVBoxLayout(banner)
        layout.setContentsMargins(12, 10, 12, 10)
        lbl = QLabel(text)
        lbl.setWordWrap(True)
        lbl.setStyleSheet(body_stylesheet(p))
        layout.addWidget(lbl)
        return banner

    def _expandable(
        self,
        title: str,
        body: str,
        *,
        icon: str = "▸",
        semantic: str = "info",
        expanded: bool = True,
    ) -> QFrame:
        p = self._palette
        accent_map = {
            "error": p.error,
            "warning": p.warning,
            "info": p.info,
            "success": p.success,
        }
        bg_map = {
            "error": p.error_bg,
            "warning": p.warning_bg,
            "info": p.info_bg,
            "success": p.success_bg,
        }
        accent = accent_map.get(semantic, p.info)
        icon_bg = bg_map.get(semantic, p.info_bg)

        card = QFrame()
        apply_card_style(card, p, object_name="tshootCard")

        root_layout = QVBoxLayout(card)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        hdr = QFrame()
        hdr_layout = QHBoxLayout(hdr)
        hdr_layout.setContentsMargins(16, 14, 16, 14)
        hdr_layout.setSpacing(12)

        icon_badge = QLabel(icon)
        icon_badge.setFixedSize(32, 32)
        icon_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_badge.setStyleSheet(
            f"font-size: 14pt; background: {icon_bg}; border-radius: 8px;"
        )

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(heading_stylesheet(p, size_pt=11))

        toggle = QToolButton()
        toggle.setObjectName("tshootToggle")
        toggle.setCheckable(True)
        toggle.setChecked(expanded)
        toggle.setText("▾" if expanded else "▸")
        toggle.setStyleSheet(
            f"QToolButton#tshootToggle {{ color: {p.text_muted}; font-size: 13pt;"
            f" font-weight: 700; background: transparent; border: none; padding: 0; }}"
            f"QToolButton#tshootToggle:checked {{ color: {accent}; }}"
        )

        hdr_layout.addWidget(icon_badge)
        hdr_layout.addWidget(title_lbl, stretch=1)
        hdr_layout.addWidget(toggle, alignment=Qt.AlignmentFlag.AlignVCenter)
        root_layout.addWidget(hdr)

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {p.border}; margin: 0 16px;")
        root_layout.addWidget(sep)

        body_widget = QWidget()
        body_layout = QVBoxLayout(body_widget)
        body_layout.setContentsMargins(16, 14, 16, 18)
        body_lbl = QLabel(body)
        body_lbl.setWordWrap(True)
        body_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        body_lbl.setStyleSheet(body_stylesheet(p) + " font-size: 10.5pt; line-height: 1.45;")
        body_lbl.setMinimumHeight(48)
        body_layout.addWidget(body_lbl)
        root_layout.addWidget(body_widget)

        body_widget.setVisible(expanded)
        sep.setVisible(expanded)

        def _toggle(checked: bool) -> None:
            body_widget.setVisible(checked)
            sep.setVisible(checked)
            toggle.setText("▾" if checked else "▸")

        toggle.toggled.connect(_toggle)

        card.setStyleSheet(
            f"QFrame#tshootCard {{"
            f" background: {p.surface};"
            f" border: 1px solid {p.border};"
            f" border-left: 3px solid {accent};"
            f" border-radius: 12px;"
            f"}}"
        )
        return card

    def _clear(self) -> None:
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()


def _format_ai_section(slm: object, *, slm_status: str, failed: bool) -> str:
    from smartinstall.ui.services.slm_response_parser import SlmPartition

    if not isinstance(slm, SlmPartition):
        return "AI diagnosis unavailable."

    if slm_status == "running":
        return (
            "SmartInstall AI is querying the local SLM (Phi-3 via Ollama) and RAG knowledge base.\n"
            "This section will update automatically when diagnosis completes."
        )

    if not slm.full_text:
        if failed:
            return (
                "No AI response yet.\n\n"
                "Checklist:\n"
                "• Ollama is running (ollama serve)\n"
                "• Models installed: phi3:mini, nomic-embed-text\n"
                "• autoRunSlm is true in smartinstall.config.json\n"
                "• Installation produced errors or a failed outcome"
            )
        return "Installation succeeded — AI troubleshooting was not required."

    parts: list[str] = []
    if slm.recommended_fix:
        parts.append("Recommended steps:\n" + slm.recommended_fix)
    if slm.recommended_fix and slm.full_text != slm.recommended_fix:
        parts.append("")
        parts.append("Full AI response:\n" + slm.full_text)
    else:
        parts.append(slm.full_text)

    return "\n".join(parts).strip()
