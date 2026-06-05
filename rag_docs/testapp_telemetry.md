# TestApp Installation Failures — Telemetry & Diagnostics

## Symptoms
- ERROR: Logging service failed to start
- Diagnostic log file missing — cannot continue verification
- Diagnostic data corrupted

## Root Causes
- Telemetry/logging service blocked or failed to initialize
- Insufficient permissions to write diagnostic logs
- Antivirus quarantined diagnostic output

## Diagnosis
- Verify `%ProgramData%` and `%TEMP%` are writable
- Check Windows Event Log for service startup failures
- Confirm diagnostic directory exists and is not read-only

## Resolution
1. Run installer with administrator privileges
2. Exclude diagnostic output directory from antivirus scanning
3. Clear corrupted diagnostic cache and retry installation
