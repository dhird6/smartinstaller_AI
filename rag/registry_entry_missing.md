# Category: REGISTRY_ENTRY_MISSING

## Error Signature
- Application not detected
- Registry key absent

## Common Causes
- Installer failed to register application in Windows registry
- Silent install skipped registry step
- Permissions prevented registry write

## Recommended Actions
- Run repair installation (if available in Programs and Features)
- Reinstall application
- Run installer as Administrator to ensure registry write access

## Diagnostic Commands
- reg query HKLM\SOFTWARE\<AppName>
- reg query HKCU\SOFTWARE\<AppName>

## Confidence Scoring
- High: Registry key confirmed absent after install
- Medium: Application not appearing in Programs and Features
