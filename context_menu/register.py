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
TARGETS = [
    r"exefile\shell\SmartInstallAI",       # right-click on .exe
    r"Msi.Package\shell\SmartInstallAI",   # right-click on .msi
]

COMMAND = f'"{PYTHONW}" "{LAUNCHER}" "%1"'
ICON = str(LAUNCHER.parent.parent / "src" / "smartinstall" / "__init__.py")  # fallback


def register() -> None:
    for base_key in TARGETS:
        # Create the menu entry key
        with winreg.CreateKeyEx(winreg.HKEY_CLASSES_ROOT, base_key) as k:
            winreg.SetValueEx(k, "", 0, winreg.REG_SZ, MENU_LABEL)

        # Create the command subkey
        with winreg.CreateKeyEx(winreg.HKEY_CLASSES_ROOT, base_key + r"\command") as k:
            winreg.SetValueEx(k, "", 0, winreg.REG_SZ, COMMAND)

        print(f"Registered: HKCR\\{base_key}")

    print("\nDone. Right-click any .exe or .msi to see 'Monitor with SmartInstaller AI'.")


def unregister() -> None:
    for base_key in TARGETS:
        for sub in [r"\command", ""]:
            try:
                winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, base_key + sub)
                print(f"Removed: HKCR\\{base_key}{sub}")
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
