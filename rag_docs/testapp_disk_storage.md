# TestApp Installation Failures — Disk & Storage

## Symptoms
- ERROR: Not enough disk space
- No space left on device
- Installation aborted during file copy

## Root Causes
- Target drive has insufficient free space
- Temporary directory full
- Quota restrictions on user profile drive

## Diagnosis
- Check free space on installation drive: `wmic logicaldisk get size,freespace,caption`
- Verify %TEMP% directory is writable and has space
- Review installer log for "112" or "0x80070070" errors

## Resolution
1. Free disk space on the target drive (delete temp files, empty Recycle Bin)
2. Choose a different installation path on a drive with adequate space
3. Clear `%TEMP%` and `%LOCALAPPDATA%\Temp` contents
4. Retry installation after confirming at least 2 GB free space
