"""Test Application — simulates a real Windows installer with injectable failures."""

from __future__ import annotations

import argparse
import sys
import time
from collections.abc import Callable
from pathlib import Path

from failure_harness.engine import FailureInjectionEngine
from failure_harness.models import ScenarioConfig
from failure_harness.scenario_manager import ScenarioManager


def _emit_step(
    step: int,
    total: int,
    message: str,
    *,
    quiet: bool,
    on_step: Callable[[int, int, str], None] | None,
) -> None:
    if not quiet:
        print(f"[{step}/{total}] {message}", flush=True)
    if on_step is not None:
        on_step(step, total, message)


def _emit_log(
    message: str,
    *,
    quiet: bool,
    is_error: bool = False,
    on_log: Callable[[str], None] | None = None,
) -> None:
    if not quiet:
        stream = sys.stderr if is_error else sys.stdout
        print(message, file=stream, flush=True)
    if on_log is not None:
        on_log(message)


def run_install_simulation(
    scenario: ScenarioConfig,
    *,
    quiet: bool = False,
    on_step: Callable[[int, int, str], None] | None = None,
    on_log: Callable[[str, bool], None] | None = None,
) -> int:
    """Simulate installation steps then inject configured failures."""
    total_steps = 5

    def log_fn(message: str, *, is_error: bool = False) -> None:
        if on_log is not None:
            on_log(message, is_error)
        else:
            _emit_log(message, quiet=quiet, is_error=is_error)

    _emit_step(1, total_steps, "Initializing TestApp Setup v1.0.0...", quiet=quiet, on_step=on_step)
    time.sleep(0.35)
    _emit_step(2, total_steps, "Checking system prerequisites...", quiet=quiet, on_step=on_step)
    time.sleep(0.35)
    _emit_step(3, total_steps, "Preparing installation directory...", quiet=quiet, on_step=on_step)
    time.sleep(0.25)

    engine = FailureInjectionEngine(random_seed=scenario.random_seed)
    result = engine.execute_scenario(scenario)

    _emit_step(4, total_steps, "Installing application components...", quiet=quiet, on_step=on_step)

    for injection in result.injections:
        for line in injection.stdout_lines:
            log_fn(line, is_error=False)
        for line in injection.stderr_lines:
            log_fn(line, is_error=True)

    if result.final_exit_code == 0:
        _emit_step(5, total_steps, "Installation completed successfully.", quiet=quiet, on_step=on_step)
    else:
        _emit_step(
            5,
            total_steps,
            f"Installation failed (exit code {result.final_exit_code}).",
            quiet=quiet,
            on_step=on_step,
        )

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
        "--console",
        action="store_true",
        help="Use console output instead of the graphical installer window",
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

    if args.quiet or args.console:
        return run_install_simulation(scenario, quiet=args.quiet)

    from failure_harness.installer_gui import run_installer_gui

    return run_installer_gui(scenario)


if __name__ == "__main__":
    raise SystemExit(main())
