# Category: AUTOCAD_UPDATE_FAILURE

## Error Signature
- Delta patch corruption
- Baseline mismatch
- Update rollback
- Patch application failed

## Meaning
An Autodesk product update failed due to corrupted patch files, baseline version mismatch, or update engine errors.

## Common Causes
- Downloaded delta patch corrupted
- Installed base version does not match patch baseline
- Previous failed update left product in inconsistent state
- Update service interrupted mid-apply

## Recommended Actions
- Uninstall the failed update via Programs and Features
- Download and apply the full installer instead of delta update
- Verify installed base version matches update requirements
- Clear Autodesk update cache and retry
- Use Autodesk Access to trigger clean update

## Verification Commands
- reg query HKLM\SOFTWARE\Autodesk (check installed version)
- dir "%ProgramData%\Autodesk\Updates"

## Confidence Scoring
- High: Delta patch or baseline mismatch error in update logs
- Medium: Update appears to complete but product version unchanged
