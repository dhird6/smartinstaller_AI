# API Specifications

## Chat Command API (UI → Controller)

Handled by `DesktopController.handle_user_input(text, parent_window)`.

| Command | Behavior | Response |
|---------|----------|----------|
| `list` | List installers in configured directory | Chat list message |
| `install` | Open file picker (.exe, .msi) | Starts install workflow |
| `browse` | Same as `install` | Starts install workflow |
| `install <name>` | Install named file from installers dir | Starts install workflow |
| Other | Unknown command | Error hint message |

## Event Bus API (Agent → UI)

Bridged via `QtEventBridge.status_update(str)`.

Status strings update:
- Floating chat context line
- Full chat context line
- Monitoring page log and busy state

## Installation Result API

`on_run_completed(AutomatedRunResult, slm_answer?, slm_sources?)`

Updates:
- Monitoring page outcome visualization
- Troubleshooting page error/RAG cards
- Dashboard stats refresh
- Chat install summary message

## SLM Diagnosis API

`on_slm_completed(answer: str, sources: list[str])`

Updates:
- Troubleshooting page with AI diagnosis
- Navigates to Troubleshooting page
- Chat diagnosis message via ChatFormatter

## Configuration API

`SmartInstallConfig` (Pydantic) — loaded from `config/smartinstall.config.json`.

Key fields for UI:

| Field | Type | Default | Purpose |
|-------|------|---------|---------|
| `autoRunSlm` | bool | — | Auto-run diagnosis after install |
| `slmModel` | str | phi3:mini | Ollama model |
| `installersDirectory` | Path | installers | Installer drop zone |
| `outputRoot` | Path | sessions | Session output |
| `reportsDirectory` | Path | reports | Report output |

## Brand Asset API

| Function | Returns | Purpose |
|----------|---------|---------|
| `company_logo_path()` | Path \| None | Resolve company logo |
| `app_logo_path()` | Path \| None | Resolve app logo |
| `load_company_logo_pixmap(size)` | QPixmap | Scaled company logo |
| `load_app_logo_pixmap(size)` | QPixmap | Scaled app logo |

## Session Stats API

`load_dashboard_stats(sessions_dir, reports_dir) → DashboardStats`

Returns: total_sessions, successful, failed, partial, recent_sessions[]
