# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for TestAppSetup.exe — failure injection test application."""

import sys
from pathlib import Path

project_root = Path(SPECPATH).resolve().parent.parent
src_path = project_root / "src"

_datas = []
_brand_logo = project_root / "images" / "logo.png"
if _brand_logo.is_file():
    _datas.append((str(_brand_logo), "images"))

a = Analysis(
    [str(src_path / "failure_harness" / "test_installer.py")],
    pathex=[str(src_path)],
    binaries=[],
    datas=_datas,
    hiddenimports=[
        "failure_harness",
        "failure_harness.installer_gui",
        "failure_harness.models",
        "failure_harness.engine",
        "failure_harness.categories",
        "failure_harness.scenario_manager",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="TestAppSetup",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
