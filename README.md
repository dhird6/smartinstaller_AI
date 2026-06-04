# SmartInstaller AI — Ollama RAG Pipeline

A fully local RAG system that reads Ollama installation error logs, retrieves the most relevant fix from a structured knowledge base, and returns step-by-step repair instructions using Phi-3 — no cloud APIs required.

## How It Works

```
Error Log  ->  Log Cleaner  ->  ChromaDB Retriever  ->  Phi-3 (local LLM)  ->  Fix Instructions
                                (nomic-embed-text)
```

1. **Log cleaning** — filters raw log to only error/critical/failed lines (last 20 matches)
2. **Embedding** — `nomic-embed-text` converts each KB doc into vectors stored in ChromaDB
3. **Retrieval** — top 2 most semantically similar docs are fetched
4. **Generation** — `phi3:mini` reads retrieved docs and produces numbered fix steps

## Models Used

| Model | Role | Size |
|---|---|---|
| `phi3:mini` | Local LLM for diagnosis | 2.2 GB |
| `nomic-embed-text` | Local embedding model | 274 MB |

Both run inside Ollama — no internet required after initial setup.

## Setup

**1. Install Ollama**

Download from [ollama.com](https://ollama.com) and run the installer.

**2. Pull the required models**

```powershell
ollama pull phi3:mini
ollama pull nomic-embed-text
```

**3. Install Python dependencies**

```powershell
python -m pip install langchain langchain-ollama langchain-chroma langchain-classic chromadb
```

**4. Start Ollama and run**

```powershell
ollama serve        # keep this running in a separate terminal
python rag.py
```

## Usage

By default `rag.py` runs against a mock ROCm/RDNA2 error log. To diagnose a real failure, replace `mock_error_log` in [rag.py](rag.py) with the contents of your Ollama server log:

```python
import os
from pathlib import Path

log_path = Path(os.environ["LOCALAPPDATA"]) / "Ollama" / "server.log"
mock_error_log = log_path.read_text(encoding="utf-8", errors="ignore")
```

## Sample Output

```
Loaded 11 knowledge base documents.

### PHI-3 DIAGNOSIS & REPAIR INSTRUCTIONS: ###

1. Update AMD GPU drivers for RDNA2/ROCm compatibility
2. Run nvidia-smi to verify driver installation
3. Set GGML_VK_VISIBLE_DEVICES to control GPU visibility
4. Set OLLAMA_NUM_GPU=0 to fall back to CPU inference

[Retrieved from: cuda_failure.md, gpu_detection.md]
```

## Project Structure

```
smartinstaller_AI/
├── rag.py              <- main RAG pipeline
└── rag_docs/           <- knowledge base (one .md file per error type)
    ├── antivirus_block.md
    ├── connection_refused.md
    ├── cuda_failure.md
    ├── disk_full.md
    ├── gpu_detection.md
    ├── missing_exe.md
    ├── model_download.md
    ├── path_error.md
    ├── port_conflict.md
    ├── proxy_issue.md
    └── server_timeout.md
```

## Errors Covered

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

## Extending the Knowledge Base

Add a new `.md` file to `rag_docs/` — no code changes needed, it is loaded automatically on startup.

```markdown
# Error: <title>

## Symptoms
- <what the user sees>

## Root Causes
- <why it happens>

## Diagnosis
- <how to investigate>

## Resolution
- <step-by-step fix>
```
