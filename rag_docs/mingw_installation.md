# MinGW / mingw-get-setup installation issues

## Symptoms
- mingw-get-setup.exe exits early or shows download errors
- MinGW packages fail to download or resolve
- Compiler toolchain not found after setup

## Common causes
- Network or proxy blocking the MinGW package mirror
- Antivirus quarantining mingw-get or downloaded packages
- Insufficient disk space under the MinGW install directory
- User cancelled the graphical setup wizard before packages were selected
- PATH not updated after install (gcc/g++ not found in new terminals)

## Recommended fix
1. Re-run mingw-get-setup.exe as Administrator if access errors appear in logs.
2. Confirm internet connectivity and corporate proxy settings; retry package download.
3. In the MinGW Installation Manager, mark required packages (mingw32-base, gcc-g++, etc.) and apply changes.
4. Add the MinGW `bin` directory to the user or system PATH (e.g. `C:\MinGW\bin`).
5. Open a new command prompt and run `gcc --version` to verify the toolchain.
6. If downloads fail repeatedly, try an offline MinGW-w64 distribution or MSYS2 as an alternative.

## Notes
- Exit code 0 with an incomplete wizard often means the installer UI was closed before components were installed.
- Registry or filesystem evidence under `MinGW` or `mingw-get` confirms partial installs.
