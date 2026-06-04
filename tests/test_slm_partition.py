"""Tests for SLM answer partitioning."""

from smartinstall.ui.services.slm_response_parser import partition_slm_answer, parse_slm_sections


def test_partition_structured_answer() -> None:
    answer = """
1) Error Summary
Exit code 1603.

2) Root Cause
Missing VC++ runtime.

3) Recommended Fix
Install VC++ redistributable and retry.
"""
    part = partition_slm_answer(answer)
    assert part.structured is True
    assert "1603" in part.error_summary
    assert "VC++" in part.root_cause
    assert "redistributable" in part.recommended_fix
    assert len(parse_slm_sections(answer)) == 3


def test_partition_unstructured_keeps_full_text() -> None:
    answer = "The installer failed because of low disk space. Free space and retry."
    part = partition_slm_answer(answer)
    assert part.structured is False
    assert part.full_text == answer
    assert part.recommended_fix == ""
