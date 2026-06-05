# Category: AUTOCAD_DISK_STORAGE_FAILURE

## Error Signature
- Insufficient disk space
- Temp path corruption
- Filesystem error
- No space left on device

## Meaning
Autodesk installation failed due to insufficient storage, corrupted temp directory, or filesystem errors on the target drive.

## Common Causes
- Insufficient free disk space (Autodesk products require 10–40 GB+)
- Corrupted or full %TEMP% directory
- Filesystem errors on C: or installation target drive
- Temp path set to a network drive or restricted path

## Recommended Actions
- Free at least 20 GB on the installation drive
- Clear temp files: del /q /s %TEMP%\*
- Run disk check: chkdsk C: /f
- Redirect temp path: set TEMP=D:\Temp
- Move installation target to drive with more space

## Verification Commands
- dir C:\ (check free space)
- echo %TEMP%
- chkdsk C: /f /r

## Confidence Scoring
- High: Explicit disk space or filesystem error in logs
- Medium: Installer failed mid-extraction without other error
