# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — BPDPManager jako macOS .app (onedir, Apple Silicon).

Nespouštěj přímo; použij ``scripts/build_macos.sh`` (build mimo iCloud, podpis,
smoke test, DMG). Verze se čte z jediného zdroje pravdy —
``src/bpdpmanager/__init__.py`` (``__version__``).
"""

import re
from pathlib import Path

ROOT = Path(SPECPATH).resolve().parent  # noqa: F821 — SPECPATH dodá PyInstaller
SRC = ROOT / "src"
PKG = SRC / "bpdpmanager"
VERSION = re.search(
    r'__version__\s*=\s*"([^"]+)"', (PKG / "__init__.py").read_text(encoding="utf-8")
).group(1)

# Data se hledají přes Path(__file__) relativně k balíčku → musí ležet
# v bundlu jako bpdpmanager/resources (stejná struktura jako ve zdrojích).
datas = [
    (str(PKG / "resources"), "bpdpmanager/resources"),
    # --load-demo (fiktivní data) — v bundlu v examples/ vedle balíčku.
    (str(ROOT / "examples" / "seed_demo.json"), "examples"),
]

a = Analysis(  # noqa: F821
    [str(ROOT / "packaging" / "launcher.py")],
    pathex=[str(SRC)],
    datas=datas,
    hiddenimports=[],
    # Testovací nástroje do aplikace nepatří. (PIL NE — xlsx_image_in_cell ho
    # volitelně používá na velikost loga v posudku; bez něj by se appka
    # chovala jinak než při běhu ze zdrojů.)
    excludes=["tkinter", "pytest", "_pytest", "pytestqt"],
    noarchive=False,
)
pyz = PYZ(a.pure)  # noqa: F821

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="BPDPManager",
    console=False,
    argv_emulation=False,
    target_arch="arm64",
    codesign_identity=None,  # ad-hoc podpis dodělá build skript
    entitlements_file=None,
)

coll = COLLECT(  # noqa: F821
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="BPDPManager",
)

app = BUNDLE(  # noqa: F821
    coll,
    name="BPDPManager.app",
    icon=str(PKG / "resources" / "icons" / "app_icon.icns"),
    bundle_identifier="io.github.safronus.bpdpmanager",
    version=VERSION,
    info_plist={
        "CFBundleName": "BPDPManager",
        "CFBundleDisplayName": "BPDPManager",
        "CFBundleShortVersionString": VERSION,
        "CFBundleVersion": VERSION,
        "NSHighResolutionCapable": True,
        "LSMinimumSystemVersion": "12.0",
        "LSApplicationCategoryType": "public.app-category.education",
        "NSHumanReadableCopyright": "© safronus · MIT License",
    },
)
