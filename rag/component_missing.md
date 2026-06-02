# Category: COMPONENT_MISSING

## Error Signature
- Required executable missing
- Required package missing
- DLL not found

## Common Causes
- Partial installation completed
- User skipped optional package selection in wizard
- Dependency not bundled in installer

## Recommended Actions
- Install missing package or dependency
- Re-run installer and select all required components
- Use repair mode if available in installer

## Diagnostic Commands
- where <executable>
- dir /s *.exe
- dir /s *.dll

## Confidence Scoring
- High: Specific missing component named in error
- Medium: Application launches but crashes with missing module error
