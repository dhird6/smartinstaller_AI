# Deployment Guide

## Prerequisites

- Windows 10/11
- Python 3.11+
- Ollama (for AI troubleshooting features)
- Administrator privileges (for monitored installs)

## Development Deployment

```powershell
cd smartinstaller_AI
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[desktop]"
python desktop.py
```

## Configuration

Edit `config/smartinstall.config.json`:

```json
{
  "autoRunSlm": true,
  "slmModel": "phi3:mini",
  "slmEmbeddingModel": "nomic-embed-text",
  "installersDirectory": "installers",
  "reportsDirectory": "reports",
  "outputRoot": "sessions"
}
```

## Ollama Setup

```powershell
ollama pull phi3:mini
ollama pull nomic-embed-text
```

Ensure Ollama is running before using AI diagnosis features.

## Production Build (PyInstaller)

```powershell
.\scripts\build_desktop.ps1
```

Output bundle includes bundled icons and agent code. Place custom logos in `assets/images/` before building.

## Branding Deployment

Copy branded assets to the deployment directory:

```
assets/images/company_logo.png
assets/images/app_logo.svg
```

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `SMARTINSTALL_PROJECT_ROOT` | Override project root path |

## Post-Install Verification

1. Launch `desktop.py` — splash screen shows both logos
2. Verify sidebar navigation and collapse
3. Open floating chatbot (bottom-right FAB)
4. Navigate to Full Chat page
5. Run `list` command in chat to verify backend connectivity
