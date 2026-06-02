"""
Register 'Monitor with SmartInstaller AI' right-click menu for .exe and .msi files.
Run once as Administrator:  python context_menu/register.py
To remove:                  python context_menu/register.py --unregister
"""
import argparse
import sys
import winreg
from pathlib import Path

MENU_LABEL = "Monitor with SmartInstaller AI"
LAUNCHER = Path(__file__).resolve().parent / "launcher.pyw"
PYTHONW = Path(sys.executable).parent / "pythonw.exe"

# Registry paths for EXE and MSI file types
# Use HKCU\SOFTWARE\Classes — works without Administrator privileges
# Windows merges HKCU\SOFTWARE\Classes with HKCR at runtime
HIVE = winreg.HKEY_CURRENT_USER
HIVE_PREFIX = r"SOFTWARE\Classes"

TARGETS = [
    r"exefile\shell\SmartInstallAI",       # right-click on .exe
    r"Msi.Package\shell\SmartInstallAI",   # right-click on .msi
]

COMMAND = f'"{PYTHONW}" "{LAUNCHER}" "%1"'


def _full(key: str) -> str:
    return HIVE_PREFIX + "\\" + key


def register() -> None:
    for base_key in TARGETS:
        full = _full(base_key)

        with winreg.CreateKeyEx(HIVE, full) as k:
            winreg.SetValueEx(k, "", 0, winreg.REG_SZ, MENU_LABEL)

        with winreg.CreateKeyEx(HIVE, full + r"\command") as k:
            winreg.SetValueEx(k, "", 0, winreg.REG_SZ, COMMAND)

        print(f"Registered: HKCU\\{full}")

    print("\nDone. Right-click any .exe or .msi > 'Show more options' > 'Monitor with SmartInstaller AI'.")


def unregister() -> None:
    for base_key in TARGETS:
        full = _full(base_key)
        for sub in [r"\command", ""]:
            try:
                winreg.DeleteKey(HIVE, full + sub)
                print(f"Removed: HKCU\\{full}{sub}")
            except FileNotFoundError:
                pass
    print("\nDone. Context menu entry removed.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Register SmartInstaller AI context menu")
    parser.add_argument("--unregister", action="store_true", help="Remove the context menu entry")
    args = parser.parse_args()

    try:
        if args.unregister:
            unregister()
        else:
            register()
    except PermissionError:
        print("ERROR: Run this script as Administrator (right-click → Run as administrator).")
        sys.exit(1)


if __name__ == "__main__":
    main()
