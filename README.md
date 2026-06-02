# SmartInstall AI — Installation Agent

Automated installer intake, one-command monitored installation, failure detection, and RAG-ready JSON evidence reports.

## User workflow (3 steps)

1. **Copy** an installer into `installers/`
2. **Run** one command
3. **Open** the report in `reports/`

```powershell
cd smartinstaller_AI
.\.venv\Scripts\Activate.ps1
pip install -e .

# Copy your installer, e.g. npp.8.9.6.2.Installer.x64.exe → installers\

python app.py run
# or: smartinstall run
```

No manual paths, session setup, or separate log collection commands required.

## Project layout

```text
smartinstaller_AI/
├── app.py                    ← python app.py run
├── installers/               ← drop .exe / .msi here
├── reports/                  ← published JSON reports
├── logs/                     ← application.log (agent)
├── sessions/                 ← per-run artifacts + session summaries
├── config/smartinstall.config.json
└── src/smartinstall/
```

## CLI commands

| Command | Description |
|---------|-------------|
| `smartinstall run` | Discover newest installer in `installers/`, run full workflow |
| `smartinstall run --installer npp.8.9.6.2.Installer.x64.exe` | Run a specific package |
| `smartinstall run-all` | Run every installer in `installers/` (oldest → newest) |
| `smartinstall install C:\path\setup.exe` | Explicit path (bypasses repository) |
| `smartinstall recover` | Mark interrupted sessions `Incomplete` |
| `smartinstall demo` | Foundation demo (no installer launch) |

### Options for `run` / `run-all`

| Flag | Purpose |
|------|---------|
| `--installer NAME` | Select installer file (default: newest in `installers/`) |
| `--product-name` | Application label in reports |
| `--tag` | Correlation tag (e.g. ticket ID) |
| `--args "/S"` | Silent install arguments |
| `--timeout 3600` | Max seconds to wait |
| `--config path` | Override config file |

## Automated workflow

```text
installers/  →  smartinstall run  →  Session  →  Launch  →  Monitor
    →  Detect failure  →  Collect evidence  →  JSON report  →  reports/
```

## Output artifacts

| Location | Content |
|----------|---------|
| `reports/mingwgetsetup_failure_20260601_<id>.json` | **Single canonical report** (`status` + `errors` + `evidence`) |
| `sessions/<uuid>/` | Captured streams, `collected_logs/`, internal `session.json` |
| `logs/application.log` | Agent structured log |

### What gets captured (EXE / GUI installers)

| Source | When | Stored in report |
|--------|------|------------------|
| stdout / stderr | During install | `status.logFiles`, stream-derived `errors[]` |
| Windows Event Log (Application, System, Setup) | Live + post-install | `evidence.eventLogs`, `errors[]` |
| Discovered `.log` / `.txt` under TEMP, APPDATA, etc. | After install (session window) | `evidence.installerLogFiles`, `errors[]` |
| Child processes (downloaders, helpers) | During install | `evidence.childProcesses`, non-zero exit → `errors[]` |
| WER crash dumps | Post-install | `evidence.crashReports` |
| GUI with exit 0 and no evidence | Heuristic | `GUI_INSTALL_INCOMPLETE` in `errors[]` |

For GUI installers (no `/S`), the agent waits `guiPostInstallGraceSeconds` (default 20s) after the main process exits so late errors (e.g. MinGW download failure dialogs) can land in logs and the Event Log.

Config: `guiPostInstallGraceSeconds`, `maxInstallerLogFiles`, `installerLogSearchDepth` in `config/smartinstall.config.json`.

## Requirements

- Python 3.11+
- Windows (installer execution + Event Log/WER)
- Run PowerShell **as Administrator** for best Event Log coverage

## Development

```powershell
pip install -r requirements.txt
pip install -e .
pytest
```

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Install failed |
| 2 | Crash detected |
| 3 | Agent error |
| 4 | No installer / invalid input |
| 5 | Insufficient privileges |
