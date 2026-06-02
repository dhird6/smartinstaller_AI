# Category: PERMISSION_DENIED

## Error Signature
- Access denied
- Permission denied
- Unauthorized access

## Common Causes
- Non-admin user privileges
- Write-protected install directory
- Group policy restriction

## Recommended Actions
- Run installer as Administrator (right-click → Run as administrator)
- Change install directory to user-writable path
- Verify folder permissions: icacls <install_path>

## Diagnostic Commands
- whoami /priv
- icacls <install_path>

## Confidence Scoring
- High: Exact "Access denied" or "Permission denied" in logs
- Medium: Installation silently failed on a protected directory
