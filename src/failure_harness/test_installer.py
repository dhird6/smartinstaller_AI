"""Test Application — simulates a real Windows installer with injectable failures."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from failure_harness.engine import FailureInjectionEngine
from failure_harness.models import ScenarioConfig
from failure_harness.scenario_manager import ScenarioManager


def _print_install_progress(step: int, total: int, message: str) -> None:
    print(f"[{step}/{total}] {message}", flush=True)


def run_install_simulation(scenario: ScenarioConfig, *, quiet: bool = False) -> int:
    """Simulate installation steps then inject configured failures."""
    total_steps = 5
    if not quiet:
        _print_install_progress(1, total_steps, "Initializing TestApp Setup v1.0.0...")
        time.sleep(0.3)
        _print_install_progress(2, total_steps, "Checking system prerequisites...")
        time.sleep(0.3)
        _print_install_progress(3, total_steps, "Preparing installation directory...")
        time.sleep(0.2)

    engine = FailureInjectionEngine(random_seed=scenario.random_seed)
    result = engine.execute_scenario(scenario)

    if not quiet:
        _print_install_progress(4, total_steps, "Installing application components...")

    for injection in result.injections:
        for line in injection.stdout_lines:
            print(line, flush=True)
        for line in injection.stderr_lines:
            print(line, file=sys.stderr, flush=True)

    if not quiet:
        if result.final_exit_code == 0:
            _print_install_progress(5, total_steps, "Installation completed successfully.")
        else:
            _print_install_progress(5, total_steps, f"Installation failed (exit code {result.final_exit_code}).")

    return result.final_exit_code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="TestApp Installer — failure injection simulator for Smart Installer validation",
    )
    parser.add_argument(
        "--scenario",
        type=str,
        help="Scenario ID or path to scenario JSON file",
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="Path to harness.config.json (for scenario directory resolution)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress progress output (failures still emitted)",
    )
    parser.add_argument(
        "--list-scenarios",
        action="store_true",
        help="List available scenarios and exit",
    )
    args = parser.parse_args(argv)

    manager = ScenarioManager.from_harness_config(args.config)

    if args.list_scenarios:
        for sid in manager.list_scenario_ids():
            sc = manager.load_scenario(sid)
            print(f"  {sid}: {sc.name}")
        return 0

    if not args.scenario:
        parser.error("Provide --scenario <id_or_path> or --list-scenarios")

    scenario_path = Path(args.scenario)
    if scenario_path.is_file():
        scenario = ScenarioConfig.model_validate_json(scenario_path.read_text(encoding="utf-8"))
    else:
        scenario = manager.load_scenario(args.scenario)

    return run_install_simulation(scenario, quiet=args.quiet)


if __name__ == "__main__":
    raise SystemExit(main())
