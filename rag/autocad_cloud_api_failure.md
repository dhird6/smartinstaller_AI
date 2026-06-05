# Category: AUTOCAD_CLOUD_API_FAILURE

## Error Signature
- Telemetry outage
- OAuth failure
- API endpoint unreachable
- Authentication service error

## Meaning
Autodesk installer or product failed due to inability to reach Autodesk cloud APIs for authentication, telemetry, or entitlement verification.

## Common Causes
- Autodesk Identity Service (IDS) unreachable
- OAuth token expired or invalid
- Corporate firewall blocking Autodesk API endpoints
- Telemetry service outage on Autodesk side

## Recommended Actions
- Check Autodesk Health Dashboard for service outages
- Allow Autodesk API endpoints through corporate firewall
- Clear Autodesk Access credentials and re-authenticate
- Try installation on a network without proxy restrictions
- Use offline activation if persistent

## Verification Commands
- ping accounts.autodesk.com
- curl https://accounts.autodesk.com (check reachability)
- netstat -ano

## Confidence Scoring
- High: OAuth or API endpoint error explicitly in logs
- Medium: Authentication step hangs indefinitely during installation
