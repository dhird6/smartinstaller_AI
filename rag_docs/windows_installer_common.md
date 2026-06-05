# Windows software installer troubleshooting (general)

## Symptoms
- Setup.exe or MSI exits with non-zero code
- "Access denied" or "Requested registry access is not allowed"
- Missing Visual C++ / .NET runtime prerequisites
- Another installation already in progress (MSI error 1618)
- Download or network failure during setup

## Common causes
- Installer not run as Administrator when elevation is required
- Pending reboot from a previous install
- Blocked by antivirus or Controlled Folder Access
- Required redistributable not installed (VC++ 2015–2022, .NET Framework 4.8)
- Corrupted download or incomplete installer package

## Recommended fix
1. Close other installers and wait for Windows Installer / msiexec to finish (error 1618).
2. Run the installer as Administrator (right-click → Run as administrator).
3. Install Microsoft Visual C++ Redistributable (x64 and x86 if needed) and retry.
4. Install .NET Framework 4.8 or the version required by the product documentation.
5. Re-download the installer from the vendor site and verify file size / signature.
6. Temporarily allow the installer folder in antivirus; retry installation.
7. Reboot if a previous install requested restart, then run setup again.

## Notes
- Match recommendations to the **installer name and log messages** in the evidence (e.g. MinGW, VS Code, Chrome).
- Do not confuse third-party installer failures with Smart Installer AI's optional Ollama components.
