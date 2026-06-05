# Category: AUTOCAD_OS_LEVEL_FAILURE

## Error Signature
- WMI corruption
- Windows Update conflict
- Missing system components
- OS component error

## Meaning
Autodesk installation failed due to corrupted or missing Windows OS components such as WMI, Windows Update, or system libraries.

## Common Causes
- Corrupted WMI repository
- Conflicting Windows Update in progress
- Missing or corrupted system DLLs
- Windows component store corruption (CBS/DISM errors)

## Recommended Actions
- Repair WMI: winmgmt /resetrepository
- Run SFC: sfc /scannow
- Run DISM: DISM /Online /Cleanup-Image /RestoreHealth
- Pause Windows Update before installing Autodesk products
- Ensure all pending Windows Updates are installed first

## Verification Commands
- sfc /scannow
- DISM /Online /Cleanup-Image /CheckHealth
- winmgmt /verifyrepository

## Confidence Scoring
- High: WMI or system component error in installation logs
- Medium: Installer crashes with no application-level error
