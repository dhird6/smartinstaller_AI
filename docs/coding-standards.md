# Coding Standards

## General

- **Minimal scope**: Smallest correct diff; no unrelated changes
- **Match conventions**: Read surrounding code before writing
- **Self-documenting code**: Comments only for non-obvious logic
- **Type safety**: Annotate function signatures and public attributes

## Naming

| Element | Convention | Example |
|---------|-------------|---------|
| Modules | snake_case | `floating_chat_widget.py` |
| Classes | PascalCase | `FloatingChatWidget` |
| Functions | snake_case | `load_company_logo_pixmap` |
| Constants | UPPER_SNAKE | `_COMPACT_W` |
| Qt object names | camelCase | `sidebarNav`, `primaryBtn` |

## File Organization

- One primary class per file for UI widgets
- `__init__.py` exports public API only
- Services contain no Qt imports
- Controllers wire services to views

## Error Handling

- User-facing errors → chat system messages via `ChatFormatter`
- Log technical details via agent logger — never expose secrets
- Graceful degradation for missing assets (empty pixmap fallback)

## Imports

- Standard library → third party → local
- Static imports only — no dynamic `__import__`
- Use absolute imports: `from smartinstall.ui...`

## Git

- Conventional commit prefixes: `feat:`, `fix:`, `refactor:`, `docs:`
- One logical change per commit
- Do not commit `.env`, credentials, or session data
