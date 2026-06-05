# TestApp Installation Failures — Updates & Upgrades

## Symptoms
- ERROR: In-place upgrade failed — rollback initiated
- Delta patch corrupted — full reinstall required
- Baseline version mismatch for patch

## Root Causes
- Corrupted delta update package
- Installed baseline does not match patch requirements
- Rollback after failed upgrade left inconsistent state

## Diagnosis
- Compare installed version with patch baseline in release notes
- Verify update package checksum
- Check Windows Installer rollback logs

## Resolution
1. Uninstall current version and perform clean install
2. Download full update package instead of delta patch
3. Repair Windows Installer cache if rollback failed
