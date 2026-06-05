# TestApp Installation Failures — Permissions & UAC

## Symptoms
- Administrator privileges required
- UAC elevation denied or cancelled (exit code 1223)
- Access is denied during installation
- Blocked by Group Policy or AppLocker

## Root Causes
- Installer not running elevated
- User declined UAC prompt
- Enterprise policy restricts software installation
- Antivirus or EDR blocked installer process

## Diagnosis
- Check if running as Administrator: `[Security.Principal.WindowsIdentity]::GetCurrent()`
- Review Windows Event Log for AppLocker blocks (Event ID 8004)
- Verify UAC settings in Local Security Policy

## Resolution
1. Right-click installer and select "Run as administrator"
2. Approve the UAC elevation prompt when it appears
3. Contact IT if Group Policy blocks the installation
4. Add installer to antivirus/EDR exclusion list temporarily
5. Use approved enterprise deployment channel (SCCM/Intune)
