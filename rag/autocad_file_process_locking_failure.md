# Category: AUTOCAD_FILE_PROCESS_LOCKING_FAILURE

## Error Signature
- File in use
- Locked DLL
- Cannot overwrite file
- Pending reboot required
- Process still running

## Meaning
Autodesk installation failed because required files are locked by running Autodesk processes or a reboot is pending from a previous install.

## Common Causes
- AutoCAD or other Autodesk products still running during install
- DLLs locked by AdskLicensingService or related processes
- Pending reboot state from previous Windows or Autodesk update
- Concurrent installer sessions running simultaneously

## Recommended Actions
- Close all running Autodesk applications before installing
- Restart machine to clear pending reboot and file locks
- Use Task Manager to kill any lingering Autodesk processes
- Disable AdskLicensingService before installing: sc stop AdskLicensingService
- Run installer immediately after fresh reboot

## Verification Commands
- tasklist | findstr -i autodesk
- tasklist | findstr -i acad
- reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager" /v PendingFileRenameOperations

## Confidence Scoring
- High: File locked or in-use error in logs
- Medium: Installation fails on file copy step repeatedly
