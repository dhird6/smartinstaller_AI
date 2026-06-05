# Category: AUTOCAD_DEPENDENCY_FAILURE

## Error Signature
- VC++ runtime missing
- .NET mismatch
- Licensing service not found
- Required component missing
- DLL not found

## Meaning
Autodesk installation failed because required runtime dependencies (Visual C++, .NET, FlexNet licensing) are missing or incompatible.

## Common Causes
- Missing or incompatible Visual C++ redistributable (2010, 2013, 2015-2022)
- .NET Framework version mismatch
- FlexNet licensing service not installed or corrupted
- Missing DirectX or OpenGL components
- Side-by-side assembly conflicts

## Recommended Actions
- Install latest Visual C++ Redistributable (x86 and x64) from Microsoft
- Install required .NET Framework version
- Repair or reinstall FlexNet licensing service
- Run Autodesk Genuine Service repair
- Use Autodesk Installation Diagnostic Assistant (AIDA) for dependency scan

## Verification Commands
- reg query HKLM\SOFTWARE\Microsoft\VisualStudio
- dotnet --list-runtimes
- sc query FlexNet Licensing Service

## Confidence Scoring
- High: Specific missing runtime or DLL named in error logs
- Medium: Application crashes on launch after install
