"""Installation failure analysis — AI suggestions first, details below, chat for follow-up."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from smartinstall.agent.orchestration.automated_run_orchestrator import AutomatedRunResult
from smartinstall.ui.components.enterprise_button import hero_outline_button, hero_primary_button
from smartinstall.ui.components.ui_card import PAGE_MARGIN, PAGE_SPACING, apply_card_style
from smartinstall.ui.services.slm_diagnosis_display import format_slm_diagnosis
from smartinstall.ui.services.slm_response_parser import parse_slm_sections
from smartinstall.ui.services.troubleshooting_suggestions_service import build_ai_suggestions
from smartinstall.ui.theme.cctech_theme import CCTechPalette, body_stylesheet, heading_stylesheet, muted_stylesheet

_DETAIL_SECTIONS: tuple[tuple[str, str, str], ...] = (
    ("Error logs & detection", "🔍", "error"),
    ("Evidence & knowledge sources", "📚", "info"),
    ("Full AI analysis text", "🤖", "success"),
)


class TroubleshootingPage(QScrollArea):
    """Failure analysis with prominent AI suggestions and optional chat handoff."""

    open_ai_chat = Signal(str)

    def __init__(self, palette: CCTechPalette, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._palette = palette
        self._last_chat_prompt = ""
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)

        self._container = QWidget()
        self._container.setObjectName("tshootContainer")
        self._container.setStyleSheet(
            f"QWidget#tshootContainer {{ background: {palette.canvas}; }}"
        )
        self.setWidget(self._container)

        self._layout = QVBoxLayout(self._container)
        self._layout.setContentsMargins(PAGE_MARGIN, PAGE_MARGIN, PAGE_MARGIN, PAGE_MARGIN)
        self._layout.setSpacing(PAGE_SPACING)

        self._placeholder = QLabel(
            "Run an installation to see AI-powered suggestions here.\n\n"
            "When errors occur, recommended fixes appear immediately. "
            "Use Continue in AI Chat to ask follow-up questions."
        )
        self._placeholder.setWordWrap(True)
        self._placeholder.setStyleSheet(muted_stylesheet(palette) + " font-size: 11pt;")
        self._layout.addWidget(self._placeholder)
        self._layout.addStretch(1)

    def set_ai_diagnosis_status(self, status: str) -> None:
        """Update banner: idle | running | ready | unavailable."""
        if hasattr(self, "_ai_status_label"):
            labels = {
                "running": "AI diagnosis in progress…",
                "ready": "AI suggestions ready",
                "unavailable": "AI diagnosis unavailable — showing rule-based suggestions",
                "idle": "Waiting for installation data",
            }
            self._ai_status_label.setText(labels.get(status, status))

    def apply_run_result(
        self,
        result: AutomatedRunResult | None,
        *,
        slm_answer: str | None = None,
        slm_sources: list[str] | None = None,
        ai_status: str = "idle",
        slm_pending: bool = False,
    ) -> None:
        self._clear()
        if result is None:
            self._layout.addWidget(self._placeholder)
            self._layout.addStretch(1)
            return

        report = result.report
        p = self._palette
        has_errors = bool(report.errors) or bool(report.status.failure_reason)
        outcome = (report.status.installation_outcome or "").lower()
        failed = has_errors or outcome in {"failed", "failure", "error", "partial"}

        heading = QLabel("Troubleshooting")
        heading.setStyleSheet(heading_stylesheet(p, size_pt=16))
        sub = QLabel(
            f"Installer: <b>{report.status.installer.installer_name}</b>"
            f"  ·  Outcome: <b>{report.status.installation_outcome}</b>"
            f"  ·  {len(report.errors)} error(s)"
        )
        sub.setWordWrap(True)
        sub.setStyleSheet(body_stylesheet(p))
        self._layout.addWidget(heading)
        self._layout.addWidget(sub)

        if failed or slm_answer or slm_pending:
            self._layout.addWidget(
                self._build_ai_suggestions_card(
                    report,
                    slm_answer=slm_answer,
                    slm_sources=slm_sources,
                    ai_status=ai_status,
                    slm_pending=slm_pending,
                )
            )

        title0, icon0, sem0 = _DETAIL_SECTIONS[0]
        errors_text = "\n".join(
            f"• [{e.category}]  {e.code}: {e.message[:300]}"
            for e in report.errors[:25]
        ) or "No errors recorded in this session."
        self._layout.addWidget(self._expandable(title0, errors_text, icon=icon0, semantic=sem0))

        title1, icon1, sem1 = _DETAIL_SECTIONS[1]
        rag_lines: list[str] = []
        if slm_sources:
            rag_lines.append("Retrieved knowledge documents:")
            rag_lines.extend(f"  •  {src}" for src in slm_sources)
            rag_lines.append("")
        rag_lines.append(
            f"Event logs: {len(report.evidence.event_logs)}  ·  "
            f"Installer logs: {len(report.evidence.installer_log_files)}  ·  "
            f"Registry changes: {len(report.evidence.registry_changes)}"
        )
        if report.status.failure_reason:
            rag_lines.insert(0, f"Recorded failure reason:\n{report.status.failure_reason}\n")
        self._layout.addWidget(
            self._expandable(title1, "\n".join(rag_lines), icon=icon1, semantic=sem1)
        )

        if slm_answer and slm_answer.strip():
            title2, icon2, sem2 = _DETAIL_SECTIONS[2]
            fix_body = slm_answer.strip()
            sections = parse_slm_sections(fix_body)
            if sections:
                fix_body = "\n\n".join(f"{s.heading}\n{s.body}" for s in sections)
            self._layout.addWidget(
                self._expandable(title2, fix_body, icon=icon2, semantic=sem2, expanded=True)
            )

        self._layout.addStretch(1)

    def _build_ai_suggestions_card(
        self,
        report,
        *,
        slm_answer: str | None,
        slm_sources: list[str] | None,
        ai_status: str,
        slm_pending: bool = False,
    ) -> QFrame:
        p = self._palette
        card = QFrame()
        apply_card_style(card, p, object_name="aiSuggestCard")
        card.setStyleSheet(
            f"QFrame#aiSuggestCard {{"
            f" background: {p.surface};"
            f" border: 1px solid {p.border};"
            f" border-left: 4px solid {p.blue_600};"
            f" border-radius: 12px;"
            f"}}"
        )
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        hdr = QHBoxLayout()
        badge = QLabel("🤖")
        badge.setFixedSize(36, 36)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setStyleSheet(
            f"font-size: 16pt; background: {p.info_bg}; border-radius: 10px;"
        )
        title_col = QVBoxLayout()
        title_lbl = QLabel("AI suggestions")
        title_lbl.setStyleSheet(heading_stylesheet(p, size_pt=13))
        self._ai_status_label = QLabel()
        self.set_ai_diagnosis_status(ai_status)
        self._ai_status_label.setStyleSheet(muted_stylesheet(p))
        title_col.addWidget(title_lbl)
        title_col.addWidget(self._ai_status_label)
        hdr.addWidget(badge)
        hdr.addWidget(title_col, stretch=1)
        layout.addLayout(hdr)

        if slm_answer and slm_answer.strip():
            bundle = format_slm_diagnosis(slm_answer, slm_sources)
            detail = QLabel(bundle.full_text)
            detail.setWordWrap(True)
            detail.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            detail.setStyleSheet(body_stylesheet(p) + " padding: 4px 0 8px 0;")
            layout.addWidget(detail)

        suggestions = build_ai_suggestions(
            report,
            slm_answer=slm_answer,
            slm_pending=slm_pending and not (slm_answer and slm_answer.strip()),
        )
        for item in suggestions:
            row = QLabel(f"•  {item}")
            row.setWordWrap(True)
            row.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            row.setStyleSheet(body_stylesheet(p) + " padding-left: 4px;")
            layout.addWidget(row)

        if slm_sources:
            src_lbl = QLabel(
                "Sources: " + ", ".join(slm_sources[:3])
                + ("…" if len(slm_sources) > 3 else "")
            )
            src_lbl.setWordWrap(True)
            src_lbl.setStyleSheet(muted_stylesheet(p))
            layout.addWidget(src_lbl)

        actions = QHBoxLayout()
        actions.setSpacing(12)
        installer = report.status.installer.installer_name
        self._last_chat_prompt = (
            f"Help me fix the installation failure for {installer}. "
            f"What should I do step by step?"
        )
        chat_btn = hero_primary_button("Continue in AI Chat", p, parent=card)
        chat_btn.clicked.connect(lambda: self.open_ai_chat.emit(self._last_chat_prompt))
        summary_btn = hero_outline_button("Ask for a short summary", p, parent=card)
        summary_btn.clicked.connect(
            lambda: self.open_ai_chat.emit(
                f"Summarize the errors for {installer} in simple steps."
            )
        )
        actions.addWidget(chat_btn)
        actions.addWidget(summary_btn)
        actions.addStretch(1)
        layout.addLayout(actions)

        hint = QLabel(
            "Suggestions appear here automatically. Open AI Chat only when you want to type follow-up questions."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet(muted_stylesheet(p) + " font-size: 8.5pt;")
        layout.addWidget(hint)

        return card

    def _expandable(
        self,
        title: str,
        body: str,
        *,
        icon: str = "▸",
        semantic: str = "info",
        expanded: bool = False,
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
        icon_badge.setStyleSheet(f"font-size: 14pt; background: {icon_bg}; border-radius: 8px;")

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(heading_stylesheet(p, size_pt=11))

        toggle = QToolButton()
        toggle.setObjectName("tshootToggle")
        toggle.setCheckable(True)
        toggle.setChecked(expanded)
        toggle.setText("▾" if expanded else "▸")
        toggle.setStyleSheet(
            f"QToolButton#tshootToggle {{ color: {p.text_muted}; font-size: 13pt;"
            f" font-weight: 700; background: transparent; border: none; }}"
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
        body_lbl.setStyleSheet(body_stylesheet(p))
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
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
