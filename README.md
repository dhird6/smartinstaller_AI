# SmartInstall AI — Installation Agent + RAG Diagnosis

Automated installer monitoring, failure detection, and instant RAG-powered diagnosis using a local Phi-3 model. Drop in an installer, run one command, get a full JSON report plus step-by-step fix instructions — no cloud APIs, no manual log hunting.

## End-to-End Flow

```
installers/
    └── setup.exe
          │
          ▼
    smartinstall run
          │
          ├─ PRE-SNAPSHOT  ── Event Log watermark, WER snapshot
          ├─ INSTALL       ── Launch installer + track process tree, stdout/stderr
          ├─ POST-SNAPSHOT ── Collect Event Log delta, crash reports, installer logs
          ├─ DETECT        ── FailureDetector classifies outcome
          │
          ├─→ consolidated_report.json   (always written)
          │
          └─→ rag_diagnosis.json         (written automatically on any failure)
                    │
                    ├── nomic-embed-text embeds error signals
                    ├── ChromaDB retrieves top-2 matching KB docs
                    └── phi3:mini produces Root Cause + Fixes + Verification steps
```

## Quick Start

**1. Install Ollama + pull models**

Download Ollama from [ollama.com](https://ollama.com), then:

```powershell
ollama pull phi3:mini
ollama pull nomic-embed-text
```

**2. Install Python dependencies**

```powershell
pip install -e .
# or: pip install -r requirements.txt
```

**3. Drop an installer and run**

```powershell
# Copy your installer into installers/
# e.g. MinGW, Notepad++, any .exe or .msi

python app.py run
# or: smartinstall run
```

> Run PowerShell **as Administrator** for full Event Log and WER coverage.

## Output

| File | Location | Content |
|------|----------|---------|
| `consolidated_report.json` | `sessions/<uuid>/` | Full evidence report: status, errors, process tree, event logs, crash dumps |
| `rag_diagnosis.json` | `sessions/<uuid>/` | Phi-3 diagnosis: root cause, confidence, fixes, verification commands |
| Published report | `reports/` | Symlinked canonical report for easy access |
| `application.log` | `logs/` | Structured agent log |

### RAG Diagnosis Format

```json
{
  "session_id": "abc-123",
  "outcome": "FAILED",
  "root_cause": "Installer exited with code 0 but application executable not found",
  "confidence": "High",
  "evidence": "exitCode=0, installationCompleted=false, GUI_INSTALL_INCOMPLETE detected",
  "recommended_fixes": [
    "Re-run installer and select all required components",
    "Verify installation path exists and is writable",
    "Check antivirus quarantine history"
  ],
  "verification_commands": [
    "where <app-executable>",
    "dir /s *.exe",
    "reg query HKLM\\SOFTWARE\\<AppName>"
  ],
  "escalation": "Escalate to vendor support if reinstall fails after 2 attempts",
  "retrieved_docs": ["gui_install_incomplete.md", "application_not_detected.md"]
}
```

## Project Layout

```text
smartinstaller_AI/
├── app.py                          ← entry point: python app.py run
├── installer_rag.py                ← standalone RAG pipeline (manual / test use)
├── rag.py                          ← Ollama-specific RAG pipeline
│
├── installers/                     ← drop .exe / .msi here
├── reports/                        ← published JSON reports
├── sessions/                       ← per-run session dirs (report + diagnosis live here)
├── logs/                           ← application.log
├── config/smartinstall.config.json
│
├── rag/                            ← knowledge base: generic installer failures (15 docs)
├── rag_docs/                       ← knowledge base: Ollama-specific failures (11 docs)
│
└── src/smartinstall/
    ├── agent/
    │   ├── collectors/             ← EventLog, Process, MSI, WER, InstallerLog
    │   ├── detection/              ← FailureDetector, ErrorAggregator, OutcomeRefiner
    │   ├── orchestration/
    │   │   └── installation_agent.py  ← main pipeline; calls RagPipeline after report write
    │   ├── runners/                ← InstallerRunner (EXE + MSI)
    │   └── session/                ← SessionManager, UnifiedReportWriter
    └── rag/
        └── rag_pipeline.py         ← RagPipeline class (lazy-loads models on first failure)
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `smartinstall run` | Run newest installer found in `installers/` |
| `smartinstall run --installer setup.exe` | Run a specific installer |
| `smartinstall run-all` | Run all installers in `installers/` oldest → newest |
| `smartinstall install C:\path\setup.exe` | Explicit installer path |
| `smartinstall recover` | Mark interrupted sessions as Incomplete |
| `smartinstall demo` | Foundation demo — no installer launched |

### Run flags

| Flag | Purpose |
|------|---------|
| `--installer NAME` | Select installer by filename |
| `--product-name NAME` | Label in reports |
| `--args "/S"` | Pass silent install flags |
| `--timeout 3600` | Max seconds before timeout |
| `--config PATH` | Override config file |

## What Gets Collected

| Source | Trigger | Stored in |
|--------|---------|-----------|
| stdout / stderr | During install | `errors[]`, stream log files |
| Windows Event Log (App/System/Setup) | Live + post-install delta | `evidence.eventLogs` |
| Installer-created `.log` / `.txt` files | After install | `evidence.installerLogFiles` |
| Child process tree (CPU, memory, exit codes) | Every 2 s during install | `evidence.childProcesses` |
| WER crash dumps | Post-install | `evidence.crashReports` |
| MSI verbose log (`/l*v`) | MSI installers only | `evidence.msiDiagnostics` |

## Knowledge Base

### Generic Installer (`rag/`) — 15 categories

| File | Error Code | Trigger |
|------|-----------|---------|
| `gui_install_incomplete.md` | `GUI_INSTALL_INCOMPLETE` | exitCode=0, app not found |
| `install_timeout.md` | `INSTALL_TIMEOUT` | installer.timedOut=true |
| `install_cancelled.md` | `INSTALL_CANCELLED` | User cancelled wizard |
| `install_crash.md` | `INSTALL_CRASH` | Crash report detected |
| `network_failure.md` | `NETWORK_FAILURE` | Download failed / TLS error |
| `permission_denied.md` | `PERMISSION_DENIED` | Access denied |
| `path_failure.md` | `PATH_CONFIGURATION_FAILURE` | Command not recognized after install |
| `antivirus_interference.md` | `ANTIVIRUS_INTERFERENCE` | Executable quarantined |
| `component_missing.md` | `COMPONENT_MISSING` | Required DLL / package missing |
| `process_tracking_failure.md` | `PROCESS_TRACKING_FAILURE` | COLLECTOR_ERROR |
| `log_collection_failure.md` | `LOG_COLLECTION_FAILURE` | Log files missing |
| `application_not_detected.md` | `APPLICATION_NOT_DETECTED` | exitCode=0, installationCompleted=false |
| `package_download_failure.md` | `PACKAGE_DOWNLOAD_FAILURE` | Repository unavailable |
| `registry_entry_missing.md` | `REGISTRY_ENTRY_MISSING` | Registry key absent |
| `disk_space_failure.md` | `DISK_SPACE_FAILURE` | No space left on device |

### Ollama-Specific (`rag_docs/`) — 11 categories

| File | Error |
|------|-------|
| `cuda_failure.md` | CUDA / ROCm initialization failed |
| `gpu_detection.md` | No compatible GPU found |
| `path_error.md` | `ollama` not recognized / PATH missing |
| `connection_refused.md` | Could not connect to Ollama instance |
| `server_timeout.md` | Timed out waiting for server to start |
| `antivirus_block.md` | Access denied / permission errors |
| `missing_exe.md` | `ollama.exe` missing after install |
| `proxy_issue.md` | Pull manifest failed / network issues |
| `model_download.md` | Model download interrupted |
| `disk_full.md` | No space left on device |
| `port_conflict.md` | Port 11434 already in use |

## Extending the Knowledge Base

Add a `.md` file to `rag/` (generic) or `rag_docs/` (Ollama). No code changes needed — both pipelines auto-load all docs on startup.

```markdown
# Category: YOUR_ERROR_CODE

## Error Signature
- <exact log string or field>

## Meaning
<one sentence>

## Common Causes
- <cause>

## Recommended Actions
- <fix>

## Confidence Scoring
- High: <exact match condition>
- Medium: <partial match>
```

## RAG Pipeline — How Diagnosis Works

1. After `consolidated_report.json` is written, `InstallationAgent` calls `RagPipeline.diagnose()` (skipped on SUCCESS)
2. `_extract_log_text()` flattens `status`, `errors[]`, `crash_reports`, and `event_log_entries` into a compact log string
3. `nomic-embed-text` embeds the log string; ChromaDB returns the 2 most semantically similar KB docs
4. `phi3:mini` (temperature=0) reads the KB docs as context and produces the structured diagnosis
5. Result is written as `rag_diagnosis.json` in the session directory
6. If Ollama is not running, the RAG step is skipped with a warning — the main report is always written regardless

## Models

| Model | Role | Size |
|-------|------|------|
| `phi3:mini` | Local LLM — generates fix instructions | 2.2 GB |
| `nomic-embed-text` | Local embeddings — semantic KB retrieval | 274 MB |

## Requirements

- Python 3.11+
- Windows (Event Log / WER APIs)
- Ollama running locally (`ollama serve`)
- PowerShell as Administrator for full Event Log coverage

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Install failed / timed out / partial |
| 2 | Crash detected |
| 3 | Agent error |
| 4 | No installer / invalid input |
| 5 | Insufficient privileges |
