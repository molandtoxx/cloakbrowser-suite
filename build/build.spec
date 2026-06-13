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

_PROJ = Path(__file__).resolve().parent.parent

# ══════════════════════════════════════════════════════════════════════════
#  Chromium bundling — detect & queue every file under chromium-{ver}/
# ══════════════════════════════════════════════════════════════════════════

_CHROMIUM_DATAS: list[tuple[str, str]] = []

try:
    from cloakbrowser.config import get_cache_dir, get_chromium_version, get_binary_dir

    _CACHE = get_cache_dir()          # ~/.cloakbrowser/
    _VER  = get_chromium_version()    # e.g. "146.0.7680.177.5"
    _DIR  = get_binary_dir()          # ~/.cloakbrowser/chromium-{ver}/

    if _DIR.is_dir():
        _mb = sum(f.stat().st_size for f in _DIR.rglob("*") if f.is_file()) / 1_048_576
        print(f"[spec] Bundling Chromium: {_DIR}  ({_mb:.0f} MiB)")

        for f in sorted(_DIR.rglob("*")):
            if f.is_file():
                _rel = str(f.relative_to(_CACHE))   # "chromium-{ver}/chrome"
                _CHROMIUM_DATAS.append((str(f), _rel))

        print(f"[spec]   → {len(_CHROMIUM_DATAS)} files")
    else:
        print(f"[spec] WARNING: Chromium directory not found at {_DIR}")
        print(f"[spec]   Bundle will NOT include Chromium — it will download on first launch.")
except ImportError:
    print("[spec] WARNING: cloakbrowser not importable — Chromium will NOT be bundled")

# ══════════════════════════════════════════════════════════════════════════

block_cipher = None

a = Analysis(
    [str(_PROJ / "build" / "entry.py")],
    pathex=[str(_PROJ)],
    binaries=[],
    datas=_CHROMIUM_DATAS,            # Chromium files included here
    hiddenimports=[
        "backend.main",
        "backend.database",
        "backend.models",
        "backend.browser_manager",
        "cli.main",
        "cloakbrowser",
        "cloakbrowser.config",
        "cloakbrowser.core",
        "cloakbrowser.core.persistent_context",
        "cloakbrowser.fingerprint",
        "cloakbrowser.geoip",
        "cloakbrowser.geoip.mmdb_reader",
        "cloakbrowser.platform.windows",
        "cloakbrowser.platform.linux",
        "cloakbrowser.platform.darwin",
        "cloakbrowser.proxy",
        "cloakbrowser.protected_cookie",
        "cloakbrowser.download",
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

# ── Also bundle frontend dist/ ──────────────────────────────────────────
_FRONTEND = _PROJ / "frontend" / "dist"
if _FRONTEND.is_dir():
    for f in sorted(_FRONTEND.rglob("*")):
        if f.is_file():
            a.datas.append((str(f), str(f.relative_to(_FRONTEND.parent))))
else:
    print("[spec] WARNING: frontend/dist/ not found — no UI will be served")

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
