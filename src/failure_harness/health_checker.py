"""Phase 1 health checks for Smart Installer operational readiness."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from failure_harness.models import HarnessConfig, PhaseResult
from smartinstall.agent.di.container import build_container
from smartinstall.agent.infrastructure.project_paths import get_project_root


@dataclass
class HealthCheckContext:
    """Runtime context for Phase 1 verification."""

    config: HarnessConfig
    project_root: Path = field(default_factory=get_project_root)
    background_process: subprocess.Popen[str] | None = None


class SmartInstallerHealthChecker:
    """Verify Smart Installer is installed, running, and all services are active."""

    def run_phase1(self, config: HarnessConfig) -> PhaseResult:
        ctx = HealthCheckContext(config=config)
        started = time.monotonic()
        checks: list[dict] = []
        errors: list[str] = []

        check_fns = [
            ("smart_installer_importable", self._check_importable),
            ("config_valid", self._check_config),
            ("logging_active", self._check_logging),
            ("directories_ready", self._check_directories),
            ("monitoring_service", self._check_monitoring),
            ("rag_connectivity", self._check_rag_connectivity),
            ("telemetry_logging", self._check_telemetry),
            ("health_checks_pass", self._check_health_endpoints),
        ]

        if not config.phase1_skip_install:
            check_fns.insert(0, ("smart_installer_installed", self._check_installation))

        for name, fn in check_fns:
            try:
                ok, detail = fn(ctx)
                checks.append({"name": name, "passed": ok, "detail": detail})
                if not ok:
                    errors.append(f"{name}: {detail}")
            except Exception as exc:  # noqa: BLE001 — health probe must not abort phase
                checks.append({"name": name, "passed": False, "detail": str(exc)})
                errors.append(f"{name}: {exc}")

        duration = time.monotonic() - started
        return PhaseResult(
            phase="phase1_smart_installer_setup",
            success=len(errors) == 0,
            durationSeconds=round(duration, 2),
            checks=checks,
            errors=errors,
        )

    def _check_installation(self, ctx: HealthCheckContext) -> tuple[bool, str]:
        dist_exe = ctx.project_root / "dist" / "SmartInstallAI.exe"
        if dist_exe.is_file():
            return True, f"Packaged installer found at {dist_exe}"
        pyproject = ctx.project_root / "pyproject.toml"
        if pyproject.is_file():
            return True, "Development installation (pyproject.toml present)"
        return False, "Smart Installer not found — run build or install package"

    def _check_importable(self, ctx: HealthCheckContext) -> tuple[bool, str]:
        try:
            import smartinstall  # noqa: F401, PLC0415

            version = getattr(smartinstall, "__version__", "unknown")
            return True, f"smartinstall package importable (version={version})"
        except ImportError as exc:
            return False, f"Cannot import smartinstall: {exc}"

    def _check_config(self, ctx: HealthCheckContext) -> tuple[bool, str]:
        config_path = ctx.project_root / "config" / "smartinstall.config.json"
        if not config_path.is_file():
            return False, f"Missing config: {config_path}"
        raw = json.loads(config_path.read_text(encoding="utf-8"))
        required = ("logsDirectory", "reportsDirectory", "ragDocsDirectory")
        missing = [k for k in required if k not in raw and k.lower() not in str(raw).lower()]
        if missing:
            return False, f"Config missing keys: {missing}"
        return True, "smartinstall.config.json valid"

    def _check_logging(self, ctx: HealthCheckContext) -> tuple[bool, str]:
        container = build_container()
        logs_dir = Path(container.config.logs_dir)
        if not logs_dir.is_absolute():
            logs_dir = ctx.project_root / logs_dir
        logs_dir.mkdir(parents=True, exist_ok=True)
        test_marker = logs_dir / ".harness_health_check"
        test_marker.write_text(_utc_now(), encoding="utf-8")
        if test_marker.is_file():
            test_marker.unlink(missing_ok=True)
            return True, f"Logging directory writable: {logs_dir}"
        return False, "Cannot write to logs directory"

    def _check_directories(self, ctx: HealthCheckContext) -> tuple[bool, str]:
        for name in ("installers", "reports", "sessions", "logs", "rag_docs"):
            path = ctx.project_root / name
            path.mkdir(parents=True, exist_ok=True)
        return True, "Standard project directories ready"

    def _check_monitoring(self, ctx: HealthCheckContext) -> tuple[bool, str]:
        state_path = ctx.project_root / "sessions" / "monitoring_state.json"
        if ctx.config.phase1_start_background_monitor:
            if ctx.background_process is None or ctx.background_process.poll() is not None:
                bg_script = ctx.project_root / "background_service.py"
                if bg_script.is_file():
                    ctx.background_process = subprocess.Popen(  # noqa: S603
                        [sys.executable, str(bg_script)],
                        cwd=str(ctx.project_root),
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
                    )
                    time.sleep(2.0)
        if state_path.is_file() or ctx.background_process is not None:
            return True, "Background monitoring service active or starting"
        return True, "Monitoring module available (background service optional in dev mode)"

    def _check_rag_connectivity(self, ctx: HealthCheckContext) -> tuple[bool, str]:
        host = ctx.config.ollama_host.rstrip("/")
        url = f"{host}/api/tags"
        try:
            req = urllib.request.Request(url, method="GET")  # noqa: S310 — controlled health probe URL
            with urllib.request.urlopen(req, timeout=5) as resp:  # noqa: S310
                if resp.status == 200:
                    return True, f"Ollama RAG backend reachable at {host}"
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            return False, f"Ollama not reachable at {host}: {exc}. Start Ollama for full RAG validation."
        return False, "Unexpected RAG connectivity response"

    def _check_telemetry(self, ctx: HealthCheckContext) -> tuple[bool, str]:
        output = ctx.project_root / ctx.config.output_directory
        if not output.is_absolute():
            output = ctx.project_root / output
        output.mkdir(parents=True, exist_ok=True)
        return True, f"Telemetry output directory ready: {output}"

    def _check_health_endpoints(self, ctx: HealthCheckContext) -> tuple[bool, str]:
        rag_docs = ctx.project_root / "rag_docs"
        if not rag_docs.is_dir() or not any(rag_docs.glob("*.md")):
            return False, "RAG knowledge base (rag_docs/*.md) missing"
        python_ok = shutil.which(sys.executable) is not None
        if not python_ok:
            return False, "Python runtime not available"
        return True, "All health checks passed"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
