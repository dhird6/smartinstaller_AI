# SmartInstaller AI

An autonomous, fully local Ollama installation troubleshooting system powered by Retrieval-Augmented Generation (RAG). It reads error logs, retrieves the most relevant fix from a local knowledge base, and returns step-by-step repair instructions — all without any cloud API calls.

## How It Works

```
Error Log  →  Log Cleaner  →  ChromaDB Retriever  →  Phi-3 (local LLM)  →  Fix Instructions
                               (nomic-embed-text)
```

1. **Log cleaning** — filters raw log output to only error/critical/failed lines
2. **Embedding** — `nomic-embed-text` converts each knowledge base document into vectors stored in ChromaDB
3. **Retrieval** — the top 2 most semantically similar error docs are fetched
4. **Generation** — `phi3:mini` reads the retrieved docs and produces numbered fix steps

## Models Used

| Model | Role | Size |
|---|---|---|
| `phi3:mini` | Local LLM for diagnosis | 2.2 GB |
| `nomic-embed-text` | Local embedding model | 274 MB |

Both run inside Ollama — no internet required after initial setup.

## Project Structure

```
smartinstaller_AI/
├── rag.py              # Main RAG pipeline
└── rag_docs/           # Knowledge base (one file per error type)
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
pip install langchain langchain-community langchain-chroma chromadb
```

**4. Run**

```powershell
python rag.py
```

## Usage

By default `rag.py` runs against a mock error log. To diagnose a real failure, replace `mock_error_log` in [rag.py](rag.py) with the contents of your Ollama log file:

```
%LOCALAPPDATA%\Ollama\server.log
```

Example:

```python
log_path = Path(os.environ["LOCALAPPDATA"]) / "Ollama" / "server.log"
mock_error_log = log_path.read_text(encoding="utf-8", errors="ignore")
```

## Extending the Knowledge Base

To add a new error type, create a new `.md` file in `rag_docs/` following this structure:

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

No code changes needed — `rag.py` automatically loads all `.md` files from `rag_docs/` on startup.

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
