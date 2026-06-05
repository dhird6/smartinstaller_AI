"""Utilities to generate and validate JSON test scenarios from failure templates."""

from __future__ import annotations

import json
from pathlib import Path

from failure_harness.categories import get_failure_template, list_sub_types
from failure_harness.models import FailureCategory, FailureMode, ScenarioConfig


def build_scenario_for_sub_type(
    *,
    category: FailureCategory,
    sub_type: str,
    scenario_id: str | None = None,
    failure_mode: FailureMode = FailureMode.SINGLE,
    expect_detection: bool = True,
    expect_rag: bool = True,
    min_rag_score: float = 0.25,
) -> ScenarioConfig:
    """Create a ScenarioConfig from a registered failure template."""
    template = get_failure_template(category, sub_type)
    sid = scenario_id or f"{category.value}_{sub_type}"
    return ScenarioConfig(
        scenarioId=sid,
        name=sub_type.replace("_", " ").title(),
        description=(
            f"Validates Smart Installer detection and RAG guidance for "
            f"{category.value}/{sub_type}."
        ),
        failureMode=failure_mode,
        failures=[
            {
                "id": f"{category.value[:4]}-001",
                "category": category.value,
                "subType": sub_type,
                "severity": "high",
                "delaySeconds": 0.3,
                "expectedRagKeywords": list(template.default_keywords),
                "recoveryPolicy": "none",
            }
        ],
        installTimeoutSeconds=120,
        expectSmartInstallerDetection=expect_detection,
        expectRagResponse=expect_rag,
        minRagRelevanceScore=min_rag_score,
    )


def write_scenario(scenario: ScenarioConfig, output_dir: Path) -> Path:
    """Write a scenario JSON file and return its path."""
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{scenario.scenario_id}.json"
    path.write_text(scenario.model_dump_json(by_alias=True, indent=2) + "\n", encoding="utf-8")
    return path


def generate_category_representatives(output_dir: Path, *, overwrite: bool = False) -> list[Path]:
    """Generate one scenario per failure category using the first registered sub-type."""
    written: list[Path] = []
    for category in FailureCategory:
        sub_types = list_sub_types(category)
        if not sub_types:
            continue
        scenario = build_scenario_for_sub_type(category=category, sub_type=sub_types[0])
        path = output_dir / f"{scenario.scenario_id}.json"
        if path.is_file() and not overwrite:
            continue
        written.append(write_scenario(scenario, output_dir))
    return written


def build_scenario_catalog(scenarios_dir: Path) -> dict:
    """Build an index of scenarios grouped by primary failure category."""
    catalog: dict[str, list[dict[str, str]]] = {}
    for path in sorted(scenarios_dir.glob("*.json")):
        if path.name == "scenario_catalog.json":
            continue
        raw = json.loads(path.read_text(encoding="utf-8"))
        scenario_id = raw.get("scenarioId", path.stem)
        failures = raw.get("failures") or []
        primary_category = failures[0].get("category", "unknown") if failures else "unknown"
        entry = {
            "scenarioId": scenario_id,
            "name": raw.get("name", scenario_id),
            "failureMode": raw.get("failureMode", "single"),
            "primaryCategory": primary_category,
        }
        catalog.setdefault(primary_category, []).append(entry)
    return {"categories": catalog, "totalScenarios": sum(len(v) for v in catalog.values())}


def write_scenario_catalog(scenarios_dir: Path) -> Path:
    catalog = build_scenario_catalog(scenarios_dir)
    path = scenarios_dir / "scenario_catalog.json"
    path.write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")
    return path
