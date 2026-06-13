# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec for CloakBrowser Suite
#
# Build:
#   pyinstaller build/build.spec --clean --noconfirm
#
# Output: dist/cloakbrowser-suite/   (single-directory bundle, includes Chromium)
#
# Build-time requirements:
#   - pip install pyinstaller
#   - pip install -e .   (for cloakbrowser dependency)
#   - Chromium pre-downloaded via:  python -c "from cloakbrowser.download import download_chromium; download_chromium()"
#

import os
import sys
from pathlib import Path

# NOTE: PyInstaller exec's the spec file in a restricted namespace
# without __file__.  We rely on cwd() being the project root (all
# build scripts cd to project root before invoking pyinstaller).
_PROJ = Path.cwd().resolve()

# ══════════════════════════════════════════════════════════════════════════
#  Chromium bundling — detect & queue every file under chromium-{ver}/
# ══════════════════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════════════════
#  Data files: Chromium + frontend dist/
#  Analysis(datas=...) expects (source_path, dest_path) 2-tuples.
#  DO NOT append to a.datas after Analysis — the internal format is
#  (dest, src, 'DATA') 3-tuples and mixing formats breaks normalize_toc.
# ══════════════════════════════════════════════════════════════════════════

_USER_DATAS: list[tuple[str, str]] = []

# ── Frontend dist/ ──────────────────────────────────────────────────────
_FRONTEND = _PROJ / "frontend" / "dist"
if _FRONTEND.is_dir():
    for f in sorted(_FRONTEND.rglob("*")):
        if f.is_file():
            _rel = str(f.relative_to(_FRONTEND.parent))   # "frontend/dist/..."
            _USER_DATAS.append((str(f), _rel))
    print(f"[spec] Frontend: {len([x for x in _USER_DATAS if 'frontend' in x[1]])} files")
else:
    print("[spec] WARNING: frontend/dist/ not found — no UI will be served")

# ── Chromium ────────────────────────────────────────────────────────────
try:
    from cloakbrowser.config import get_cache_dir, get_chromium_version, get_binary_dir

    _CACHE = get_cache_dir()
    _VER  = get_chromium_version()
    _DIR  = get_binary_dir()

    if _DIR.is_dir():
        _mb = sum(f.stat().st_size for f in _DIR.rglob("*") if f.is_file()) / 1_048_576
        print(f"[spec] Bundling Chromium: {_DIR}  ({_mb:.0f} MiB)")

        for f in sorted(_DIR.rglob("*")):
            if f.is_file():
                _rel = str(f.relative_to(_CACHE))   # "chromium-{ver}/chrome"
                _USER_DATAS.append((str(f), _rel))

        print(f"[spec]   → Chromium: {len([x for x in _USER_DATAS if 'chromium' in x[1]])} files")
    else:
        print(f"[spec] WARNING: Chromium directory not found at {_DIR}")
        print("[spec]   Bundle will NOT include Chromium — it will download on first launch.")
except ImportError:
    print("[spec] WARNING: cloakbrowser not importable — Chromium will NOT be bundled")

# ── Also bundle frontend dist/ ──────────────────────────────────────────
_FRONTEND = _PROJ / "frontend" / "dist"
if _FRONTEND.is_dir():
    for f in sorted(_FRONTEND.rglob("*")):
        if f.is_file():
            _rel = str(f.relative_to(_FRONTEND.parent))  # "frontend/dist/..."
            _USER_DATAS.append((_rel, str(f), 'DATA'))
    print(f"[spec] Frontend: {len([x for x in _USER_DATAS if x[0].startswith('frontend')])} files")
else:
    print("[spec] WARNING: frontend/dist/ not found — no UI will be served")

# ══════════════════════════════════════════════════════════════════════════

block_cipher = None

a = Analysis(
    [str(_PROJ / "build" / "entry.py")],
    pathex=[str(_PROJ)],
    binaries=[],
    datas=_USER_DATAS,                # Chromium + frontend all go through constructor
    hiddenimports=[
        "backend.main",
        "backend.database",
        "backend.models",
        "backend.browser_manager",
        "cli.main",
        "cloakbrowser",
        "cloakbrowser.config",
        "cloakbrowser.browser",
        "cloakbrowser.download",
        "cloakbrowser.geoip",
        "uvicorn",
        "uvicorn.logging",
        "uvicorn.loops.auto",
        "uvicorn.loops.asyncio",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.http.h11_impl",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.protocols.websockets.websockets_impl",
        "uvicorn.middleware.wsgi",
        "starlette.middleware",
        "fastapi",
        "websockets",
        "websockets.legacy",
        "httpx",
        "httpcore",
        "httpcore._async.connection_pool",
        "h11",
        "sniffio",
        "anyio",
        "anyio.streams",
        "platform",
        "compat",
    ],
    hookspath=[],
    hooksconfig={"fastapi": {"exclude-dependencies": False}},
    runtime_hooks=[],
    excludes=[
        "tkinter", "PyQt5", "PyQt6", "PySide2", "PySide6",
        "matplotlib", "numpy", "scipy", "pandas", "PIL", "cv2",
        "notebook", "jupyter", "boto3", "botocore",
        "tensorflow", "torch",
        "setuptools", "pip", "wheel",
        "test", "unittest", "email", "http.server",
    ],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# ── Detect platform ─────────────────────────────────────────────────────
import platform as _plt
_IS_MACOS = _plt.system() == "Darwin"

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="CloakBrowser Suite" if _IS_MACOS else "cloakbrowser-suite",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    contents_directory="_internal",
)

if _IS_MACOS:
    coll = BUNDLE(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        name="CloakBrowser Suite",
        icon=str(_PROJ / "build" / "icon.icns") if (_PROJ / "build" / "icon.icns").exists() else None,
        version="0.1.0",
        info_plist={
            "NSHighResolutionCapable": True,
            "NSRequiresAquaSystemAppearance": False,
            "CFBundleName": "CloakBrowser Suite",
            "CFBundleDisplayName": "CloakBrowser Suite",
            "CFBundleIdentifier": "com.cloakbrowser.suite",
            "CFBundleVersion": "0.1.0",
            "CFBundleShortVersionString": "0.1.0",
            "NSHumanReadableCopyright": "MIT License",
        },
    )
else:
    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=False,
        upx_exclude=[],
        name="cloakbrowser-suite",
    )
