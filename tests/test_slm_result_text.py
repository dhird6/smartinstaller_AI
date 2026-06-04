"""Tests for SLM result text extraction."""

from smartinstall.agent.slm.auto_diagnosis import SlmDiagnosisResult
from smartinstall.agent.slm.slm_result_text import slm_text_from_result


def test_slm_text_from_output() -> None:
    result = SlmDiagnosisResult(
        success=True,
        return_code=0,
        report_path=__file__,  # type: ignore[arg-type]
        output="Error Summary: disk full",
        sources=["doc1"],
    )
    assert slm_text_from_result(result) == "Error Summary: disk full"
    assert result.answer == "Error Summary: disk full"
