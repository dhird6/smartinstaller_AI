# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for SmartInstall AI desktop executable."""

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

project_root = Path(SPECPATH).resolve().parent
src_root = project_root / "src"

block_cipher = None

_test_app = project_root / "installers" / "TestAppSetup.exe"
_harness_scenarios = project_root / "failure_harness" / "config" / "scenarios"
_harness_config = project_root / "failure_harness" / "config" / "harness.config.json"

added_datas = [
    (str(project_root / "config" / "smartinstall.config.json"), "config"),
    (str(project_root / "rag_docs"), "rag_docs"),
    (str(src_root / "smartinstall" / "ui" / "resources"), "smartinstall/ui/resources"),
]
if _test_app.is_file():
    added_datas.append((str(_test_app), "installers"))
if _harness_scenarios.is_dir():
    added_datas.append((str(_harness_scenarios), "failure_harness/config/scenarios"))
if _harness_config.is_file():
    added_datas.append((str(_harness_config), "failure_harness/config"))

_assets_images = project_root / "assets" / "images"
if _assets_images.is_dir():
    added_datas.append((str(_assets_images), "assets/images"))

_brand_logo = project_root / "images" / "logo.png"
if _brand_logo.is_file():
    added_datas.append((str(_brand_logo), "images"))

# langchain_classic uses lazy __getattr__ imports — PyInstaller misses them unless listed.
_chromadb_hidden = [
    m for m in collect_submodules("chromadb") if not m.startswith("chromadb.test")
]
_langchain_hidden = (
    collect_submodules("langchain_classic.chains")
    + collect_submodules("langchain_core")
    + collect_submodules("langchain_chroma")
    + collect_submodules("langchain_ollama")
    + collect_submodules("langchain_text_splitters")
    + _chromadb_hidden
    + [
        "langchain_classic.chains.retrieval",
        "langchain_classic.chains.combine_documents",
        "langchain_classic.chains.combine_documents.stuff",
        "langchain_classic.chains.combine_documents.reduce",
        "langchain_classic",
        "langchain_community",
        "langchain",
    ]
)

hiddenimports = [
    "smartinstall",
    "smartinstall.ui",
    "smartinstall.ui.main",
    "smartinstall.ui.layout.responsive",
    "smartinstall.agent",
    "smartinstall.agent.infrastructure.bundled_assets",
    "smartinstall.agent.slm.rag_engine",
    "failure_harness",
    "failure_harness.orchestrator",
    "failure_harness.test_installer",
    "smartinstall.agent.collectors.registry_collector",
    "smartinstall.agent.collectors.filesystem_collector",
    "win32evtlog",
    "win32evtlogutil",
    "win32api",
    "win32con",
    "pydantic",
    "pydantic_core",
] + _langchain_hidden

try:
    added_datas += collect_data_files("chromadb")
except Exception:
    pass

a = Analysis(
    [str(project_root / "desktop.py")],
    pathex=[str(src_root)],
    binaries=[],
    datas=added_datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "chromadb.server.fastapi",
        "chromadb.test",
        "fastapi",
        "uvicorn",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="SmartInstallAI",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
