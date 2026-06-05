# Category: AUTOCAD_PERMISSIONS_SECURITY_FAILURE

## Error Signature
- Access denied
- UAC restriction
- Enterprise policy block
- Antivirus interference
- EDR quarantine

## Meaning
Autodesk installation blocked by insufficient privileges, Windows UAC, enterprise group policy, or antivirus/EDR systems.

## Common Causes
- User does not have local administrator rights
- UAC prompt dismissed or denied
- Enterprise Group Policy blocking installer execution
- Antivirus or EDR quarantining Autodesk executables
- Windows Defender blocking setup components

## Recommended Actions
- Run installer as Administrator (right-click → Run as administrator)
- Check Windows Security → Protection History for quarantined items
- Add Autodesk installation directory to antivirus exclusion list
- Coordinate with IT to temporarily relax Group Policy during install
- Re-run with elevated privileges after restoring quarantined files

## Verification Commands
- whoami /priv
- icacls "C:\Program Files\Autodesk"
- gpresult /r

## Confidence Scoring
- High: Access denied, UAC cancelled, or quarantine entry in logs
- Medium: Installation silently failed on a protected directory
