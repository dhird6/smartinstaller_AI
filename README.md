# SmartInstall AI — Installation Agent + RAG Diagnosis

Automated installer intake, one-command monitored installation, failure detection, and automatic RAG-powered diagnosis using a local Phi-3 model — no cloud APIs required.

## How It Works

```
installers/  →  smartinstall run  →  Monitor  →  Detect failure  →  JSON report
                                                                          ↓
                                                               RAG Pipeline (Phi-3)
                                                                          ↓
                                                               rag_diagnosis.json
```

1. **Agent** runs the installer and collects evidence (process tree, event logs, crash reports, MSI logs)
2. **FailureDetector** classifies the outcome (SUCCESS / FAILED / CRASHED / TIMED_OUT)
3. **UnifiedReportWriter** writes `consolidated_report.json`
4. **RagPipeline** automatically reads the report, embeds the error signals with `nomic-embed-text`, retrieves the closest KB docs from ChromaDB, and feeds them to `phi3:mini` → writes `rag_diagnosis.json`

## User Workflow

1. Copy an installer into `installers/`
2. Run one command
3. Open the report and diagnosis in `reports/`

```powershell
cd smartinstaller_AI
.\.venv\Scripts\Activate.ps1
pip install -e .

# Copy your installer, e.g. npp.8.9.6.2.Installer.x64.exe → installers\

python app.py run
# or: smartinstall run
```

## Models Used (RAG)

| Model | Role | Size |
|---|---|---|
| `phi3:mini` | Local LLM for diagnosis | 2.2 GB |
| `nomic-embed-text` | Local embedding model | 274 MB |

Pull before first run:
```powershell
ollama pull phi3:mini
ollama pull nomic-embed-text
```

## Project Layout

```text
smartinstaller_AI/
├── app.py                        ← python app.py run
├── installer_rag.py              ← standalone RAG pipeline (manual use)
├── installers/                   ← drop .exe / .msi here
├── reports/                      ← published JSON reports + rag_diagnosis.json
├── logs/                         ← application.log (agent)
├── sessions/                     ← per-run artifacts + session summaries
├── config/smartinstall.config.json
├── rag/                          ← knowledge base: generic installer failures (15 docs)
├── rag_docs/                     ← knowledge base: Ollama-specific failures (11 docs)
└── src/smartinstall/
    ├── agent/
    │   ├── collectors/           ← EventLog, Process, MSI, WER, InstallerLog
    │   ├── detection/            ← FailureDetector, ErrorAggregator
    │   ├── orchestration/        ← InstallationAgent (wires everything + calls RAG)
    │   ├── runners/              ← InstallerRunner
    │   └── session/              ← SessionManager, UnifiedReportWriter
    └── rag/
        └── rag_pipeline.py       ← RagPipeline — called automatically after report write
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `smartinstall run` | Discover newest installer in `installers/`, run full workflow |
| `smartinstall run --installer npp.8.9.6.2.Installer.x64.exe` | Run a specific package |
| `smartinstall run-all` | Run every installer in `installers/` (oldest → newest) |
| `smartinstall install C:\path\setup.exe` | Explicit path |
| `smartinstall recover` | Mark interrupted sessions `Incomplete` |
| `smartinstall demo` | Foundation demo (no installer launch) |

## Output Artifacts

| Location | Content |
|----------|---------|
| `reports/<name>_<date>_<id>.json` | Canonical report (`status` + `errors` + `evidence`) |
| `reports/rag_diagnosis_<id>.json` | Phi-3 diagnosis (`root_cause`, `confidence`, `fixes`, `verification_commands`) |
| `sessions/<uuid>/` | Captured streams, `collected_logs/`, internal `session.json` |
| `logs/application.log` | Agent structured log |

## RAG Diagnosis Output Format

```json
{
  "session_id": "...",
  "outcome": "FAILED",
  "root_cause": "...",
  "confidence": "High",
  "evidence": "...",
  "recommended_fixes": ["1. ...", "2. ...", "3. ..."],
  "verification_commands": ["where <exe>", "reg query ..."],
  "escalation": "...",
  "retrieved_docs": ["gui_install_incomplete.md", "application_not_detected.md"]
}
```

## Knowledge Base Coverage

### Generic Installer (`rag/`)
| File | Error Code |
|---|---|
| `gui_install_incomplete.md` | `GUI_INSTALL_INCOMPLETE` |
| `install_timeout.md` | `INSTALL_TIMEOUT` |
| `install_cancelled.md` | `INSTALL_CANCELLED` |
| `install_crash.md` | `INSTALL_CRASH` |
| `network_failure.md` | `NETWORK_FAILURE` |
| `permission_denied.md` | `PERMISSION_DENIED` |
| `path_failure.md` | `PATH_CONFIGURATION_FAILURE` |
| `antivirus_interference.md` | `ANTIVIRUS_INTERFERENCE` |
| `component_missing.md` | `COMPONENT_MISSING` |
| `process_tracking_failure.md` | `PROCESS_TRACKING_FAILURE` |
| `log_collection_failure.md` | `LOG_COLLECTION_FAILURE` |
| `application_not_detected.md` | `APPLICATION_NOT_DETECTED` |
| `package_download_failure.md` | `PACKAGE_DOWNLOAD_FAILURE` |
| `registry_entry_missing.md` | `REGISTRY_ENTRY_MISSING` |
| `disk_space_failure.md` | `DISK_SPACE_FAILURE` |

### Ollama-Specific (`rag_docs/`)
| File | Error |
|---|---|
| `cuda_failure.md` | CUDA / ROCm initialization failed |
| `gpu_detection.md` | No compatible GPU found |
| `path_error.md` | `ollama` not recognized / missing PATH |
| `connection_refused.md` | Could not connect to running Ollama instance |
| `server_timeout.md` | Timed out waiting for server to start |
| `antivirus_block.md` | Access denied / permission errors |
| `missing_exe.md` | `ollama.exe` missing after install |
| `proxy_issue.md` | Pull manifest failed / network issues |
| `model_download.md` | Model download interrupted |
| `disk_full.md` | No space left on device |
| `port_conflict.md` | Port 11434 already in use |

## Requirements

- Python 3.11+
- Windows (installer execution + Event Log / WER)
- Ollama installed and running (`ollama serve`)
- Run PowerShell **as Administrator** for best Event Log coverage

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Install failed |
| 2 | Crash detected |
| 3 | Agent error |
| 4 | No installer / invalid input |
| 5 | Insufficient privileges |
