"""Generate harness execution reports and summaries."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from failure_harness.models import HarnessEvent, HarnessRunReport, PhaseResult, RagValidationResult


class ReportGenerator:
    """Write test execution summary, timelines, and metrics."""

    def __init__(self, output_dir: Path) -> None:
        self._output_dir = output_dir.resolve()
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def write_report(self, report: HarnessRunReport) -> Path:
        json_path = self._output_dir / f"harness_report_{report.run_id}.json"
        json_path.write_text(
            report.model_dump_json(by_alias=True, indent=2),
            encoding="utf-8",
        )
        self._write_summary_markdown(report)
        self._write_metrics_csv(report)
        return json_path

    def _write_summary_markdown(self, report: HarnessRunReport) -> Path:
        md_path = self._output_dir / f"harness_summary_{report.run_id}.md"
        lines = [
            f"# Harness Run Summary — {report.run_id}",
            "",
            f"- **Scenario:** {report.scenario_id}",
            f"- **Started:** {report.started_at}",
            f"- **Completed:** {report.completed_at}",
            f"- **Overall Success:** {'Yes' if report.overall_success else 'No'}",
            "",
            "## Phase 1 — Smart Installer Setup",
            f"- Success: {report.phase1.success}",
            f"- Duration: {report.phase1.duration_seconds}s",
            "",
            "### Checks",
        ]
        for check in report.phase1.checks:
            status = "PASS" if check.get("passed") else "FAIL"
            lines.append(f"- [{status}] {check.get('name')}: {check.get('detail')}")

        lines.extend(
            [
                "",
                "## Phase 2 — Test Application Installation",
                f"- Success: {report.phase2.success}",
                f"- Duration: {report.phase2.duration_seconds}s",
                "",
            ]
        )
        for check in report.phase2.checks:
            status = "PASS" if check.get("passed") else "FAIL"
            lines.append(f"- [{status}] {check.get('name')}: {check.get('detail')}")

        if report.rag_validation:
            rag = report.rag_validation
            lines.extend(
                [
                    "",
                    "## RAG Validation",
                    f"- Success: {rag.success}",
                    f"- Relevance Score: {rag.relevance_score}",
                    f"- Matched Keywords: {', '.join(rag.matched_keywords) or 'none'}",
                    f"- Sources: {', '.join(rag.sources) or 'none'}",
                ]
            )

        if report.metrics:
            lines.extend(["", "## Metrics"])
            for key, value in report.metrics.items():
                lines.append(f"- **{key}:** {value}")

        md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return md_path

    def _write_metrics_csv(self, report: HarnessRunReport) -> Path:
        csv_path = self._output_dir / f"harness_metrics_{report.run_id}.csv"
        rows = [
            ("metric", "value"),
            ("run_id", report.run_id),
            ("scenario_id", report.scenario_id),
            ("overall_success", str(report.overall_success)),
            ("phase1_success", str(report.phase1.success)),
            ("phase2_success", str(report.phase2.success)),
            ("phase1_duration_seconds", str(report.phase1.duration_seconds)),
            ("phase2_duration_seconds", str(report.phase2.duration_seconds)),
        ]
        if report.rag_validation:
            rows.extend(
                [
                    ("rag_success", str(report.rag_validation.success)),
                    ("rag_relevance_score", str(report.rag_validation.relevance_score)),
                    ("rag_matched_keyword_count", str(len(report.rag_validation.matched_keywords))),
                ]
            )
        for key, value in report.metrics.items():
            rows.append((key, str(value)))

        with csv_path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerows(rows)
        return csv_path

    @staticmethod
    def build_timelines(
        events: list[HarnessEvent],
    ) -> tuple[list[HarnessEvent], list[HarnessEvent]]:
        failure_types = {"failure_injected", "failure_detected", "scenario_start", "scenario_complete"}
        recovery_types = {"recovery_attempt", "recovery_success", "recovery_skip", "retry_attempt"}

        failure_timeline = [e for e in events if e.event_type in failure_types or e.phase == "failure_injection"]
        recovery_timeline = [e for e in events if e.event_type in recovery_types or e.phase == "recovery"]
        return failure_timeline, recovery_timeline

    @staticmethod
    def compute_metrics(
        phase1: PhaseResult,
        phase2: PhaseResult,
        rag: RagValidationResult | None,
        total_failures_injected: int,
        detection_passed: bool,
    ) -> dict:
        phase1_pass = sum(1 for c in phase1.checks if c.get("passed"))
        phase2_pass = sum(1 for c in phase2.checks if c.get("passed"))
        return {
            "successRate": round(phase2_pass / max(len(phase2.checks), 1), 3),
            "recoverySuccessRate": 1.0 if phase2.success else 0.0,
            "failureClassificationAccuracy": 1.0 if detection_passed else 0.0,
            "recommendationAccuracy": rag.relevance_score if rag else 0.0,
            "failuresInjected": total_failures_injected,
            "phase1ChecksPassed": phase1_pass,
            "phase2ChecksPassed": phase2_pass,
        }
