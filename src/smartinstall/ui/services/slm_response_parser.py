"""Parse structured SLM output into chat sections."""

from __future__ import annotations

import re

from smartinstall.ui.models.chat_message import ChatSection

_HEADINGS = ("Error Summary", "Root Cause", "Recommended Fix")
_HEADING_RE = re.compile(
    r"(?im)^\s*(?:\d+\)\s*)?(Error Summary|Root Cause|Recommended Fix(?:\s*\([^)]*\))?)\s*:?\s*$"
)


def parse_slm_sections(answer: str) -> list[ChatSection]:
    """Extract Error / Root Cause / Fix sections when present."""
    text = answer.strip()
    if not text:
        return []

    matches = list(_HEADING_RE.finditer(text))
    if len(matches) < 2:
        return []

    sections: list[ChatSection] = []
    for index, match in enumerate(matches):
        heading_raw = match.group(1)
        heading = _normalize_heading(heading_raw)
        body_start = match.end()
        body_end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[body_start:body_end].strip()
        if body:
            sections.append(ChatSection(heading=heading, body=body))
    return sections


def _normalize_heading(raw: str) -> str:
    lowered = raw.lower()
    for heading in _HEADINGS:
        if heading.lower() in lowered:
            return heading
    return raw.strip()
