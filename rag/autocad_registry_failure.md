# Category: AUTOCAD_REGISTRY_FAILURE

## Error Signature
- Registry corruption
- Orphaned registry entries
- COM registration failure
- Registry key access denied

## Meaning
Autodesk installation failed due to corrupted, orphaned, or inaccessible Windows registry entries from previous installations.

## Common Causes
- Orphaned registry keys from incomplete previous uninstall
- COM component registration failure
- Registry permissions preventing write access
- Conflicting registry entries from multiple Autodesk versions

## Recommended Actions
- Run Autodesk Uninstall Tool to clean orphaned entries
- Use Microsoft's FixIt tool to clean registry
- Manually remove HKLM\SOFTWARE\Autodesk entries for the failed product
- Run installer as Administrator to ensure registry write access
- Use Registry Editor to grant permissions to Autodesk keys

## Verification Commands
- reg query HKLM\SOFTWARE\Autodesk
- reg query HKCU\SOFTWARE\Autodesk

## Confidence Scoring
- High: COM registration error or registry access denied in logs
- Medium: Product not appearing in Programs and Features after install
