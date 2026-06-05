"""AI suggestions, troubleshooting hints, and error analysis for live monitoring."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

from smartinstall.ui.components.ui_card import section_card
from smartinstall.ui.services.slm_response_parser import SlmPartition, partition_slm_answer
from smartinstall.ui.theme.cctech_theme import CCTechPalette, body_stylesheet, heading_stylesheet, muted_stylesheet

_WAITING_AI = "Waiting for installation events…"
_WAITING_TROUBLESHOOT = "Monitoring installation — known issues will appear here when detected."
_WAITING_ANALYSIS = "Error root-cause analysis will appear when issues are detected."


class MonitoringAssistancePanel(QWidget):
    """Full-width AI assistance block below live monitoring (stacked vertically)."""

    def __init__(self, palette: CCTechPalette, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._palette = palette
        self._troubleshooting_items: list[tuple[str, str]] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # Troubleshooting and analysis first; AI suggestions last (below).
        self._trouble_body = self._section("Troubleshooting", _WAITING_TROUBLESHOOT)
        self._analysis_body = self._section("Error Analysis", _WAITING_ANALYSIS)
        self._ai_body = self._section("AI Suggestions", _WAITING_AI)

        layout.addWidget(self._trouble_body)
        layout.addWidget(self._analysis_body)
        layout.addWidget(self._ai_body)

    def _section(self, title: str, initial: str) -> QFrame:
        p = self._palette
        card, outer = section_card(p, object_name="assistCard")
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(heading_stylesheet(p, size_pt=11))
        outer.addWidget(title_lbl)
        body = QLabel(initial)
        body.setWordWrap(True)
        body.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        body.setStyleSheet(body_stylesheet(p) + " font-size: 10pt;")
        body.setObjectName(f"assist_{title.replace(' ', '_')}")
        outer.addWidget(body)
        if title == "AI Suggestions":
            self._ai_label = body
        elif title == "Troubleshooting":
            self._trouble_label = body
        else:
            self._analysis_label = body
        return card

    def reset_for_new_install(self, *, installer_name: str = "") -> None:
        self._troubleshooting_items.clear()
        waiting = (
            f"Waiting for installation events for {installer_name}…"
            if installer_name
            else _WAITING_AI
        )
        self._ai_label.setText(waiting)
        self._trouble_label.setText(_WAITING_TROUBLESHOOT)
        self._analysis_label.setText(_WAITING_ANALYSIS)

    def set_install_success(self, installer_name: str) -> None:
        """Successful install with no actionable errors — do not mention Ollama."""
        self._ai_label.setText(
            f"{installer_name} completed successfully.\n"
            "No installer issues detected — AI troubleshooting was not required."
        )
        self._trouble_label.setText("No issues found for this installation.")
        self._analysis_label.setText("No errors to analyze.")

    def set_slm_running(self, *, installer_name: str = "") -> None:
        product = installer_name or "the monitored installer"
        self._analysis_label.setText(f"Running root-cause analysis for {product}…")
        self._ai_label.setText(
            f"Analyzing {product} installation logs…\n"
            "Retrieving similar incidents and generating fix steps."
        )

    def apply_slm(self, answer: str, *, confidence: float | None = None) -> None:
        slm = partition_slm_answer(answer)
        self._apply_slm_partition(slm, confidence=confidence)

    def _apply_slm_partition(self, slm: SlmPartition, *, confidence: float | None = None) -> None:
        p = self._palette
        if not slm.full_text:
            self._ai_label.setText(
                "No AI recommendations for this installation yet.\n"
                "Suggestions appear when the monitored installer reports actionable errors."
            )
            return

        lines: list[str] = []
        if slm.error_summary:
            lines.append(f"<b>Detected Issue</b><br/>{slm.error_summary}")
        elif slm.full_text and not slm.structured:
            lines.append(f"<b>Detected Issue</b><br/>{slm.full_text[:400]}")

        if slm.root_cause:
            lines.append(f"<br/><b>Possible Cause</b><br/>{slm.root_cause}")

        if slm.recommended_fix:
            lines.append(f"<br/><b>Recommended Fix</b><br/>{slm.recommended_fix}")
        elif slm.structured:
            lines.append("<br/><b>Recommended Fix</b><br/>See full AI response in Troubleshooting.")

        if confidence is not None:
            lines.append(f"<br/><b>Confidence Score</b><br/>{int(confidence * 100)}%")

        self._ai_label.setTextFormat(Qt.TextFormat.RichText)
        self._ai_label.setText("".join(lines) if lines else slm.full_text)
        self._ai_label.setStyleSheet(body_stylesheet(p) + " font-size: 10pt;")

        analysis = slm.root_cause or slm.error_summary or slm.full_text[:600]
        self._analysis_label.setText(analysis)

    def add_troubleshooting_hint(self, issue: str, action: str) -> None:
        key = (issue.strip(), action.strip())
        if key in self._troubleshooting_items:
            return
        self._troubleshooting_items.append(key)
        self._render_troubleshooting()

    def _render_troubleshooting(self) -> None:
        if not self._troubleshooting_items:
            self._trouble_label.setText(_WAITING_TROUBLESHOOT)
            return
        blocks: list[str] = []
        for issue, action in self._troubleshooting_items[-8:]:
            blocks.append(f"<b>Issue Found:</b> {issue}<br/><b>Suggested Action:</b> {action}")
        self._trouble_label.setTextFormat(Qt.TextFormat.RichText)
        self._trouble_label.setText("<br/><br/>".join(blocks))

    def apply_errors_from_report(self, errors: list[object]) -> None:
        for err in errors[:12]:
            code = str(getattr(err, "code", "") or "ERROR")
            message = str(getattr(err, "message", "") or "")
            self.add_troubleshooting_hint(
                f"{code}: {message[:200]}",
                _heuristic_fix(message),
            )


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
