"""Console entry point for failure-harness script."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from failure_harness.orchestrator import HarnessOrchestrator, load_harness_config
from failure_harness.scenario_manager import ScenarioManager


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Smart Installer Failure Injection & RAG Validation Test Harness",
    )
    parser.add_argument("--config", type=Path, help="Path to harness.config.json")
    parser.add_argument("--scenario", type=str, help="Scenario ID to run (default from config)")
    parser.add_argument("--list-scenarios", action="store_true", help="List available scenarios")
    parser.add_argument("--run-all", action="store_true", help="Run all scenarios sequentially")
    parser.add_argument("--phase1-only", action="store_true", help="Run Phase 1 health checks only")
    args = parser.parse_args(argv)

    config = load_harness_config(args.config)

    if args.list_scenarios:
        manager = ScenarioManager.from_harness_config(args.config)
        print("Available scenarios:")
        for sid in manager.list_scenario_ids():
            sc = manager.load_scenario(sid)
            desc = sc.description[:80] if sc.description else ""
            print(f"  {sid}: {sc.name} — {desc}")
        return 0

    if args.phase1_only:
        from failure_harness.health_checker import SmartInstallerHealthChecker

        result = SmartInstallerHealthChecker().run_phase1(config)
        print(json.dumps(result.model_dump(by_alias=True), indent=2))
        return 0 if result.success else 1

    orchestrator = HarnessOrchestrator(config)

    if args.run_all:
        manager = ScenarioManager.from_harness_config(args.config)
        failures = 0
        for sid in manager.list_scenario_ids():
            print(f"\n=== Running scenario: {sid} ===")
            report = orchestrator.run(sid)
            if not report.overall_success:
                failures += 1
            print(f"Result: {'PASS' if report.overall_success else 'FAIL'}")
        return 0 if failures == 0 else 1

    report = orchestrator.run(args.scenario)
    print("\n### HARNESS RUN COMPLETE ###\n")
    print(f"Run ID:       {report.run_id}")
    print(f"Scenario:     {report.scenario_id}")
    print(f"Overall:      {'PASS' if report.overall_success else 'FAIL'}")
    print(f"Phase 1:      {'PASS' if report.phase1.success else 'FAIL'}")
    print(f"Phase 2:      {'PASS' if report.phase2.success else 'FAIL'}")
    if report.rag_validation:
        print(f"RAG Score:    {report.rag_validation.relevance_score}")
    if report.smart_install_report_path:
        print(f"SI Report:    {report.smart_install_report_path}")
    print(f"Harness Report: failure_harness/artifacts/harness_report_{report.run_id}.json")
    return 0 if report.overall_success else 1


if __name__ == "__main__":
    raise SystemExit(main())
