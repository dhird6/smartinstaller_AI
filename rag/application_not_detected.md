# Category: APPLICATION_NOT_DETECTED

## Error Signature
- Installer succeeded but application not found
- exitCode = 0, installationCompleted = false

## Detection Rules
- exitCode = 0 (installer exited cleanly)
- installationCompleted = false (post-install verification failed)

## Common Causes
- Application installed to non-standard path
- Registry entry not created by installer
- Silent install used a different target directory

## Verification Steps
- Search for executable: where <app> or dir /s *.exe
- Search registry: reg query HKLMSOFTWARE
- Check common install directories

## Recommended Actions
- Verify custom installation path used during install
- Verify application executable exists on disk
- Run repair mode or reinstall

## Diagnostic Commands
- where <executable>
- dir /s *.exe
- reg query HKLM\SOFTWARE\<AppName>

## Confidence Scoring
- High: exitCode=0 with installationCompleted=false confirmed
- Medium: Application not launchable after install with exit code 0
