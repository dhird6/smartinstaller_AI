# Smart Installer Failure Injection & RAG Validation Harness

Reusable Windows test framework that validates Smart Installer's ability to detect, diagnose, troubleshoot, and recover from downstream application installation failures using the local RAG knowledge system.

**Important:** This harness does not test Smart Installer's own installation. Phase 1 verifies Smart Installer is operational; Phase 2 injects failures into a **Test Application** installer while Smart Installer monitors the session.

## Architecture

```text
Phase 1: Smart Installer Health Checks
    ├── Package importable, config valid
    ├── Logging, directories, monitoring ready
    ├── Ollama RAG connectivity
    └── Telemetry output paths ready

Phase 2: Test Application Installation
    ├── FailureInjectionEngine (dry-run plan logged)
    ├── TestAppSetup.exe with --scenario <runtime JSON>
    ├── Smart Installer monitored install (InstallationAgent)
    ├── Failure detection + exit code fidelity checks
    └── RAG validation (keyword + source relevance)
```

## Bundled Components

| Component | Location | Purpose |
|-----------|----------|---------|
| Smart Installer | `src/smartinstall/` | Monitors installs, detects failures, queries RAG |
| Test Application | `installers/TestAppSetup.exe` | Simulates installer with injectable failures |
| Failure Engine | `src/failure_harness/engine.py` | Single/sequential/simultaneous/random/deterministic modes |
| Scenario Manager | `failure_harness/config/scenarios/` | 27+ JSON-configurable scenarios |
| Health Checker | `src/failure_harness/health_checker.py` | Phase 1 operational verification |
| RAG Validator | `src/failure_harness/rag_validator.py` | Detection + recommendation relevance scoring |
| Orchestrator | `src/failure_harness/orchestrator.py` | End-to-end workflow coordinator |
| Structured Logger | `src/failure_harness/structured_logger.py` | JSONL, CSV, human-readable logs |
| Report Generator | `src/failure_harness/report_generator.py` | JSON, Markdown, CSV summaries |

## Bundled Desktop EXE (Smart Installer + Test App)

Build a single executable that includes Smart Installer UI, TestAppSetup.exe, and all failure scenarios:

```powershell
.\scripts\build_desktop.ps1
```

Output: `dist\SmartInstallAI.exe`

On first launch, bundled assets are extracted beside the exe:
- `installers/TestAppSetup.exe`
- `failure_harness/config/scenarios/*.json`

Use **Installation Center → Run test install scenario** in the desktop UI to launch a monitored TestApp install with the selected failure scenario.

## Quick Start

```powershell
cd smartinstaller_AI
.\.venv\Scripts\Activate.ps1
pip install -e ".[desktop]"

# Build the test application installer
.\failure_harness\scripts\build_test_installer.ps1

# Run Phase 1 health checks only
.\failure_harness\scripts\run_harness.ps1 -Phase1Only

# Run a single scenario
.\failure_harness\scripts\run_harness.ps1 -Scenario disk_insufficient_space

# List all scenarios
.\failure_harness\scripts\run_harness.ps1 -ListScenarios

# Run all scenarios
.\failure_harness\scripts\run_harness.ps1 -RunAll
```

## Failure Categories (22)

All 22 categories from the specification are registered in `src/failure_harness/categories.py` with **88 failure sub-types**. Each category has at least one JSON scenario under `failure_harness/config/scenarios/`.

| Category | Example Scenario |
|----------|------------------|
| download_acquisition | `download_corrupt_checksum` |
| disk_storage | `disk_insufficient_space` |
| permissions_security | `permissions_uac_denial` |
| dependency | `dependency_missing_dotnet` |
| version_compatibility | `version_compatibility_unsupported_os` |
| registry | `registry_corruption` |
| service | `service_startup_failure` |
| installer_engine | `installer_engine_msi_rollback` |
| file_process_locking | `file_process_locked_dll` |
| os_level | `os_level_wmi_corruption` |
| gpu_driver | `gpu_driver_missing_directx` |
| licensing | `licensing_expired` |
| cloud_api | `cloud_api_timeout` |
| enterprise_deployment | `enterprise_sccm_conflict` |
| update | `update_upgrade_failure` |
| uninstallation | `uninstallation_shared_dependency` |
| migration | `migration_profile_corruption` |
| localization | `localization_unicode_path` |
| plugin_ecosystem | `plugin_ecosystem_api_mismatch` |
| human_user | `human_user_cancellation` |
| telemetry | `telemetry_logging_service_failure` |
| rare_edge_case | `rare_edge_certificate_expiration` |

Composite scenarios: `multi_simultaneous_failures`, `random_failure_sequence`, `sequential_multi_category`, `recovery_retry_success`.

## Scenario Configuration

Failure modes: `single`, `simultaneous`, `sequential`, `random`, `deterministic`

Recovery policies: `none`, `retry`, `skip`, `abort`, `auto`

Example scenario snippet:

```json
{
  "scenarioId": "disk_insufficient_space",
  "failureMode": "single",
  "failures": [{
    "id": "disk-001",
    "category": "disk_storage",
    "subType": "insufficient_disk_space",
    "exitCode": 112,
    "expectedRagKeywords": ["disk", "space", "storage"],
    "recoveryPolicy": "none"
  }],
  "expectSmartInstallerDetection": true,
  "expectRagResponse": true,
  "minRagRelevanceScore": 0.25
}
```

Omit `exitCode` to use the template default for the sub-type.

## Logging & Reporting

Each run produces:

- `failure_harness/logs/harness_<runId>.jsonl` — structured events
- `failure_harness/logs/harness_<runId>.csv` — tabular event log
- `failure_harness/logs/harness_<runId>.log` — human-readable trace
- `failure_harness/artifacts/harness_report_<runId>.json` — full report
- `failure_harness/artifacts/harness_summary_<runId>.md` — executive summary
- `failure_harness/artifacts/harness_metrics_<runId>.csv` — success/recovery/RAG metrics
- `reports/smartinstall_report.json` — Smart Installer unified diagnostic report

## CLI Reference

```powershell
$env:PYTHONPATH = "src"
python -m failure_harness.run_cli --list-scenarios
python -m failure_harness.run_cli --phase1-only
python -m failure_harness.run_cli --scenario disk_insufficient_space
python -m failure_harness.run_cli --run-all
python -m failure_harness.run_cli --generate-catalog
```

Or use the installed entry point: `failure-harness --scenario disk_insufficient_space`

## Success Criteria

The harness validates all ten success criteria from the specification:

1. Smart Installer operational (Phase 1)
2. Test Application install begins (Phase 2)
3. Configured failures injected via TestApp
4. Smart Installer detects failures in unified report
5. Exit codes match failure templates
6. RAG retrieves relevant troubleshooting guidance
7. Recovery workflows execute when configured
8. Complete structured logs generated
9. Timelines and metrics in harness report
10. Smart Installer remains active throughout (never terminated by injection)

## Requirements

- Windows 10/11
- Python 3.11+
- Smart Installer AI (this repository)
- Ollama with `phi3:mini` and `nomic-embed-text` (for full RAG validation)

## Limitations

The Test Application simulates failures via **stdout/stderr messages and exit codes**. It does not create real OS-level conditions (disk full, registry corruption, UAC blocks, etc.). For those, extend `FailureInjectionEngine` with OS-level injectors or use physical test environments.
