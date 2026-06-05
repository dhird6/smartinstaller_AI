# TestApp Installation Failures — Version Compatibility

## Symptoms
- ERROR: Unsupported operating system version
- This product requires Windows 10 version 1903 or later
- Architecture mismatch (x64 required)

## Root Causes
- Installer OS version check failed
- 32-bit OS attempting 64-bit installation
- Plugin or component incompatible with host version

## Diagnosis
- Run `winver` to confirm Windows build
- Check `wmic os get osarchitecture`
- Review installer log for version gate messages

## Resolution
1. Upgrade Windows to a supported version
2. Install the correct architecture build (x64 vs x86)
3. Remove incompatible plugins before retrying installation
