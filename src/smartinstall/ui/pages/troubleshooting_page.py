"""Installation failure analysis workspace — professional expandable sections."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
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
from smartinstall.ui.services.slm_response_parser import parse_slm_sections
from smartinstall.ui.theme.cctech_theme import CCTechPalette, body_stylesheet, heading_stylesheet, muted_stylesheet

# (title, icon, accent, description)
_SECTIONS: tuple[tuple[str, str, str], ...] = (
    ("Error logs & detection",                 "🔍", "error"),
    ("Root cause analysis",                    "🧠", "warning"),
    ("Similar incidents  ·  RAG retrieval",    "📚", "info"),
    ("AI recommendations & resolution steps",  "🤖", "success"),
)


class TroubleshootingPage(QScrollArea):
    """Expandable failure-analysis cards driven by run result and SLM output."""

    def __init__(self, palette: CCTechPalette, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._palette = palette
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
            "Run an installation to populate failure analysis, root cause diagnosis, "
            "vector-retrieved knowledge, and AI recommendations."
        )
        self._placeholder.setWordWrap(True)
        self._placeholder.setStyleSheet(muted_stylesheet(palette) + " font-size: 11pt;")
        self._layout.addWidget(self._placeholder)
        self._layout.addStretch(1)

    # ── Public API ─────────────────────────────────────────────────────────

    def apply_run_result(
        self,
        result: AutomatedRunResult | None,
        *,
        slm_answer: str | None = None,
        slm_sources: list[str] | None = None,
    ) -> None:
        self._clear()
        if result is None:
            self._layout.addWidget(self._placeholder)
            self._layout.addStretch(1)
            return

        report = result.report
        p = self._palette

        # Add a page heading
        heading = QLabel("Failure Analysis")
        heading.setStyleSheet(heading_stylesheet(p, size_pt=16))
        sub = QLabel(
            f"Installer: <b>{report.status.installer.installer_name}</b>"
            f"  ·  Outcome: <b>{report.status.installation_outcome}</b>"
            f"  ·  {len(report.errors)} error(s) detected"
        )
        sub.setWordWrap(True)
        sub.setStyleSheet(body_stylesheet(p))
        self._layout.addWidget(heading)
        self._layout.addWidget(sub)
        self._layout.addSpacing(4)

        # Section 0 — errors
        title0, icon0, sem0 = _SECTIONS[0]
        errors_text = "\n".join(
            f"• [{e.category}]  {e.code}: {e.message[:300]}"
            for e in report.errors[:25]
        ) or "No errors recorded in this session."
        self._layout.addWidget(self._expandable(title0, errors_text, icon=icon0, semantic=sem0))

        # Section 1 — root cause
        title1, icon1, sem1 = _SECTIONS[1]
        root_cause = (
            report.status.failure_reason
            or "No explicit failure reason recorded — see AI analysis below."
        )
        self._layout.addWidget(self._expandable(title1, root_cause, icon=icon1, semantic=sem1))

        # Section 2 — RAG sources
        title2, icon2, sem2 = _SECTIONS[2]
        rag_lines: list[str] = []
        if slm_sources:
            rag_lines.append("Retrieved knowledge documents:\n")
            rag_lines.extend(f"  •  {src}" for src in slm_sources)
            rag_lines.append("")
        rag_lines.append(
            f"Evidence collected:  {len(report.evidence.event_logs)} event log(s)  ·  "
            f"{len(report.evidence.installer_log_files)} installer log(s)  ·  "
            f"{len(report.evidence.registry_changes)} registry change(s)"
        )
        self._layout.addWidget(
            self._expandable(title2, "\n".join(rag_lines), icon=icon2, semantic=sem2)
        )

        # Section 3 — AI fix
        title3, icon3, sem3 = _SECTIONS[3]
        fix_body = slm_answer or "AI diagnosis pending — ensure Ollama is running locally."
        sections = parse_slm_sections(fix_body)
        if sections:
            fix_body = "\n\n".join(f"{s.heading}\n{s.body}" for s in sections)
        self._layout.addWidget(self._expandable(title3, fix_body, icon=icon3, semantic=sem3))

        self._layout.addStretch(1)

    # ── Card builder ────────────────────────────────────────────────────────

    def _expandable(
        self,
        title: str,
        body: str,
        *,
        icon: str = "▸",
        semantic: str = "info",
    ) -> QFrame:
        p = self._palette
        accent_map = {
            "error":   p.error,
            "warning": p.warning,
            "info":    p.info,
            "success": p.success,
        }
        bg_map = {
            "error":   p.error_bg,
            "warning": p.warning_bg,
            "info":    p.info_bg,
            "success": p.success_bg,
        }
        accent = accent_map.get(semantic, p.info)
        icon_bg = bg_map.get(semantic, p.info_bg)

        card = QFrame()
        apply_card_style(card, p, object_name="tshootCard")

        root_layout = QVBoxLayout(card)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ── Header ──────────────────────────────────────────────────────────
        hdr = QFrame()
        hdr.setObjectName("tshootHdr")
        hdr_layout = QHBoxLayout(hdr)
        hdr_layout.setContentsMargins(16, 14, 16, 14)
        hdr_layout.setSpacing(12)

        # Icon badge
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
        toggle.setChecked(True)
        toggle.setText("▾")
        toggle.setStyleSheet(
            f"QToolButton#tshootToggle {{ color: {p.text_muted}; font-size: 13pt;"
            f" font-weight: 700; background: transparent; border: none; padding: 0; }}"
            f"QToolButton#tshootToggle:checked {{ color: {accent}; }}"
        )

        hdr_layout.addWidget(icon_badge)
        hdr_layout.addWidget(title_lbl, stretch=1)
        hdr_layout.addWidget(toggle, alignment=Qt.AlignmentFlag.AlignVCenter)
        root_layout.addWidget(hdr)

        # ── Separator ────────────────────────────────────────────────────────
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {p.border}; margin: 0 16px;")
        root_layout.addWidget(sep)

        # ── Body ─────────────────────────────────────────────────────────────
        body_widget = QWidget()
        body_layout = QVBoxLayout(body_widget)
        body_layout.setContentsMargins(16, 14, 16, 18)
        body_lbl = QLabel(body)
        body_lbl.setWordWrap(True)
        body_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        body_lbl.setStyleSheet(body_stylesheet(p))
        body_layout.addWidget(body_lbl)
        root_layout.addWidget(body_widget)

        # Toggle logic
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
