# TestApp Installation Failures — MSI & Installer Engine

## Symptoms
- MSI rollback initiated after fatal error
- Exit code 1603: Fatal error during installation
- Package verification failed (1620)
- Bootstrapper failed to launch main installer

## Root Causes
- Windows Installer service corruption
- Previous failed installation left pending transactions
- Package tampered or incomplete
- Conflicting product version already installed

## Diagnosis
- Check Windows Installer log for "Return value 3" (fatal error)
- Run `msiexec /unregister` then `msiexec /register` (Administrator)
- Verify no other installation is in progress (1618)
- Review rollback log section in verbose MSI log

## Resolution
1. Restart Windows Installer service: `net stop msiserver && net start msiserver`
2. Clear pending reboot flag if safe to do so
3. Remove conflicting product version via Programs and Features
4. Re-download complete installer package
5. Run Microsoft Program Install and Uninstall Troubleshooter
