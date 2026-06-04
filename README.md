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
pip install -e ".[desktop]"

# CLI workflow (install + automatic SLM diagnosis)
python app.py run --installer mingw-get-setup.exe

# Desktop enterprise UI (recommended)
python desktop.py
# or: python app.py gui
# Navigate: Home Dashboard | Monitoring | Troubleshooting + right AI Assistant
```

## Desktop application (PySide6) — CCTech Enterprise UI

Premium enterprise shell inspired by [CCTech](https://www.cctech.co.in/):

| Area | Features |
|------|----------|
| **Collapsible sidebar** | CCTech logo & branding, sectioned nav (Dashboard, Monitoring, Troubleshooting, Installation Center, Full Chat) |
| **Home dashboard** | Active/recent/failed installs, success rate, background monitoring status (no browse on home) |
| **Installation Center** | Manual Mode 2: browse, upload, start monitored install |
| **Background service** | Mode 1: auto-detect installers launched from Explorer (`python background_service.py`) |
| **AI Assistant** (right, dockable) | Minimize FAB, compact/docked/fullscreen, welcome + suggested prompts |
| **Monitoring** | Live log viewer (pause/search/filter/export), process stage, real-time event stream |
| **Troubleshooting** | Error logs, root cause, RAG sources, smart error popup + Windows toast notifications |

**CCTech brand logo:** place `images/logo.png` in the project root (`smartinstaller_AI/images/logo.png`). The app uses it for the sidebar, dashboard hero, splash, window icon, and chat UI. Bundled SVG placeholders are not used.

Branding: deep navy + cyan gradients, glass cards, animated background, splash screen on startup.

The desktop app reuses the same backend engines:

- Installation orchestrator
- Monitoring + evidence collectors
- Unified JSON report publisher
- Local SLM/RAG diagnosis

### Dual monitoring modes

| Mode | Workflow |
|------|----------|
| **Automatic (Mode 1)** | User runs installer from Explorer → background service detects process → passive monitoring + toasts |
| **Manual (Mode 2)** | Installation Center → browse/upload → monitored install (existing workflow) |

Chat commands:

- `list` — show installers in `installers/`
- `install <file-name>` — run monitored install + SLM
- **Installation Center** — browse/upload `.exe` / `.msi` for manual monitoring

### Background monitoring service

```powershell
python background_service.py
```

Runs installer detection, evidence collection, Windows notifications, and writes `sessions/monitoring_state.json` for dashboard sync (also started automatically with `python desktop.py` when `autoMonitorEnabled` is true).

### System tray (always-on)

- Close the dashboard → app stays in the **system tray** (`minimizeToTray`: true by default).
- Start tray-only: `python desktop.py --tray`
- Tray menu: open dashboard, live monitoring, pause/resume auto-detect, auto-start at login, view last failure.

### Windows Service (SCM)

Register monitoring as a true Windows Service (runs without UI, even when no user is logged in):

```powershell
# Administrator PowerShell
.\scripts\install_windows_service.ps1

# Or manually:
python smartinstall_service.py install
python smartinstall_service.py start
python app.py service stop
```

Service name: `SmartInstallAIMonitor`

### MSI / UAC parent-chain detection

Automatic mode resolves installer chains:

- `msiexec.exe /i package.msi` → monitors **msiexec PID**, records **.msi path**
- UAC (`consent.exe` → elevated `setup.exe`) → flags **elevation** and walks parents
- Dedupes wrapper + child so the same install is not monitored twice

### User-initiated only (tracks the real install)

Automatic monitoring uses **launch tracking**, not a full-machine scan:

1. Remembers process IDs from the last poll — only **new** processes are considered.
2. Requires the installer to be started from **Explorer** (or Open with / browser / UAC→Explorer).
3. One **launch ID** per install — `setup.exe` + its child `msiexec` share a single session.
4. Ignores Windows Update, silent MSI, SYSTEM accounts, and cached `Windows\Installer` paths.

Anti-loop settings in `smartinstall.config.json`:

| Key | Default | Purpose |
|-----|---------|---------|
| `autoMonitorMaxProcessAgeSeconds` | 120 | Only brand-new installer processes |
| `autoMonitorCooldownSeconds` | 600 | Same installer not monitored again for 10 min |
| `autoMonitorMaxConcurrent` | 1 | One automatic session at a time |

### Test installation issues (QA only)

Simulate errors during monitoring to validate live logs, toasts, and troubleshooting:

1. `config/test_installation_issues.json` — edit scenarios (`issues[]`; set each `enabled: true`)
2. `config/test_installation_issues.README.md` — field reference
3. In `smartinstall.config.json`: `"enableTestIssueInjection": true`
4. In the issues file: `"enabled": true`
5. Restart the app; run any install (or `testing/run_slow_test_installer.bat` for a 45s dummy installer)

Default QA scenario `vcredist_before_post_snapshot` fires **before post-snapshot**. Injected errors appear in live logs, Windows toasts, **Live Monitoring** (AI analysis panel), **Troubleshooting**, and the final report (`sessions/.../test_injected_issues.log`). When any installer is detected, a toast confirms real-time monitoring is active.

**Never enable `enableTestIssueInjection` in production.**

### Auto-start at login (further enhancement)

Set `"autoStartAtLogin": true` in `config/smartinstall.config.json`, or enable **Enable auto-start at login** from the tray menu. Launches `desktop.py --tray` at user logon.

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

## Packaging (SmartInstallAI.exe)

```powershell
# Close SmartInstallAI.exe if it is running, then:
.\scripts\build_desktop.ps1
```

Output: `dist\SmartInstallAI.exe`

If you see `ModuleNotFoundError: langchain_classic.chains.retrieval`, rebuild with the latest
`packaging\SmartInstallAI.spec` (LangChain uses lazy imports that PyInstaller must bundle explicitly).

Requirements on target machine:

- Windows 10/11
- Ollama running locally with `phi3:mini` and `nomic-embed-text`
- Run as Administrator for full registry/event log coverage

The bundle includes `config/` and `rag_docs/`. Installer/session folders are created next to the executable.
