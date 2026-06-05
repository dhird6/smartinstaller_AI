"""Load and manage JSON test scenarios."""

from __future__ import annotations

import json
from pathlib import Path

from failure_harness.models import HarnessConfig, ScenarioConfig
from smartinstall.agent.infrastructure.project_paths import get_project_root


class ScenarioManager:
    """Discover and load scenario JSON files."""

    def __init__(self, scenarios_dir: Path) -> None:
        self._scenarios_dir = scenarios_dir.resolve()
        if not self._scenarios_dir.is_dir():
            self._scenarios_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_harness_config(cls, config_path: Path | None = None) -> ScenarioManager:
        root = get_project_root()
        if config_path and config_path.is_file():
            raw = json.loads(config_path.read_text(encoding="utf-8"))
            harness = HarnessConfig.model_validate(raw)
            scenarios_dir = Path(harness.scenarios_directory)
            if not scenarios_dir.is_absolute():
                scenarios_dir = root / scenarios_dir
        else:
            default = root / "failure_harness" / "config" / "scenarios"
            scenarios_dir = default if default.is_dir() else root / "failure_harness" / "config" / "scenarios"
        return cls(scenarios_dir)

    @property
    def scenarios_dir(self) -> Path:
        return self._scenarios_dir

    def list_scenario_ids(self) -> list[str]:
        return sorted(
            p.stem
            for p in self._scenarios_dir.glob("*.json")
            if p.stem not in {"scenario_catalog"}
        )

    def load_scenario(self, scenario_id: str) -> ScenarioConfig:
        path = self._scenarios_dir / f"{scenario_id}.json"
        if not path.is_file():
            path = Path(scenario_id)
        if not path.is_file():
            available = ", ".join(self.list_scenario_ids()) or "(none)"
            raise FileNotFoundError(
                f"Scenario '{scenario_id}' not found in {self._scenarios_dir}. Available: {available}"
            )
        raw = json.loads(path.read_text(encoding="utf-8"))
        return ScenarioConfig.model_validate(raw)

    def load_all_scenarios(self) -> list[ScenarioConfig]:
        return [self.load_scenario(sid) for sid in self.list_scenario_ids()]
