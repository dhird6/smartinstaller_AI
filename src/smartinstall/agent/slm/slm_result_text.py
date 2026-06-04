"""Extract SLM diagnosis text from runner result objects."""

from __future__ import annotations

from typing import Any


def slm_text_from_result(result: Any) -> str:
    """Return normalized SLM answer text from SlmDiagnosisResult or similar objects."""
    for attr in ("output", "answer", "text", "content"):
        value = getattr(result, attr, None)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""
