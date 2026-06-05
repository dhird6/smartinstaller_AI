"""Tests for TestApp installer simulation."""

from failure_harness.scenario_manager import ScenarioManager
from failure_harness.test_installer import run_install_simulation


def test_run_install_simulation_reports_all_steps() -> None:
    manager = ScenarioManager.from_harness_config()
    scenario = manager.load_scenario("disk_insufficient_space")
    steps: list[str] = []
    exit_code = run_install_simulation(
        scenario,
        quiet=True,
        on_step=lambda _step, _total, message: steps.append(message),
    )
    assert len(steps) == 5
    assert exit_code != 0
