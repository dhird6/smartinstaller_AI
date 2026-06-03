# Testing Guide

## Running Tests

```powershell
cd smartinstaller_AI
.\.venv\Scripts\Activate.ps1
pytest tests/ -v
```

With coverage:

```powershell
pytest tests/ --cov=smartinstall --cov-report=term-missing
```

## Test Categories

| Category | Location | Scope |
|----------|----------|-------|
| Chat formatting | `tests/test_chat_formatter*.py` | Message formatting, sections |
| SLM parsing | `tests/test_slm_response_parser.py` | RAG response parsing |
| Agent/orchestration | Other `tests/test_*.py` | Backend logic |

## Manual UI Testing Checklist

### Layout & Navigation
- [ ] App launches without errors at 1480×920
- [ ] Minimum size 1100×680 — no clipped content
- [ ] Sidebar expands/collapses smoothly
- [ ] All 4 nav items work: Dashboard, Monitoring, Troubleshooting, Full Chat
- [ ] Page transitions animate correctly

### Floating Chatbot
- [ ] FAB visible bottom-right on dashboard
- [ ] Click FAB opens compact chat window
- [ ] Minimize closes to FAB
- [ ] Maximize enlarges window; restore returns to compact
- [ ] Close hides chat window
- [ ] Chat does not occupy layout space (content full width)

### Full Chat Page
- [ ] Sidebar "Full Chat" shows full-page workspace
- [ ] Message history preserved when switching from floating chat
- [ ] Light theme applied on full chat page

### Branding
- [ ] Company logo in sidebar, header, splash
- [ ] App logo in header, dashboard hero, chat header
- [ ] Custom logos in `assets/images/` load correctly

### Functional
- [ ] `list` command returns installers
- [ ] Install workflow navigates to Monitoring
- [ ] Status updates appear in chat and monitoring log
- [ ] SLM diagnosis navigates to Troubleshooting (if enabled)

## Adding Tests

- Unit test UI services and formatters (no Qt required)
- Avoid GUI automation unless CI infrastructure supports it
- Mock file system and config for agent tests
