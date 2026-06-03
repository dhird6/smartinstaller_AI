"""Tests for structured chat formatter output."""

from smartinstall.ui.services.chat_formatter import ChatFormatter


def test_slm_diagnosis_structured_sections() -> None:
    answer = (
        "1) Error Summary\nNetwork failure.\n\n"
        "2) Root Cause\nNo internet connectivity.\n\n"
        "3) Recommended Fix\nEnable network adapter."
    )
    message = ChatFormatter.slm_diagnosis(answer, ["proxy_issue.md"])
    assert len(message.sections) >= 3
    assert message.sections[0].heading == "Error Summary"
