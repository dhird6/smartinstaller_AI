# SmartInstaller AI

An autonomous, fully local installation troubleshooting system powered by Retrieval-Augmented Generation (RAG). It reads error logs, retrieves the most relevant fix from a structured knowledge base, and returns step-by-step repair instructions — all without any cloud API calls.

Two independent RAG pipelines are included:
- **`rag.py`** — Ollama-specific installation failures
- **`installer_rag.py`** — Generic Windows software installer failures (any application)

## How It Works

```
Failure Log  →  Log Cleaner  →  ChromaDB Retriever  →  Phi-3 (local LLM)  →  Diagnosis Report
                                 (nomic-embed-text)
```

1. **Log cleaning** — filters raw output to error/critical/failed/timeout lines only
2. **Embedding** — `nomic-embed-text` converts each KB document into vectors stored in ChromaDB
3. **Retrieval** — top 2 most semantically similar failure docs are fetched
4. **Generation** — `phi3:mini` reads the retrieved docs and outputs a structured diagnosis

## Models Used

| Model | Role | Size |
|---|---|---|
| `phi3:mini` | Local LLM for diagnosis | 2.2 GB |
| `nomic-embed-text` | Local embedding model | 274 MB |

Both run inside Ollama — no internet required after initial setup.

## Project Structure

```
smartinstaller_AI/
├── rag.py                      # RAG pipeline: Ollama installation failures
├── installer_rag.py            # RAG pipeline: Generic installer failures
│
├── rag_docs/                   # Knowledge base: Ollama-specific errors
│   ├── antivirus_block.md
│   ├── connection_refused.md
│   ├── cuda_failure.md
│   ├── disk_full.md
│   ├── gpu_detection.md
│   ├── missing_exe.md
│   ├── model_download.md
│   ├── path_error.md
│   ├── port_conflict.md
│   ├── proxy_issue.md
│   └── server_timeout.md
│
└── rag/                        # Knowledge base: Generic installer errors
    ├── gui_install_incomplete.md
    ├── install_timeout.md
    ├── install_cancelled.md
    ├── install_crash.md
    ├── network_failure.md
    ├── permission_denied.md
    ├── path_failure.md
    ├── antivirus_interference.md
    ├── component_missing.md
    ├── process_tracking_failure.md
    ├── log_collection_failure.md
    ├── application_not_detected.md
    ├── package_download_failure.md
    ├── registry_entry_missing.md
    └── disk_space_failure.md
```

## Setup

**1. Install Ollama for Windows**

Download from [ollama.com](https://ollama.com) and run the installer.

**2. Pull the required models**

```powershell
ollama pull phi3:mini
ollama pull nomic-embed-text
```

**3. Install Python dependencies**

```powershell
pip install langchain langchain-ollama langchain-chroma chromadb
```

**4. Run**

```powershell
# For Ollama installation failures
python rag.py

# For generic Windows installer failures
python installer_rag.py
```

## RAG Pipelines

### `rag.py` — Ollama Troubleshooter

Diagnoses failures during Ollama installation and startup on Windows. Pass in your Ollama server log:

```python
log_path = Path(os.environ["LOCALAPPDATA"]) / "Ollama" / "server.log"
mock_error_log = log_path.read_text(encoding="utf-8", errors="ignore")
```

**Output format:** numbered fix steps referencing the official Ollama docs.

---

### `installer_rag.py` — Generic Installer Troubleshooter

Diagnoses failures from any Windows software installer monitored by Smart Installer AI. Accepts structured failure logs with fields like `installationOutcome`, `error.code`, `exitCode`.

**Output format (structured):**
```
Root Cause:           <one sentence>
Confidence:           High | Medium | Low
Evidence:             <what in the log matched>
Recommended Fixes:    1. ... 2. ... 3. ...
Verification Commands: - <command>
Escalation:           <when and to whom>
```

**Confidence scoring:**
| Level | Condition |
|---|---|
| High | Exact error code or signature match |
| Medium | Similar symptoms without exact codes |
| Low | Generic installation failure, insufficient logs |

## Errors Covered

### Ollama (`rag_docs/`)

| File | Error |
|---|---|
| `path_error.md` | `ollama` not recognized / missing PATH |
| `missing_exe.md` | `ollama.exe` missing after install |
| `server_timeout.md` | Timed out waiting for server to start |
| `connection_refused.md` | Could not connect to running Ollama instance |
| `proxy_issue.md` | Pull manifest failed / network issues |
| `antivirus_block.md` | Access denied / permission errors |
| `gpu_detection.md` | No compatible GPU found |
| `cuda_failure.md` | CUDA / ROCm initialization failed |
| `model_download.md` | Model download interrupted |
| `disk_full.md` | No space left on device |
| `port_conflict.md` | Port 11434 already in use |

### Generic Installer (`rag/`)

| File | Error Code | Trigger |
|---|---|---|
| `gui_install_incomplete.md` | `GUI_INSTALL_INCOMPLETE` | exitCode=0, app not installed |
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

## Extending the Knowledge Base

Add a new `.md` file to `rag_docs/` (Ollama) or `rag/` (generic installer) using this template:

```markdown
# Category: <ERROR_CODE>

## Error Signature
- <exact log string or field value>

## Meaning
<one sentence explanation>

## Common Causes
- <cause 1>

## Recommended Actions
- <fix 1>

## Confidence Scoring
- High: <exact match condition>
- Medium: <partial match condition>
```

No code changes needed — both pipelines auto-load all `.md` files from their respective folders on startup.
