# Category: AUTOCAD_INSTALLER_ENGINE_FAILURE

## Error Signature
- MSI rollback initiated
- Bootstrapper failure
- Transaction corruption
- Return value 3
- Fatal error during installation

## Meaning
The Autodesk installer engine (MSI/bootstrapper) encountered a fatal error and rolled back the installation.

## Common Causes
- MSI transaction corruption mid-install
- Bootstrapper dependency failure
- Windows Installer service malfunction
- Pending reboot from previous install blocking MSI
- Insufficient permissions for MSI operations

## Recommended Actions
- Restart the machine to clear pending reboot state
- Run: net stop msiserver && net start msiserver
- Clear MSI cache: del /q "%WINDIR%\Installer\*.tmp"
- Re-download and re-run the Autodesk installer
- Enable MSI verbose logging: msiexec /i <pkg> /l*v install.log

## Verification Commands
- sc query msiserver
- dir %WINDIR%\Installer
- reg query HKLM\SYSTEM\CurrentControlSet\Control\Session Manager /v PendingFileRenameOperations

## Confidence Scoring
- High: Return value 3 or MSI rollback in logs
- Medium: Installation rolled back with no clear error message
