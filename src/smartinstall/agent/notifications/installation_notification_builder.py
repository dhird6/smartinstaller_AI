"""Build single combined Windows toast bodies for installation events."""

from __future__ import annotations

from smartinstall.core.models.unified_report import ReportErrorEntry

_MONITORING_STARTED_BODY = (
    "Smart Installer has detected an active software installation and is monitoring "
    "the installation process in real time to identify and resolve potential issues."
)


def monitoring_started_message(installer_name: str) -> str:
    if installer_name:
        return f"{_MONITORING_STARTED_BODY}\n\nInstaller: {installer_name}"
    return _MONITORING_STARTED_BODY


def format_error_list(errors: list[ReportErrorEntry], *, max_items: int = 6) -> str:
    if not errors:
        return ""
    lines: list[str] = []
    for error in errors[:max_items]:
        lines.append(f"• [{error.code}] {error.message[:120]}")
    if len(errors) > max_items:
        lines.append(f"• … and {len(errors) - max_items} more issue(s)")
    return "\n".join(lines)


def format_slm_completion_toast(
    *,
    installer_name: str,
    slm_answer: str,
    errors: list[ReportErrorEntry] | None = None,
) -> tuple[str, str]:
    """Return (title, message) for one combined AI troubleshooting toast."""
    title = "Smart Installer — AI Troubleshooting"
    if installer_name:
        title = f"AI Troubleshooting — {installer_name}"

    parts: list[str] = []
    if errors:
        error_block = format_error_list(errors)
        if error_block:
            parts.append(f"Issues detected:\n{error_block}")

    excerpt = _slm_excerpt(slm_answer)
    if excerpt:
        parts.append(f"AI recommendation:\n{excerpt}")

    if not parts:
        parts.append("AI troubleshooting analysis is ready. Open Smart Installer for details.")

    return title, "\n\n".join(parts)[:480]


def _slm_excerpt(answer: str) -> str:
    lines = [line.strip() for line in answer.splitlines() if line.strip()]
    if not lines:
        return ""
    return " ".join(lines[:5])[:400]
