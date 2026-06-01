# Category: INSTALL_TIMEOUT

## Error Signature
- installer.timedOut = true

## Meaning
Installer exceeded execution timeout.

## Common Causes
- Slow download
- Installer waiting for user input
- Hung process
- Antivirus interference

## Recommended Actions
- Increase timeout setting
- Disable antivirus temporarily
- Verify network connectivity
- Retry installation

## Confidence Scoring
- High: installer.timedOut = true present in logs
- Medium: Installation hung with no progress for extended period
