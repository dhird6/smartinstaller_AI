# SmartInstall AI

Automated installer execution + failure evidence collection + local SLM diagnosis.

## End-to-end workflow

1. Put installer in `installers/`
2. Run monitored install (`python app.py run --installer <name>.exe`)
3. Open generated report in `reports/`
4. Run SLM diagnosis using that JSON report (`python rag.py --report <report.json>`)

```text
Installer -> Monitor -> smartinstall_report.json -> RAG retrieval -> Phi-3 fix steps
```

## Core commands

```powershell
cd smartinstaller_AI
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e .

# run installer monitoring
python app.py run --installer mingw-get-setup.exe

# use report JSON as SLM input
python rag.py --report "reports\mingwgetsetup_failure_20260602_<id>.json"
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
