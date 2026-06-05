# TestApp Installation Failures — Enterprise Deployment

## Symptoms
- ERROR: SCCM deployment conflict — package already assigned
- Intune app sequencing dependency not satisfied
- Group Policy restricts software installation

## Root Causes
- Conflicting software deployment from SCCM or Intune
- Missing prerequisite in deployment sequence
- GPO software restriction policy blocking install

## Diagnosis
- Check SCCM Software Center for duplicate assignments
- Review Intune app dependency chain in admin portal
- Run `gpresult /h gp.html` and inspect software restriction policies

## Resolution
1. Remove duplicate SCCM deployment or use repair mode
2. Install Intune prerequisite apps first
3. Request GPO exception from IT or use approved deployment channel
