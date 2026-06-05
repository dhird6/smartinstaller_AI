# Category: AUTOCAD_SERVICE_FAILURE

## Error Signature
- Licensing daemon failed to start
- Background service startup error
- AdskLicensingService not running
- Service timeout

## Meaning
Autodesk installation or startup failed because a required background service (licensing, telemetry, or platform service) could not start.

## Common Causes
- AdskLicensingService or FlexNet service failed to start
- Port conflict with another application
- Service account permissions insufficient
- Previous service installation corrupted

## Recommended Actions
- Start AdskLicensingService manually: sc start AdskLicensingService
- Repair Autodesk licensing components via Control Panel
- Check Windows Event Viewer → System for service errors
- Reinstall Autodesk Desktop Licensing Service
- Ensure ports 2080 and 27000 are not blocked by firewall

## Verification Commands
- sc query AdskLicensingService
- sc query "FlexNet Licensing Service"
- netstat -ano | findstr 2080

## Confidence Scoring
- High: Explicit service start failure or timeout in logs
- Medium: Licensing errors on Autodesk product launch after install
