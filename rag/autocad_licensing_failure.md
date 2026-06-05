# Category: AUTOCAD_LICENSING_FAILURE

## Error Signature
- License validation failed
- FlexNet error
- License server unreachable
- Clock skew detected
- Entitlement not found

## Meaning
Autodesk product failed to activate or launch due to licensing validation errors, FlexNet issues, or network licensing server problems.

## Common Causes
- Invalid or expired Autodesk subscription
- FlexNet licensing service corrupted or not running
- Network license server unreachable
- System clock out of sync (clock skew > 5 minutes)
- License file corrupted or moved

## Recommended Actions
- Sign out and sign back into Autodesk Account in Autodesk Access
- Repair AdskLicensingService via Autodesk Licensing Repair Tool
- Sync system clock: w32tm /resync
- For network licenses: verify license server is reachable on port 27000
- Run Autodesk License Manager (LMTOOLS) to diagnose FlexNet

## Verification Commands
- sc query AdskLicensingService
- w32tm /query /status
- netstat -ano | findstr 27000

## Confidence Scoring
- High: FlexNet error code, license server unreachable, or clock skew in logs
- Medium: Product launches but immediately asks for activation repeatedly
