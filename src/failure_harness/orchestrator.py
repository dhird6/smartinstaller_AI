"""Main harness orchestrator — Phase 1 setup + Phase 2 failure injection testing."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from failure_harness.engine import FailureInjectionEngine
from failure_harness.health_checker import SmartInstallerHealthChecker
from failure_harness.models import HarnessConfig, HarnessRunReport, PhaseResult, ScenarioConfig
from failure_harness.rag_validator import RagValidator
from failure_harness.report_generator import ReportGenerator
from failure_harness.scenario_manager import ScenarioManager
from failure_harness.structured_logger import StructuredHarnessLogger
from smartinstall.agent.di.container import build_container
from smartinstall.agent.infrastructure.project_paths import get_project_root
from smartinstall.agent.slm.rag_engine import load_report
from smartinstall.core.models.requests import StartSessionRequest


class HarnessOrchestrator:
    """End-to-end failure injection and RAG validation workflow."""

    def __init__(self, config: HarnessConfig) -> None:
        self._config = config
        self._root = get_project_root()
        self._output_dir = self._resolve_path(config.output_directory)
        self._logs_dir = self._resolve_path(config.logs_directory)
        self._run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:8]
        self._logger = StructuredHarnessLogger(self._logs_dir, self._run_id)
        self._health_checker = SmartInstallerHealthChecker()
        self._rag_validator = RagValidator()
        self._reporter = ReportGenerator(self._output_dir)

    def run(self, scenario_id: str | None = None) -> HarnessRunReport:
        started_at = _utc_now()
        sid = scenario_id or self._config.default_scenario or "disk_insufficient_space"
        self._logger.log("orchestrator", "Harness", "run_start", f"Starting harness run {self._run_id}", {"scenarioId": sid})

        scenario = ScenarioManager.from_harness_config(self._harness_config_path()).load_scenario(sid)
        self._ensure_test_app_ready()

        phase1 = self._run_phase1()
        phase2 = self._run_phase2(scenario)

        rag_result = None
        smart_report_path = self._extract_report_path(phase2)
        if smart_report_path and Path(smart_report_path).is_file() and scenario.expect_rag_response:
            rag_result = self._run_rag_validation(scenario, smart_report_path)

        all_events = self._logger.get_events()
        failure_tl, recovery_tl = ReportGenerator.build_timelines(all_events)

        detection_passed = any(c.get("name") == "failure_detection" and c.get("passed") for c in phase2.checks)
        metrics = ReportGenerator.compute_metrics(
            phase1,
            phase2,
            rag_result,
            total_failures_injected=len(scenario.failures),
            detection_passed=detection_passed,
        )

        overall = phase1.success and phase2.success
        if scenario.expect_rag_response and rag_result is not None:
            overall = overall and rag_result.success

        report = HarnessRunReport(
            runId=self._run_id,
            scenarioId=scenario.scenario_id,
            startedAt=started_at,
            completedAt=_utc_now(),
            overallSuccess=overall,
            phase1=phase1,
            phase2=phase2,
            failureTimeline=failure_tl,
            recoveryTimeline=recovery_tl,
            ragValidation=rag_result,
            smartInstallReportPath=smart_report_path,
            metrics=metrics,
        )

        report_path = self._reporter.write_report(report)
        self._logger.log(
            "orchestrator",
            "Harness",
            "run_complete",
            f"Harness run complete — success={overall}",
            {"reportPath": str(report_path)},
        )
        return report

    def _run_phase1(self) -> PhaseResult:
        self._logger.log("phase1", "HealthChecker", "phase_start", "Phase 1: Smart Installer setup verification")
        result = self._health_checker.run_phase1(self._config)
        for check in result.checks:
            self._logger.log(
                "phase1",
                "HealthChecker",
                "health_check",
                f"{check['name']}: {'PASS' if check['passed'] else 'FAIL'}",
                check,
            )
        self._logger.log(
            "phase1",
            "HealthChecker",
            "phase_complete",
            f"Phase 1 complete — success={result.success}",
        )
        return result

    def _run_phase2(self, scenario: ScenarioConfig) -> PhaseResult:
        self._logger.log(
            "phase2",
            "Orchestrator",
            "phase_start",
            f"Phase 2: Test app install with scenario '{scenario.scenario_id}'",
        )
        started = time.monotonic()
        checks: list[dict] = []
        errors: list[str] = []

        test_app = self._get_test_app_path().resolve()
        checks.append({"name": "test_app_ready", "passed": test_app.is_file(), "detail": str(test_app)})
        if not test_app.is_file():
            errors.append("Test application not found")

        scenario_file = self._write_runtime_scenario(scenario).resolve()
        installer_copy = self._stage_test_installer(test_app, scenario).resolve()

        engine = FailureInjectionEngine(random_seed=scenario.random_seed)
        dry_run = engine.execute_scenario(scenario, simulate_only=True)
        for event in dry_run.events:
            self._logger.log(event.phase, event.component, event.event_type, event.message, event.details)
        expected_exit = dry_run.final_exit_code
        checks.append(
            {
                "name": "failure_injection_planned",
                "passed": len(dry_run.injections) > 0,
                "detail": f"{len(dry_run.injections)} failure(s), expected exit={expected_exit}",
                "expectedExitCode": expected_exit,
            }
        )

        report_path: str | None = None
        try:
            container = build_container()
            output_root = Path(container.config.output_root)
            if not output_root.is_absolute():
                output_root = self._root / output_root

            request = StartSessionRequest(
                installerPath=str(installer_copy),
                installerType="EXE",
                productName="TestApp Failure Injection",
                productVersion="1.0.0",
                callerTag=f"harness:{scenario.scenario_id}",
                outputDirectory=str(output_root.resolve()),
                additionalArgs=subprocess.list2cmdline(["--scenario", str(scenario_file)]),
                timeoutSeconds=scenario.install_timeout_seconds,
            )

            self._logger.log(
                "phase2",
                "SmartInstaller",
                "install_start",
                f"Starting monitored install of {installer_copy.name}",
                {"scenarioId": scenario.scenario_id},
            )

            install_result = container.installation_agent.run_monitored_installation(request)
            install_ok = install_result.success and install_result.value is not None

            checks.append(
                {
                    "name": "monitored_install_completed",
                    "passed": install_ok,
                    "detail": "Installation session completed" if install_ok else str(install_result.error),
                }
            )

            if install_ok:
                _session, unified = install_result.value
                report_path = str(
                    container.automated_run_orchestrator._publisher.publish(  # noqa: SLF001
                        unified,
                        application_name="TestApp Failure Injection",
                    )
                )
                checks.append({"name": "report_generated", "passed": True, "detail": report_path, "reportPath": report_path})

                report = load_report(Path(report_path))
                detected, det_msg = self._rag_validator.validate_detection_accuracy(report, scenario)
                checks.append({"name": "failure_detection", "passed": detected, "detail": det_msg})

                actual_exit = self._extract_exit_code(report)
                exit_match = actual_exit == expected_exit if expected_exit != 0 else actual_exit not in (0, None)
                checks.append(
                    {
                        "name": "exit_code_fidelity",
                        "passed": exit_match,
                        "detail": f"expected={expected_exit}, actual={actual_exit}",
                    }
                )
                if not exit_match:
                    errors.append(f"Exit code mismatch: expected {expected_exit}, got {actual_exit}")

                if not detected and scenario.expect_smart_installer_detection:
                    errors.append(det_msg)

                self._logger.log(
                    "phase2",
                    "SmartInstaller",
                    "failure_detected" if detected else "failure_not_detected",
                    det_msg,
                    {"reportPath": report_path, "errorCount": len(report.errors)},
                )
            else:
                errors.append(f"Monitored install failed: {install_result.error}")

        except Exception as exc:  # noqa: BLE001
            checks.append({"name": "monitored_install_completed", "passed": False, "detail": str(exc)})
            errors.append(str(exc))

        duration = time.monotonic() - started
        success = len(errors) == 0 and all(c.get("passed", False) for c in checks if c.get("name") != "failure_detection" or scenario.expect_smart_installer_detection)

        if scenario.expect_smart_installer_detection:
            detection_check = next((c for c in checks if c.get("name") == "failure_detection"), None)
            if detection_check and not detection_check.get("passed"):
                success = False

        self._logger.log("phase2", "Orchestrator", "phase_complete", f"Phase 2 complete — success={success}")

        return PhaseResult(
            phase="phase2_test_application_install",
            success=success,
            durationSeconds=round(duration, 2),
            checks=checks,
            errors=errors,
        )

    def _run_rag_validation(self, scenario: ScenarioConfig, report_path: str):
        self._logger.log("phase2", "RAG", "rag_request", f"Validating RAG response for report {report_path}")
        docs = self._config.rag_docs_directory
        result = self._rag_validator.validate_from_report(
            report_path,
            scenario,
            docs_path=docs,
            llm_model=self._config.slm_model,
            embedding_model=self._config.embedding_model,
        )
        self._logger.log(
            "phase2",
            "RAG",
            "rag_response",
            f"RAG validation score={result.relevance_score}, success={result.success}",
            result.model_dump(by_alias=True),
        )
        return result

    def _ensure_test_app_ready(self) -> None:
        test_app = self._get_test_app_path()
        if test_app.is_file():
            return
        build_script = self._root / "failure_harness" / "scripts" / "build_test_installer.ps1"
        if build_script.is_file() and sys.platform == "win32":
            self._logger.log("setup", "TestApp", "build_start", "Building TestAppSetup.exe via PyInstaller")
            result = subprocess.run(  # noqa: S603
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(build_script),
                    "-SkipInstall",
                ],
                cwd=str(self._root),
                capture_output=True,
                text=True,
                timeout=300,
                check=False,
            )
            if result.returncode == 0 and test_app.is_file():
                self._logger.log("setup", "TestApp", "build_complete", f"Built {test_app}")
                return
            self._logger.log(
                "setup",
                "TestApp",
                "build_failed",
                result.stderr[:500] if result.stderr else "PyInstaller build failed",
            )
        raise FileNotFoundError(
            f"TestAppSetup.exe not found at {test_app}. "
            f"Run: .\\failure_harness\\scripts\\build_test_installer.ps1"
        )

    def _get_test_app_path(self) -> Path:
        if self._config.test_app_path:
            p = Path(self._config.test_app_path)
            return p if p.is_absolute() else self._root / p
        from smartinstall.agent.infrastructure.bundled_assets import bundled_test_app_path

        bundled = bundled_test_app_path()
        candidates = [
            bundled,
            self._root / "installers" / "TestAppSetup.exe",
            self._root / "installers" / "TestAppSetup.py",
            self._root / "failure_harness" / "bin" / "TestAppSetup.exe",
        ]
        for c in candidates:
            if c is not None and c.is_file():
                return c
        return self._root / "installers" / "TestAppSetup.exe"

    def _stage_test_installer(self, test_app: Path, scenario: ScenarioConfig) -> Path:
        installers_dir = self._root / "installers"
        installers_dir.mkdir(parents=True, exist_ok=True)
        dest = installers_dir / f"TestAppSetup_{scenario.scenario_id}.exe"
        if test_app.resolve() != dest.resolve():
            shutil.copy2(test_app, dest)
        return dest.resolve()

    def _write_runtime_scenario(self, scenario: ScenarioConfig) -> Path:
        runtime_dir = self._output_dir / "runtime_scenarios"
        runtime_dir.mkdir(parents=True, exist_ok=True)
        path = runtime_dir / f"{scenario.scenario_id}_{self._run_id}.json"
        path.write_text(scenario.model_dump_json(by_alias=True, indent=2), encoding="utf-8")
        return path

    def _resolve_path(self, rel: str) -> Path:
        p = Path(rel)
        return p if p.is_absolute() else self._root / p

    def _harness_config_path(self) -> Path:
        return self._root / "failure_harness" / "config" / "harness.config.json"

    @staticmethod
    def _extract_report_path(phase2: PhaseResult) -> str | None:
        for check in phase2.checks:
            if check.get("name") == "report_generated" and check.get("reportPath"):
                return str(check["reportPath"])
        return None

    @staticmethod
    def _extract_exit_code(report) -> int | None:
        status = getattr(report, "status", None)
        if status is not None:
            installer = getattr(status, "installer", None)
            if installer is not None and getattr(installer, "exit_code", None) is not None:
                return installer.exit_code
        return None


def load_harness_config(path: Path | None = None) -> HarnessConfig:
    root = get_project_root()
    config_path = path or root / "failure_harness" / "config" / "harness.config.json"
    if not config_path.is_file():
        return HarnessConfig()
    raw = json.loads(config_path.read_text(encoding="utf-8"))
    return HarnessConfig.model_validate(raw)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
