# Category: AUTOCAD_ENTERPRISE_DEPLOYMENT_FAILURE

## Error Signature
- SCCM deployment failed
- Intune deployment error
- VDI environment conflict
- Group Policy conflict
- Silent install failure in enterprise

## Meaning
Autodesk product deployment failed in an enterprise environment due to SCCM/Intune sequencing issues, VDI restrictions, or Group Policy conflicts.

## Common Causes
- SCCM/Intune deployment sequence conflict
- VDI environment lacking required GPU or disk resources
- Group Policy blocking installer or registry writes
- Silent install flags incompatible with Autodesk bootstrapper
- MSI transform (MST) file outdated or corrupt

## Recommended Actions
- Review SCCM/Intune deployment logs for sequencing errors
- Ensure deployment runs under SYSTEM account with admin rights
- Update MST transform files for current Autodesk version
- Test with direct manual install to isolate deployment tool issues
- Coordinate with IT to whitelist Autodesk installer in Group Policy

## Verification Commands
- gpresult /r
- eventvwr → Application and Services Logs → Microsoft → Windows → AppXDeployment

## Confidence Scoring
- High: SCCM/Intune error code in deployment logs
- Medium: Installation succeeds manually but fails via deployment tool
