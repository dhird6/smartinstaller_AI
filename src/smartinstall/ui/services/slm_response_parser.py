"""Parse structured SLM output into troubleshooting and chat sections."""

from __future__ import annotations

import re
from dataclasses import dataclass

from smartinstall.ui.models.chat_message import ChatSection

_HEADINGS = ("Error Summary", "Root Cause", "Recommended Fix")
_HEADING_RE = re.compile(
    r"(?im)^\s*(?:#{1,3}\s*)?"
    r"(?:\d+[\).]\s*)?"
    r"(Error Summary|Root Cause|Recommended(?:\s+Fix)?(?:\s*\([^)]*\))?)"
    r"\s*:?\s*$"
)


@dataclass(frozen=True, slots=True)
class SlmPartition:
    """Normalized SLM fields for the Troubleshooting workspace."""

    error_summary: str
    root_cause: str
    recommended_fix: str
    full_text: str
    structured: bool


def parse_slm_sections(answer: str) -> list[ChatSection]:
    """Extract Error / Root Cause / Fix sections when present."""
    partition = partition_slm_answer(answer)
    if not partition.structured:
        return []

    sections: list[ChatSection] = []
    if partition.error_summary:
        sections.append(ChatSection(heading="Error Summary", body=partition.error_summary))
    if partition.root_cause:
        sections.append(ChatSection(heading="Root Cause", body=partition.root_cause))
    if partition.recommended_fix:
        sections.append(
            ChatSection(heading="Recommended Fix", body=partition.recommended_fix)
        )
    return sections


def partition_slm_answer(answer: str) -> SlmPartition:
    """Split SLM output into troubleshooting fields; always keeps full_text."""
    text = answer.strip()
    if not text:
        return SlmPartition("", "", "", "", structured=False)

    matches = list(_HEADING_RE.finditer(text))
    if len(matches) < 2:
        return SlmPartition(
            error_summary="",
            root_cause="",
            recommended_fix="",
            full_text=text,
            structured=False,
        )

    buckets: dict[str, str] = {}
    for index, match in enumerate(matches):
        heading_raw = match.group(1)
        heading = _normalize_heading(heading_raw)
        body_start = match.end()
        body_end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[body_start:body_end].strip()
        if body:
            buckets[heading] = body

    return SlmPartition(
        error_summary=buckets.get("Error Summary", ""),
        root_cause=buckets.get("Root Cause", ""),
        recommended_fix=buckets.get("Recommended Fix", ""),
        full_text=text,
        structured=True,
    )


def _normalize_heading(raw: str) -> str:
    lowered = raw.lower()
    if "error" in lowered and "summary" in lowered:
        return "Error Summary"
    if "root" in lowered and "cause" in lowered:
        return "Root Cause"
    if "recommended" in lowered or "fix" in lowered:
        return "Recommended Fix"
    for heading in _HEADINGS:
        if heading.lower() in lowered:
            return heading
    return raw.strip()
