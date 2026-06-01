# Category: NETWORK_FAILURE

## Error Signature
- Download failed
- Connection timeout
- TLS error
- SSL handshake failed

## Common Causes
- No internet connection
- Firewall blocking installer
- Proxy misconfiguration
- DNS resolution failure

## Recommended Actions
- Verify internet: ping google.com
- Disable VPN temporarily
- Configure proxy settings
- Check firewall rules for installer process

## Diagnostic Commands
- ping google.com
- ipconfig /all
- netstat -ano

## Confidence Scoring
- High: Explicit download failed or TLS error in logs
- Medium: Installer stalled at download step with no network error
