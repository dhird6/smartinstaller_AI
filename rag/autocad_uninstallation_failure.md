# Category: AUTOCAD_UNINSTALLATION_FAILURE

## Error Signature
- Uninstall cache missing
- Shared dependency conflict
- Cannot remove component
- Uninstaller not found

## Meaning
Autodesk product uninstallation failed due to missing uninstall cache, shared dependency conflicts, or corrupted uninstaller.

## Common Causes
- Windows Installer cache for Autodesk MSI deleted or moved
- Shared component relied on by another Autodesk product
- Uninstaller executable missing from installation directory
- Previous partial uninstall left inconsistent state

## Recommended Actions
- Use Autodesk Uninstall Tool (recommended over Windows uninstaller)
- Run Autodesk Genuine Service cleanup utility
- Manually remove residual files from C:\Program Files\Autodesk
- Clean registry entries: HKLM\SOFTWARE\Autodesk\<product>
- Use Microsoft's Windows Installer Cleanup utility for stubborn MSI entries

## Verification Commands
- reg query HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall
- dir "C:\Program Files\Autodesk"

## Confidence Scoring
- High: Uninstall cache missing or shared component conflict in logs
- Medium: Product still appears in Programs and Features after uninstall
