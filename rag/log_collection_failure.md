# Category: LOG_COLLECTION_FAILURE

## Error Signature
- Unable to collect logs
- Log files missing

## Common Causes
- Permission issue preventing log directory access
- Collector bug in Smart Installer AI
- Log directory does not exist

## Recommended Actions
- Verify log directory access permissions
- Re-run log collection
- Enable debug logging: set DEBUG=1 before running installer
- Check that log path is correctly configured

## Confidence Scoring
- High: Explicit log collection error in Smart Installer AI output
- Medium: Expected log files absent after installation attempt
