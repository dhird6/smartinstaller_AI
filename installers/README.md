# Installers Repository

Copy `.exe` or `.msi` installation packages into this folder.

Then run from the project root:

```powershell
python app.py run
```

or:

```powershell
smartinstall run
```

The agent picks the **newest** file by default. To run a specific package:

```powershell
smartinstall run --installer npp.8.9.6.2.Installer.x64.exe
```

**Note:** Placeholder files are ignored; only real installer binaries are executed.
