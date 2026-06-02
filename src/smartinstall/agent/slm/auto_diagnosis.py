"""Automatic SLM diagnosis runner for SmartInstall reports."""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class SlmDiagnosisResult:
    success: bool
    return_code: int
    report_path: Path
    output: str
    command: list[str]
    error: str | None = None


def run_slm_for_report(
    report_path: Path,
    *,
    timeout_seconds: int = 300,
) -> SlmDiagnosisResult:
    """
    Validate SmartInstall JSON and invoke local SLM (`rag.py --report ...`).

    Security note:
    - Uses subprocess argument list (no shell) to avoid command injection.
    - Accepts only an existing report path and validates JSON before invocation.
    """
    resolved_report = report_path.resolve()
    if not resolved_report.is_file():
        return SlmDiagnosisResult(
            success=False,
            return_code=1,
            report_path=resolved_report,
            output="",
            command=[],
            error=f"Report JSON not found: {resolved_report}",
        )

    try:
        json.loads(resolved_report.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return SlmDiagnosisResult(
            success=False,
            return_code=1,
            report_path=resolved_report,
            output="",
            command=[],
            error=f"Invalid report JSON: {exc}",
        )

    project_root = Path(__file__).resolve().parents[4]
    rag_script = project_root / "rag.py"
    if not rag_script.is_file():
        return SlmDiagnosisResult(
            success=False,
            return_code=1,
            report_path=resolved_report,
            output="",
            command=[],
            error=f"SLM script missing: {rag_script}",
        )

    command = [sys.executable, str(rag_script), "--report", str(resolved_report)]
    try:
        completed = subprocess.run(
            command,
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            shell=False,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return SlmDiagnosisResult(
            success=False,
            return_code=1,
            report_path=resolved_report,
            output="",
            command=command,
            error=f"Failed to run SLM diagnosis: {exc}",
        )

    merged_output = "\n".join(
        part.strip() for part in (completed.stdout, completed.stderr) if part and part.strip()
    )
    return SlmDiagnosisResult(
        success=completed.returncode == 0,
        return_code=completed.returncode,
        report_path=resolved_report,
        output=merged_output,
        command=command,
        error=None if completed.returncode == 0 else "SLM diagnosis returned non-zero exit code",
    )
