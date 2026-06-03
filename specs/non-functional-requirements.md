# Non-Functional Requirements

## NFR-001: Performance

- UI SHALL remain responsive during installation monitoring
- Background work SHALL run on QThread workers
- Page transitions SHALL complete within 300ms

## NFR-002: Security

- User input SHALL NOT be passed directly to file paths or subprocess
- Secrets SHALL be loaded from environment variables only
- Logs SHALL NOT contain credentials or PII

## NFR-003: Privacy

- AI inference SHALL run locally via Ollama — no mandatory cloud calls
- Session data SHALL remain on-premises

## NFR-004: Usability

- Minimum window size: 1100×680
- WCAG 2.1 AA contrast for primary text
- Consistent CCTech design language across all screens

## NFR-005: Maintainability

- Specification-driven development with docs in `specs/` and `docs/`
- Modular component architecture
- Type-annotated public APIs

## NFR-006: Deployability

- PyInstaller desktop bundle support
- Configurable via JSON and environment variables
- Custom branding without code changes

## NFR-007: Reliability

- Graceful handling of missing logo assets
- Clear error messages in chat for unknown commands
- Installation failures captured in unified reports

## NFR-008: Compatibility

- Windows 10/11
- Python 3.11+
- PySide6 6.6+
