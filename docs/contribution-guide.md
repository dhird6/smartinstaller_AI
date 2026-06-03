# Contribution Guide

## Getting Started

1. Fork / clone the repository
2. Set up development environment (see [Development Guidelines](./development-guidelines.md))
3. Read [Architecture](./architecture.md) and relevant specs in `specs/`

## Workflow

1. **Spec first** — Update or create specification in `specs/` for new features
2. **Implement** — Follow [Coding Standards](./coding-standards.md)
3. **Test** — Run `pytest` and manual UI verification
4. **Document** — Update `docs/` if behavior or structure changes
5. **Submit** — Pull request with clear description

## Pull Request Checklist

- [ ] Spec updated (if applicable)
- [ ] Code follows CCTech theme and UI guidelines
- [ ] No secrets or credentials committed
- [ ] Tests pass
- [ ] Manual desktop verification completed
- [ ] Documentation updated

## UI Contributions

- Use `CCTechPalette` tokens from `cctech_theme.py`
- Place reusable components in `ui/components/`
- Do not reintroduce docked right-panel chat — use `FloatingChatWidget`
- Test sidebar collapse and floating chat at multiple resolutions

## Reporting Issues

Include:
- Windows version
- Python and PySide6 versions
- Steps to reproduce
- Screenshots for UI issues
- Relevant log excerpts from `logs/`

## Code Review Focus

- Security: input validation, no shell injection
- UX: alignment, no hidden/clipped elements
- Architecture: controllers vs services separation
- Minimal diff scope
