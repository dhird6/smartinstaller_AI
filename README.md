# SmartInstall AI

Automated installer execution + failure evidence collection + local SLM diagnosis.

## End-to-end workflow

1. Put installer in `installers/`
2. Run monitored install (`python app.py run --installer <name>.exe`)
3. SmartInstall auto-passes the generated JSON report to SLM
4. Review diagnosis output in console (and report in `reports/`)

```text
Installer -> Monitor -> smartinstall_report.json -> RAG retrieval -> Phi-3 fix steps
```

## Core commands

```powershell
cd smartinstaller_AI
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e .

# run installer monitoring + automatic SLM diagnosis
python app.py run --installer mingw-get-setup.exe
```

## SmartInstall output

The canonical run artifact is one JSON report in `reports/`:

- `status`: installer metadata + final outcome
- `errors[]`: normalized errors from streams, event log, installer logs, child exits, crash signals
- `evidence`: event logs, installer log files, process tree, crash reports, MSI diagnostics

For GUI installers, the agent waits `guiPostInstallGraceSeconds` after installer exit to capture delayed failures.

## Local SLM/RAG

`rag.py` accepts:

- `--report <path>`: reads SmartInstall JSON report (recommended)
- `--text "<raw error text>"`: fallback manual input
- `--docs-path <path>`: alternate RAG knowledge-base folder

Note: during `python app.py run` and `python app.py run-all`, SmartInstall now automatically calls `rag.py --report <generated_report_path>` after each run.

Knowledge docs are loaded from `rag_docs/*.md`, embedded with `nomic-embed-text`, and resolved by `phi3:mini`.

## Requirements

- Python 3.11+
- Windows (installer execution + Event Log/WER)
- Ollama with:
  - `phi3:mini`
  - `nomic-embed-text`

Pull models:

```powershell
ollama pull phi3:mini
ollama pull nomic-embed-text
```

## Development

```powershell
pytest
```
