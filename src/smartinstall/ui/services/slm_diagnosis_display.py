"""Format SLM diagnosis for Monitoring, Troubleshooting, and Windows toasts."""

from __future__ import annotations

from dataclasses import dataclass

from smartinstall.ui.services.slm_response_parser import parse_slm_sections

_MONITORING_DETECTED_MESSAGE = (
    "Smart Installer has detected an active software installation and is monitoring "
    "the installation process in real time to identify and resolve potential issues."
)


@dataclass(slots=True)
class SlmDisplayBundle:
    """Structured SLM output for UI surfaces."""

    summary: str
    full_text: str
    sections: list[tuple[str, str]]
    notification_body: str


def monitoring_detected_message(installer_name: str) -> str:
    return f"{_MONITORING_DETECTED_MESSAGE}\n\nInstaller: {installer_name}"


def format_slm_diagnosis(answer: str, sources: list[str] | None = None) -> SlmDisplayBundle:
    text = answer.strip()
    sections = parse_slm_sections(text)
    section_pairs = [(s.heading, s.body) for s in sections] if sections else []

    if section_pairs:
        full_parts = [f"{heading}\n{body}" for heading, body in section_pairs]
        full_text = "\n\n".join(full_parts)
        summary_bits = [f"{heading}: {body.splitlines()[0][:120]}" for heading, body in section_pairs[:3]]
        summary = " · ".join(summary_bits)
    else:
        full_text = text
        summary = text.splitlines()[0][:200] if text else "AI analysis complete."

    if sources:
        source_line = "Sources: " + ", ".join(sources[:3])
        if len(sources) > 3:
            source_line += "…"
        full_text = f"{full_text}\n\n{source_line}" if full_text else source_line

    notification_body = _build_notification_body(section_pairs, text)
    return SlmDisplayBundle(
        summary=summary,
        full_text=full_text,
        sections=section_pairs,
        notification_body=notification_body,
    )


def _build_notification_body(section_pairs: list[tuple[str, str]], fallback: str) -> str:
    if section_pairs:
        parts: list[str] = []
        for heading, body in section_pairs[:3]:
            first = body.splitlines()[0].strip() if body else ""
            if first:
                parts.append(f"{heading}: {first[:100]}")
        return "\n".join(parts)[:480]
    return fallback[:480]
