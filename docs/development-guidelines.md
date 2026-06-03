# Development Guidelines

## Setup

```powershell
cd smartinstaller_AI
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[desktop]"
python desktop.py
```

## Coding Standards

### Python

- Python 3.11+ with type hints on public APIs
- Use `from __future__ import annotations` in new modules
- Pydantic models for structured data
- Strict equality (`===` equivalent: `is`, `==` with known types)

### Qt / PySide6

- Prefer composition over deep inheritance
- Use signals/slots for cross-widget communication
- Long operations on `QThread` workers — never block UI thread
- Object names for QSS targeting (e.g., `#primaryBtn`)

### Security

- Validate all external input before file/command operations
- No user input in file paths or subprocess calls
- Secrets via environment variables only
- No `eval`, `exec`, or dynamic imports with user data

## UI Development

1. Read `docs/ui-design-guidelines.md` before adding components
2. Add reusable pieces to `ui/components/`
3. Page-specific layout goes in `ui/pages/`
4. Update relevant spec in `specs/` when behavior changes

## Testing

```powershell
pytest tests/ -v
```

UI logic (formatters, parsers) has unit tests. GUI integration tests are manual.

## Adding Features

1. Update specification in `specs/`
2. Implement with minimal scope
3. Update documentation in `docs/`
4. Run tests and manual desktop verification

## Brand Assets

Override logos by placing files in `assets/images/`:

```
assets/images/company_logo.png
assets/images/app_logo.svg
```

No code changes required — `brand_assets.py` discovers them automatically.
