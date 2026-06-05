# Autodesk Intelligent Installation & Recovery Platform — Overview

## What This Covers
This knowledge base covers failure diagnosis and remediation for Autodesk enterprise desktop products including AutoCAD, Revit, Inventor, Civil 3D, and related products installed via Autodesk Access or ODIS (On-Demand Install Service).

## Known Autodesk Diagnostic Systems
- **AIDA** (Autodesk Installation Diagnostic Assistant) — built-in diagnostics
- **Autodesk Access** — desktop delivery platform
- **ODIS** (On-Demand Install Service) — package delivery and update service
- **AdskLicensingService** — local licensing daemon
- **FlexNet** — network licensing manager

## Recommended Diagnosis Approach
1. Identify failure category (see taxonomy below)
2. Check relevant log files
3. Apply targeted fix steps
4. Validate with verification commands
5. Escalate to Autodesk support if unresolved after 2 fix attempts

## Log File Locations
- Autodesk installer logs: %TEMP%\Autodesk\
- AdskLicensingService logs: %ProgramData%\Autodesk\Adlm\
- ODIS logs: %LOCALAPPDATA%\Autodesk\ODIS\
- AutoCAD error logs: %APPDATA%\Autodesk\AutoCAD <version>\

## Failure Taxonomy (22 Categories)
1. Download & Acquisition Failures
2. Disk & Storage Failures
3. Permissions & Security Failures
4. Dependency Failures (VC++, .NET, FlexNet)
5. Version Compatibility Failures
6. Registry Failures
7. Service Failures (licensing daemon, background services)
8. Installer Engine Failures (MSI rollback, bootstrapper)
9. File/Process Locking Failures
10. OS-Level Failures (WMI, SFC, DISM)
11. GPU/Driver Failures (OpenGL, DirectX)
12. Licensing Failures (FlexNet, OAuth, clock skew)
13. Cloud/API Failures (OAuth, telemetry)
14. Enterprise Deployment Failures (SCCM, Intune, VDI)
15. Update Failures (delta patch, baseline mismatch)
16. Uninstallation Failures
17. Migration Failures
18. Localization Failures
19. Plugin Ecosystem Failures
20. Human/User Failures
21. Telemetry Failures
22. Rare Edge Cases (certificate expiry, race conditions)

## Confidence Scoring
- **High**: Exact error code or log signature matches a known category
- **Medium**: Symptoms match but no exact error code
- **Low**: Generic failure without sufficient log data

## Escalation
Escalate to Autodesk support if:
- Issue persists after 2 full reinstall attempts
- Enterprise deployment consistently fails across multiple machines
- Licensing errors persist after FlexNet repair
