# TestApp Installation Failures — Localization & Paths

## Symptoms
- ERROR: Unicode path not supported by installer engine
- Non-ASCII characters in installation path
- Regional settings conflict (decimal separator)

## Root Causes
- Installation path contains CJK or other non-ASCII characters
- Locale-specific path encoding issues
- Regional format conflicts with installer parsing

## Diagnosis
- Inspect installation path for non-ASCII characters
- Check system locale: `systeminfo | findstr /B /C:"System Locale"`
- Review installer log for path validation errors

## Resolution
1. Choose an ASCII-only installation path (e.g., `C:\Program Files\TestApp`)
2. Temporarily set system locale to English for installation
3. Use short path (8.3) names if supported by installer
