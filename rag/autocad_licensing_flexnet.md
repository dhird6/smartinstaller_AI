# Category: AUTOCAD_PLUGIN_ECOSYSTEM_FAILURE

## Error Signature
- Plugin API mismatch
- Binary incompatibility
- Add-in failed to load
- Plugin version not supported

## Meaning
AutoCAD or Autodesk product failed to load or install due to incompatible third-party plugins or add-ins.

## Common Causes
- Third-party plugin compiled for older AutoCAD API version
- Binary incompatibility between 32-bit plugin and 64-bit AutoCAD
- Plugin DLL blocked by antivirus or enterprise policy
- Plugin registration failed in AutoCAD profile

## Recommended Actions
- Disable all third-party plugins and test product launch
- Update plugins to versions compatible with current AutoCAD version
- Check plugin vendor website for compatibility matrix
- Remove plugin DLLs from AutoCAD support paths
- Re-register compatible plugins after clean install

## Verification Commands
- dir "C:\Users\%USERNAME%\AppData\Roaming\Autodesk\AutoCAD*\Support"
- Check AutoCAD → Options → Files → Support File Search Path

## Confidence Scoring
- High: Specific plugin or add-in load failure in AutoCAD logs
- Medium: AutoCAD crashes on startup only when plugins are present
