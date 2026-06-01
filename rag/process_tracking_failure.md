# Category: PROCESS_TRACKING_FAILURE

## Error Signature
- COLLECTOR_ERROR
- Process tracking exception
- 'ProcessCollector' object has no attribute '_collect_tree_pids'

## Meaning
Smart Installer AI monitoring framework failed to collect process information.

## Impact
Installation result may be incomplete or unreliable due to monitoring failure.

## Common Causes
- Bug in ProcessCollector implementation
- Process exited before tracking began
- Insufficient permissions to read process tree

## Recommended Actions
- Fix collector implementation: verify _collect_tree_pids method exists
- Retry process monitoring after fix
- Fall back to parent PID tracking as interim workaround
- Enable debug logging for collector

## Confidence Scoring
- High: COLLECTOR_ERROR or exact exception message in logs
- Medium: Installation result marked unreliable without specific error
