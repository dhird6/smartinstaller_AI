# Test installation issues (QA only)

Edit `test_installation_issues.json` to add or tune **simulated** errors while testing Smart Installer monitoring, toasts, and AI troubleshooting.

## Enable (both required)

1. In `smartinstall.config.json`:

```json
"enableTestIssueInjection": true
```

2. In `config/test_installation_issues.json`:

```json
"enabled": true
```

3. Enable individual scenarios under `issues[].enabled`.

4. Restart `python desktop.py` or the background service.

## Add a new test issue

Copy an entry in the `issues` array:

| Field | Description |
|-------|-------------|
| `id` | Unique name (for logs) |
| `enabled` | `true` to activate this scenario |
| `trigger` | `during_install`, `before_post_snapshot` (fires when installer exits, before post-snapshot), or `on_complete` |
| `delaySeconds` | Seconds after install starts before firing (`during_install` only) |
| `installerNamePattern` | `*` = all, or `setup*.exe`, `*.msi`, etc. |
| `code` | Error code shown in UI/report |
| `message` | Error text |
| `suggestedFix` | Shown in notifications / troubleshooting (interim until SLM completes) |
| `forceFailedOutcome` | `true` marks install as failed in the report |
| `showNotification` | Windows toast when error fires |

When the install fails, **autoRunSlm** (default `true`) runs the local SLM. Full analysis appears in **Live Monitoring**, **Troubleshooting**, and a second Windows toast when SLM finishes.

**Never** set `enableTestIssueInjection` on end-user or production machines.
