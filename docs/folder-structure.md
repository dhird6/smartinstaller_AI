# Folder Structure Guide

## Project Root Layout

```
smartinstaller_AI/
├── assets/
│   ├── images/          # Company & app logos (configurable branding)
│   └── icons/             # Optional additional icon assets
├── config/
│   └── smartinstall.config.json
├── design/                # UI mockups, design references
├── docs/                  # Project documentation
├── specs/                 # Specification-driven development docs
├── scripts/               # Build and utility scripts
├── src/
│   └── smartinstall/
│       ├── agent/         # Backend orchestration, collectors, SLM
│       ├── core/          # Shared models and types
│       └── ui/            # Desktop application
│           ├── bridge/
│           ├── components/
│           ├── controllers/
│           ├── models/
│           ├── pages/
│           ├── resources/
│           ├── services/
│           ├── shell/
│           ├── theme/
│           ├── widgets/
│           └── workers/
├── tests/
├── installers/            # Drop zone for .exe / .msi
├── reports/               # Generated JSON reports
├── sessions/              # Session output
├── logs/
├── rag_docs/              # RAG knowledge base
├── desktop.py             # Desktop entry point
├── app.py                 # CLI entry point
└── pyproject.toml
```

## UI Package Structure

| Directory | Purpose |
|-----------|---------|
| `ui/shell/` | Application shell — layout, navigation, floating chat |
| `ui/pages/` | Route-level page widgets |
| `ui/components/` | Reusable presentational components |
| `ui/widgets/` | Stateful/complex widgets |
| `ui/services/` | UI business logic (no Qt widgets) |
| `ui/controllers/` | Application controllers |
| `ui/models/` | UI data models |
| `ui/theme/` | Design system tokens and stylesheets |
| `ui/resources/` | Static assets and brand loading |

## Asset Conventions

- **Company logo**: `assets/images/company_logo.{svg,png}`
- **App logo**: `assets/images/app_logo.{svg,png}`
- **Bundled icons**: `src/smartinstall/ui/resources/icons/*.svg`
- **PyInstaller**: Resources resolved via `_MEIPASS` in frozen builds

## Adding New Pages

1. Create page widget in `ui/pages/`
2. Add page index constant in `MainShell`
3. Register in `QStackedWidget` and sidebar nav labels
4. Update specs in `specs/ui-specifications.md`
