# SmartInstall AI — Installation Agent + RAG Diagnosis

Automated installer monitoring, failure detection, and instant local RAG-powered diagnosis using Phi-3. Right-click any `.exe` or `.msi`, use it normally, and get step-by-step fix suggestions if it fails — no cloud APIs, no terminal, no manual steps.

---

## How It Works

```
Right-click installer
        |
        +-- Thread A: start Ollama silently (if not running)
        |
        +-- Thread B: SmartInstall agent runs in background
        |       |
        |       +-- PRE-SNAPSHOT   event log watermark, WER snapshot
        |       +-- INSTALL        launch installer + track processes, logs, events
        |       +-- POST-SNAPSHOT  collect deltas: event log, crash dumps, installer logs
        |       +-- DETECT         classify outcome (SUCCESS / FAILED / CRASHED / TIMED_OUT)
        |       +-- REPORT         write consolidated_report.json
        |       +-- RAG            on failure: embed errors -> ChromaDB -> phi3:mini
        |                          write rag_diagnosis.json
        |
        +-- Main thread: status window (spinner -> result in-place, never re-opens)
```

---

## One-Time Setup

```powershell
# 1. Install Ollama from https://ollama.com, then pull models:
ollama pull phi3:mini
ollama pull nomic-embed-text

# 2. Install the package (use python -m pip if pip alone is wrong version):
cd "path\to\smartinstaller_AI"
python -m pip install -e .

# 3. Register the right-click menu (no admin needed):
python context_menu/register.py
```

That's it. You never need to run these again.

---

## Using It

1. **Right-click** any `.exe` or `.msi` installer in File Explorer
2. Click **"Show more options"** (Windows 11 only)
3. Click **"Monitor with SmartInstaller AI"**
4. A small status window appears — **use your installer normally**, click through it as usual
5. When the installer finishes, the window updates automatically:

**On success** (green):
```
Installation completed successfully.
No failures detected.
```

**On failure** (red):
```
Root Cause:    Installer exited with code 0 but application not found on disk
Confidence:    High
Evidence:      exitCode=0, installationCompleted=false, GUI_INSTALL_INCOMPLETE

Recommended Fixes:
  1. Re-run installer and select all required components
  2. Verify installation path exists and is writable
  3. Check antivirus quarantine — Windows Security > Protection History

Verification Commands:
  - where <app-executable>
  - reg query HKLM\SOFTWARE\<AppName>

KB docs matched: gui_install_incomplete.md, application_not_detected.md
```

> **Note:** Ollama starts automatically in the background if it is not already running. The status window is non-blocking — your installer runs freely, monitoring happens in parallel.

---

## To Remove the Context Menu Entry

```powershell
python context_menu/register.py --unregister
```

---

## Output Files

Both files are written to `sessions/<uuid>/` for each run:

| File | Written when | Content |
|------|-------------|---------|
| `consolidated_report.json` | Always | Full evidence: status, errors, process tree, event logs, crash dumps |
| `rag_diagnosis.json` | Failures only | Root cause, confidence, numbered fixes, verification commands, KB docs matched |

Published reports are also copied to `reports/` for easy access.

### rag_diagnosis.json format

```json
{
  "session_id": "abc-123",
  "outcome": "FAILED",
  "root_cause": "Installer exited cleanly but target executable not found",
  "confidence": "High",
  "evidence": "exitCode=0, installationCompleted=false",
  "recommended_fixes": ["Re-run installer", "Check antivirus quarantine", "Verify install path"],
  "verification_commands": ["where <exe>", "reg query HKLM\\SOFTWARE\\<App>"],
  "escalation": "Escalate to vendor if reinstall fails twice",
  "retrieved_docs": ["gui_install_incomplete.md", "application_not_detected.md"]
}
```

---

## Project Layout

```text
smartinstaller_AI/
├── context_menu/
│   ├── register.py          <- run once to add/remove right-click menu
│   └── launcher.pyw         <- silent launcher (no console window)
│
├── app.py                   <- CLI entry point (python app.py run)
├── installer_rag.py         <- standalone RAG pipeline for manual use
├── rag.py                   <- Ollama-specific RAG pipeline
│
├── installers/              <- drop .exe / .msi here (CLI workflow only)
├── reports/                 <- published JSON reports
├── sessions/                <- per-run dirs: consolidated_report + rag_diagnosis
├── logs/                    <- application.log
├── config/smartinstall.config.json
│
├── rag/                     <- knowledge base: generic installer failures (15 docs)
├── rag_docs/                <- knowledge base: Ollama-specific failures (11 docs)
│
└── src/smartinstall/
    ├── agent/
    │   ├── collectors/      <- EventLog, Process, MSI, WER, InstallerLog
    │   ├── detection/       <- FailureDetector, ErrorAggregator, OutcomeRefiner
    │   ├── orchestration/   <- InstallationAgent (calls RagPipeline after report)
    │   ├── runners/         <- InstallerRunner: EXE + MSI, elevated + standard
    │   └── session/         <- SessionManager, UnifiedReportWriter
    └── rag/
        └── rag_pipeline.py  <- RagPipeline (lazy-loads models on first failure)
```

---

## CLI (Advanced / Automation)

```powershell
smartinstall run                                  # newest installer in installers/
smartinstall run --installer setup.exe            # specific file
smartinstall run-all                              # all installers oldest to newest
smartinstall install C:\path\to\setup.exe        # any path, no copying needed
smartinstall recover                              # mark interrupted sessions incomplete
```

| Flag | Purpose |
|------|---------|
| `--args "/S"` | Silent install flags |
| `--timeout 3600` | Max wait in seconds |
| `--product-name NAME` | Label used in reports |

---

## What Gets Collected

| Source | When | Where in report |
|--------|------|----------------|
| stdout / stderr | During install | `errors[]`, log files |
| Windows Event Log | Live + post-install delta | `evidence.eventLogs` |
| Installer-created log files | After install | `evidence.installerLogFiles` |
| Child process tree (CPU, memory) | Every 2 s | `evidence.childProcesses` |
| WER crash dumps | Post-install | `evidence.crashReports` |
| MSI verbose log | MSI only | `evidence.msiDiagnostics` |

---

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

### Adding a New Error Type

Drop a `.md` file into `rag/` (generic) or `rag_docs/` (Ollama). No code changes needed.

```markdown
# Category: YOUR_ERROR_CODE

## Error Signature
- <log string or field value that identifies this error>

## Meaning
<one sentence>

## Common Causes
- <cause>

## Recommended Actions
- <fix step>

## Confidence Scoring
- High: <exact match condition>
- Medium: <partial match>
```

---

## Models

| Model | Role | Size |
|-------|------|------|
| `phi3:mini` | Local LLM — generates fix instructions | 2.2 GB |
| `nomic-embed-text` | Local embeddings — semantic KB retrieval | 274 MB |

Both run inside Ollama. No internet required after initial pull.

---

## Requirements

- Python 3.11+
- Windows 10 / 11 (Event Log and WER APIs)
- Ollama installed (auto-started by launcher if not running)

## Exit Codes (CLI)

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Install failed / timed out / partial |
| 2 | Crash detected |
| 3 | Agent error |
| 4 | No installer / invalid path |
| 5 | Insufficient privileges |
