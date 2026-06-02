# Category: ANTIVIRUS_INTERFERENCE

## Error Signature
- Executable disappeared after installation
- Quarantine detected
- File removed by security software

## Common Causes
- Antivirus deleted executable during or after install
- Windows Defender quarantine triggered
- Real-time protection blocked file write

## Recommended Actions
- Check Windows Security → Protection History for quarantined items
- Restore quarantined file
- Add installation directory as antivirus exclusion
- Reinstall application after adding exclusion

## Diagnostic Commands
- Check: %APPDATA%MicrosoftWindows DefenderQuarantine

## Confidence Scoring
- High: File missing after install + quarantine entry found
- Medium: Executable missing after install with no other explanation
