# Category: DISK_SPACE_FAILURE

## Error Signature
- No space left on device
- Disk full
- Insufficient storage

## Common Causes
- Target drive has insufficient free space
- Temp directory on system drive is full

## Recommended Actions
- Free storage on target drive
- Move installation location to a drive with more space
- Clear temp files: del /q /s %TEMP%\*

## Diagnostic Commands
- dir C:\ (check free space)
- where /r C:\ *.tmp

## Confidence Scoring
- High: Explicit disk full or no space error in logs
- Medium: Installation failed mid-extract without other error
