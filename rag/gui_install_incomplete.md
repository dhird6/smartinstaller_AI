# Category: GUI_INSTALL_INCOMPLETE

## Error Signature
- installationOutcome = Failure
- error.code = GUI_INSTALL_INCOMPLETE
- exitCode = 0
- installationCompleted = false

## Meaning
Installer exited successfully but target application was not installed correctly.

## Common Causes
- User cancelled wizard
- Required components not selected
- Network interruption
- Installation path changed
- Silent installation failure

## Verification
- Check installation directory
- Verify executable exists
- Verify registry entries
- Review screenshots

## Recommended Actions
- Re-run installer
- Select required components
- Verify internet connectivity
- Verify installation path

## Confidence Scoring
- High: Exact match on exitCode=0 and installationCompleted=false
- Medium: Similar incomplete install symptoms without exact codes
