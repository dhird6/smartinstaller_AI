# Smart Installer AI — Project Overview

Smart Installer AI is an enterprise desktop application developed by **CCTech** (Centre for Computational Technologies). It provides autonomous Windows installation monitoring, evidence collection, unified JSON reporting, and local AI-powered troubleshooting via Ollama RAG.

## Key Features

- **Monitored installations** — Pre/post snapshots, live process monitoring, unified reports
- **Live monitoring dashboard** — Real-time timeline, logs, and progress visualization
- **AI troubleshooting** — Local SLM + RAG for root cause analysis and fix recommendations
- **Enterprise UX** — CCTech-branded PySide6 desktop with floating chatbot and full chat workspace
- **On-premises privacy** — No cloud dependency for diagnosis

## Technology Stack

| Layer | Technology |
|-------|------------|
| Desktop UI | PySide6 (Qt 6) |
| Backend | Python 3.11+ |
| AI | Ollama + LangChain + Chroma |
| Config | Pydantic + JSON |
| Packaging | PyInstaller |

## Entry Points

```bash
python desktop.py          # Desktop GUI (recommended)
python app.py gui          # Alternative GUI launch
python app.py run --installer <name>.exe   # CLI install
```

## Branding

Place logos in `assets/images/`:

- `company_logo.svg` (or `.png`) — CCTech company logo
- `app_logo.svg` — Smart Installer application logo

Both are loaded independently across header, sidebar, splash, chatbot, and dashboard.

## Related Documentation

- [Architecture](./architecture.md)
- [Folder Structure](./folder-structure.md)
- [Development Guidelines](./development-guidelines.md)
- [UI Design Guidelines](./ui-design-guidelines.md)
- [Deployment Guide](./deployment-guide.md)
- [Testing Guide](./testing-guide.md)
- [Contribution Guide](./contribution-guide.md)
