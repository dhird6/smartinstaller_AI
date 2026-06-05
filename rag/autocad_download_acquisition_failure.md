# Category: AUTOCAD_DOWNLOAD_ACQUISITION_FAILURE

## Error Signature
- Download failed
- CDN error
- Corrupt download
- Authentication token failure
- Proxy connection refused

## Meaning
Autodesk installer failed to acquire installation packages due to network, CDN, authentication, or proxy issues.

## Common Causes
- CDN outage or unreachable endpoint
- Corrupt or incomplete download
- Proxy or VPN blocking Autodesk CDN
- OAuth/token authentication failure
- ODIS (On-Demand Install Service) unable to fetch packages

## Recommended Actions
- Verify internet connectivity and retry
- Disable VPN or configure proxy for Autodesk CDN
- Clear Autodesk download cache and retry
- Re-authenticate Autodesk Access and relaunch installer
- Use offline installer package if network is unreliable

## Verification Commands
- ping autodesk.com
- netstat -ano
- ipconfig /all

## Confidence Scoring
- High: Explicit CDN, download failed, or token error in logs
- Medium: Installer stalled at download step with no progress
