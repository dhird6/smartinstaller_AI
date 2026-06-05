"""Configurable failure injection engine."""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

from failure_harness.categories import FailureTemplate, get_failure_template, severity_multiplier
from failure_harness.models import (
    FailureMode,
    FailureSeverity,
    HarnessEvent,
    InjectedFailureSpec,
    RecoveryPolicy,
    ScenarioConfig,
)


@dataclass
class InjectionResult:
    """Outcome of executing one injected failure."""

    spec: InjectedFailureSpec
    template: FailureTemplate
    stdout_lines: list[str] = field(default_factory=list)
    stderr_lines: list[str] = field(default_factory=list)
    exit_code: int = 0
    injected_at: str = ""
    recovery_attempted: bool = False
    recovery_success: bool = False


@dataclass
class EngineRunResult:
    """Aggregate result from failure engine execution."""

    scenario: ScenarioConfig
    injections: list[InjectionResult]
    events: list[HarnessEvent]
    final_exit_code: int
    success_path: bool


class FailureInjectionEngine:
    """Executes failure scenarios with configurable timing and modes."""

    def __init__(self, *, random_seed: int | None = None) -> None:
        self._rng = random.Random(random_seed)

    def resolve_execution_order(self, scenario: ScenarioConfig) -> list[InjectedFailureSpec]:
        failures = list(scenario.failures)
        mode = scenario.failure_mode

        if mode == FailureMode.SINGLE:
            return failures[:1] if failures else []

        if mode == FailureMode.SIMULTANEOUS:
            return failures

        if mode == FailureMode.SEQUENTIAL:
            return sorted(failures, key=lambda f: f.delay_seconds)

        if mode in (FailureMode.RANDOM, FailureMode.DETERMINISTIC):
            seed = scenario.random_seed if mode == FailureMode.DETERMINISTIC else None
            if seed is not None:
                rng = random.Random(seed)
            else:
                rng = self._rng
            shuffled = failures.copy()
            rng.shuffle(shuffled)
            return shuffled

        return failures

    def execute_scenario(
        self,
        scenario: ScenarioConfig,
        *,
        simulate_only: bool = False,
    ) -> EngineRunResult:
        """Run failure injections and return structured results."""
        events: list[HarnessEvent] = []
        injections: list[InjectionResult] = []
        order = self.resolve_execution_order(scenario)

        events.append(
            self._event(
                "failure_injection",
                "FailureEngine",
                "scenario_start",
                f"Starting scenario '{scenario.scenario_id}' with mode {scenario.failure_mode.value}",
                {"failureCount": len(order), "mode": scenario.failure_mode.value},
            )
        )

        max_exit = 0
        for spec in order:
            if spec.delay_seconds > 0 and not simulate_only:
                time.sleep(min(spec.delay_seconds, 30.0))

            result = self._inject_failure(spec, events, simulate_only=simulate_only)
            injections.append(result)
            max_exit = max(max_exit, result.exit_code)

            if scenario.failure_mode == FailureMode.SEQUENTIAL and spec.recovery_policy != RecoveryPolicy.NONE:
                self._attempt_recovery(spec, result, events)

        if not injections:
            success_path = True
        else:
            success_path = all(inj.exit_code == 0 for inj in injections)

        events.append(
            self._event(
                "failure_injection",
                "FailureEngine",
                "scenario_complete",
                f"Scenario complete — {len(injections)} failure(s) injected",
                {"finalExitCode": max_exit},
            )
        )

        return EngineRunResult(
            scenario=scenario,
            injections=injections,
            events=events,
            final_exit_code=max_exit if injections else 0,
            success_path=success_path,
        )

    def _inject_failure(
        self,
        spec: InjectedFailureSpec,
        events: list[HarnessEvent],
        *,
        simulate_only: bool,
    ) -> InjectionResult:
        template = get_failure_template(spec.category, spec.sub_type)
        now = _utc_now()
        stderr_msg = spec.message or template.stderr_message
        stdout_msg = template.stdout_message

        events.append(
            self._event(
                "failure_injection",
                "FailureEngine",
                "failure_injected",
                f"Injecting {spec.category.value}/{spec.sub_type} (severity={spec.severity.value})",
                {
                    "failureId": spec.id,
                    "category": spec.category.value,
                    "subType": spec.sub_type,
                    "exitCode": spec.exit_code if spec.exit_code is not None else template.exit_code,
                },
            )
        )

        exit_code = spec.exit_code if spec.exit_code is not None else template.exit_code
        if spec.severity == FailureSeverity.CRITICAL:
            exit_code = max(exit_code, template.exit_code)

        stdout_lines = [stdout_msg, *template.log_lines[: severity_multiplier(spec.severity)]]
        stderr_lines = [stderr_msg, *template.log_lines]

        return InjectionResult(
            spec=spec,
            template=template,
            stdout_lines=stdout_lines,
            stderr_lines=stderr_lines,
            exit_code=exit_code,
            injected_at=now,
        )

    def _attempt_recovery(
        self,
        spec: InjectedFailureSpec,
        result: InjectionResult,
        events: list[HarnessEvent],
    ) -> None:
        policy = spec.recovery_policy
        if policy == RecoveryPolicy.NONE or policy == RecoveryPolicy.ABORT:
            return

        result.recovery_attempted = True
        events.append(
            self._event(
                "recovery",
                "FailureEngine",
                "recovery_attempt",
                f"Attempting recovery policy '{policy.value}' for failure {spec.id}",
                {"failureId": spec.id, "policy": policy.value},
            )
        )

        if policy in (RecoveryPolicy.RETRY, RecoveryPolicy.AUTO) and spec.retry_count > 0:
            result.recovery_success = True
            result.exit_code = 0
            events.append(
                self._event(
                    "recovery",
                    "FailureEngine",
                    "recovery_success",
                    f"Recovery succeeded after retry for {spec.id}",
                    {"failureId": spec.id},
                )
            )
        elif policy == RecoveryPolicy.SKIP:
            result.recovery_success = True
            result.exit_code = 0
            events.append(
                self._event(
                    "recovery",
                    "FailureEngine",
                    "recovery_skip",
                    f"Skipped failed step {spec.id}",
                    {"failureId": spec.id},
                )
            )

    def _event(
        self,
        phase: str,
        component: str,
        event_type: str,
        message: str,
        details: dict | None = None,
    ) -> HarnessEvent:
        return HarnessEvent(
            timestamp=_utc_now(),
            phase=phase,
            component=component,
            eventType=event_type,
            message=message,
            details=details or {},
        )


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
