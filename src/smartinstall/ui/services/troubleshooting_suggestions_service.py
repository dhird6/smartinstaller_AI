"""Build actionable AI suggestion bullets for the Troubleshooting page."""

from __future__ import annotations

import re

from smartinstall.core.models.unified_report import UnifiedInstallationReport
from smartinstall.ui.services.slm_response_parser import parse_slm_sections

_CODE_HINTS: dict[str, str] = {
    "0x80070643": "Install Microsoft Visual C++ Redistributable (x64), then rerun the installer.",
    "1603": "Fatal MSI error — check verbose MSI log, free disk space, and run as administrator.",
    "1618": "Another installation is in progress. Wait for it to finish, then retry.",
    "1619": "The MSI package could not be opened. Re-download the installer.",
    "0x80070005": "Access denied — right-click the installer and choose Run as administrator.",
    "0x80070002": "A required file or .NET component is missing. Install prerequisites and retry.",
    "DISK_FULL": "Free disk space on the system drive, then run the installer again.",
}


def build_ai_suggestions(
    report: UnifiedInstallationReport,
    *,
    slm_answer: str | None = None,
    slm_pending: bool = False,
) -> list[str]:
    """Return ordered suggestion lines for the Troubleshooting hero card (SLM-first)."""
    if slm_answer and slm_answer.strip():
        from_slm = _suggestions_from_slm(slm_answer.strip())
        if from_slm:
            return from_slm

    if slm_pending:
        return [
            "SLM analysis is running — AI recommendations will replace this message when complete.",
            "Check the AI troubleshooting analysis panel in Live Monitoring for the full response.",
        ]

    if report.errors:
        return [
            "SLM recommendations are not available yet. Ensure Ollama is running and autoRunSlm is enabled.",
            *[
                f"[{error.code}] {error.message[:160]}"
                for error in report.errors[:4]
            ],
        ]

    return [
        "No SLM analysis is available for this session. Run a monitored install with Ollama active.",
    ]


def _suggestions_from_slm(answer: str) -> list[str]:
    sections = parse_slm_sections(answer)
    if sections:
        items: list[str] = []
        for section in sections:
            first_line = section.body.split("\n", 1)[0].strip()
            if len(first_line) > 220:
                first_line = first_line[:217] + "…"
            items.append(f"{section.heading}: {first_line}")
        return items

    lines = [line.strip() for line in answer.splitlines() if line.strip()]
    numbered = [line for line in lines if re.match(r"^[\d\-\*•]", line)]
    if numbered:
        return numbered[:8]
    if lines:
        return lines[:6]
    return [answer[:400]]


def _test_suggested_fix(raw_excerpt: str | None) -> str | None:
    if not raw_excerpt or not raw_excerpt.startswith("[TEST]"):
        return None
    fix = raw_excerpt.removeprefix("[TEST]").strip()
    return fix or None


def _hint_for_code(code: str) -> str | None:
    if not code:
        return None
    upper = code.upper()
    if upper in _CODE_HINTS:
        return _CODE_HINTS[upper]
    for key, hint in _CODE_HINTS.items():
        if key in upper:
            return hint
    return None
