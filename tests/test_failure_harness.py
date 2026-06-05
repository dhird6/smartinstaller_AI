"""Unit tests for the failure injection harness."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from failure_harness.categories import get_failure_template, list_sub_types
from failure_harness.engine import FailureInjectionEngine
from failure_harness.models import FailureCategory, FailureMode, ScenarioConfig
from failure_harness.rag_validator import RagValidator
from failure_harness.scenario_manager import ScenarioManager


@pytest.fixture
def scenarios_dir() -> Path:
    root = Path(__file__).resolve().parents[1]
    return root / "failure_harness" / "config" / "scenarios"


def test_all_failure_categories_have_templates() -> None:
    for category in FailureCategory:
        sub_types = list_sub_types(category)
        assert len(sub_types) >= 1, f"Category {category.value} has no sub-types"


def test_disk_failure_template() -> None:
    template = get_failure_template(FailureCategory.DISK_STORAGE, "insufficient_disk_space")
    assert template.exit_code == 112
    assert "disk" in template.stderr_message.lower() or "space" in template.stderr_message.lower()


def test_engine_single_failure_mode() -> None:
    scenario = ScenarioConfig.model_validate(
        {
            "scenarioId": "test-single",
            "name": "Test",
            "failureMode": "single",
            "failures": [
                {
                    "id": "f1",
                    "category": "disk_storage",
                    "subType": "insufficient_disk_space",
                    "severity": "high",
                },
                {
                    "id": "f2",
                    "category": "dependency",
                    "subType": "missing_vc_runtime",
                    "severity": "medium",
                },
            ],
        }
    )
    engine = FailureInjectionEngine()
    order = engine.resolve_execution_order(scenario)
    assert len(order) == 1
    assert order[0].id == "f1"


def test_engine_simultaneous_mode() -> None:
    scenario = ScenarioConfig.model_validate(
        {
            "scenarioId": "test-multi",
            "name": "Test",
            "failureMode": "simultaneous",
            "failures": [
                {"id": "a", "category": "disk_storage", "subType": "insufficient_disk_space"},
                {"id": "b", "category": "registry", "subType": "registry_corruption"},
            ],
        }
    )
    engine = FailureInjectionEngine()
    order = engine.resolve_execution_order(scenario)
    assert len(order) == 2


def test_engine_deterministic_random_order() -> None:
    base = {
        "scenarioId": "test-det",
        "name": "Test",
        "failureMode": "deterministic",
        "randomSeed": 99,
        "failures": [
            {"id": "a", "category": "licensing", "subType": "flexnet_failure"},
            {"id": "b", "category": "cloud_api", "subType": "api_timeout"},
            {"id": "c", "category": "installer_engine", "subType": "msi_rollback"},
        ],
    }
    engine = FailureInjectionEngine()
    order1 = engine.resolve_execution_order(ScenarioConfig.model_validate(base))
    order2 = engine.resolve_execution_order(ScenarioConfig.model_validate(base))
    assert [f.id for f in order1] == [f.id for f in order2]


def test_engine_execute_produces_nonzero_exit(scenarios_dir: Path) -> None:
    raw = json.loads((scenarios_dir / "disk_insufficient_space.json").read_text(encoding="utf-8"))
    scenario = ScenarioConfig.model_validate(raw)
    engine = FailureInjectionEngine()
    result = engine.execute_scenario(scenario, simulate_only=True)
    assert result.final_exit_code != 0
    assert len(result.injections) == 1


def test_scenario_manager_loads_scenarios(scenarios_dir: Path) -> None:
    manager = ScenarioManager(scenarios_dir)
    ids = manager.list_scenario_ids()
    assert "disk_insufficient_space" in ids
    scenario = manager.load_scenario("disk_insufficient_space")
    assert scenario.scenario_id == "disk_insufficient_space"


def test_rag_validator_keyword_scoring() -> None:
    validator = RagValidator()
    matched, score = validator._score_relevance(
        "The installation failed due to insufficient disk space on drive C:",
        ["testapp_disk_storage.md"],
        ["disk", "space", "storage"],
    )
    assert score > 0.3
    assert "disk" in matched or "space" in matched


def test_rag_validator_fuzzy_match() -> None:
    assert RagValidator._fuzzy_match("disk space", "insufficient disk-space error")


def test_harness_config_exists() -> None:
    root = Path(__file__).resolve().parents[1]
    config_path = root / "failure_harness" / "config" / "harness.config.json"
    assert config_path.is_file()
    from failure_harness.orchestrator import load_harness_config

    config = load_harness_config(config_path)
    assert config.harness_version == "1.0"
