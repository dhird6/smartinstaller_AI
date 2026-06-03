"""Tests for SLM response section parser."""

from smartinstall.ui.services.slm_response_parser import parse_slm_sections


def test_parse_structured_slm_sections() -> None:
    answer = """
1) Error Summary
Exit code 1603 during MSI install.

2) Root Cause
Administrator privileges are required.

3) Recommended Fix
1. Re-run installer as Administrator.
2. Verify UAC prompt is accepted.
"""
    sections = parse_slm_sections(answer)
    headings = [section.heading for section in sections]
    assert "Error Summary" in headings
    assert "Root Cause" in headings
    assert "Recommended Fix" in headings
