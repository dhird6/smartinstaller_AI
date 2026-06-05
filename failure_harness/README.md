# Smart Installer Failure Injection & RAG Validation Harness

Reusable test framework that validates Smart Installer's ability to detect, diagnose, and recover from downstream application installation failures using the local RAG knowledge system.

## Architecture

```text
Phase 1: Smart Installer Health Checks
    └── Import, config, logging, monitoring, RAG connectivity

Phase 2: Test Application Installation
    ├── TestAppSetup.exe (failure injection simulator)
    ├── Smart Installer monitored install
    ├── Failure detection validation
    └── RAG troubleshooting validation
```

## Components

| Component | Location | Purpose |
|-----------|----------|---------|
| Test Application | `installers/TestAppSetup.exe` | Simulates real installer with injectable failures |
| Failure Engine | `src/failure_harness/engine.py` | Executes single/sequential/simultaneous/random failures |
| Scenario Manager | `failure_harness/config/scenarios/*.json` | JSON-configurable test scenarios |
| Health Checker | `src/failure_harness/health_checker.py` | Phase 1 Smart Installer verification |
| RAG Validator | `src/failure_harness/rag_validator.py` | Validates RAG relevance and detection accuracy |
| Orchestrator | `src/failure_harness/orchestrator.py` | End-to-end workflow coordinator |
| Reports | `failure_harness/artifacts/` | JSON, Markdown, CSV summaries |

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

All 22 failure categories from the specification are supported with deterministic sub-types.

## Scenario Configuration

Failure modes: `single`, `simultaneous`, `sequential`, `random`, `deterministic`

Recovery policies: `none`, `retry`, `skip`, `abort`, `auto`

## Requirements

- Windows 10/11
- Python 3.11+
- Smart Installer AI (this repository)
- Ollama with `phi3:mini` and `nomic-embed-text` (for full RAG validation)
