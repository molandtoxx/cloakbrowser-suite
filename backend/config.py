"""Application configuration — persisted to config.json in the data directory.

Supports:
  - chromium_path: point to a custom Chromium binary or directory.
    If set to a file → use directly.
    If set to a directory → auto-detect the browser executable inside.
    If not set → fall through to cloakbrowser's auto-download (ensure_binary).
"""

from __future__ import annotations

import json
import logging
import platform
import subprocess
from pathlib import Path
from typing import Any

from . import database as db

logger = logging.getLogger("cloakbrowser.suite.config")

_CONFIG_FILENAME = "config.json"


def get_config_path() -> Path:
    """Return the path to config.json in the data directory."""
    return Path(db.get_data_dir()) / _CONFIG_FILENAME


def load_config() -> dict[str, Any]:
    """Load config.json from the data directory. Returns {} if missing or invalid."""
    path = get_config_path()
    if not path.exists():
        return {}
    try:
        text = path.read_text(encoding="utf-8")
        data = json.loads(text)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to load config from %s: %s", path, exc)
        return {}


def save_config(config: dict[str, Any]) -> None:
    """Save config.json to the data directory (atomic write)."""
    path = get_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.rename(path)


def _find_binary_in_dir(directory: Path) -> Path | None:
    """Auto-detect the browser executable inside a directory.

    Checks: directory/chrome(.exe), directory/Chromium.app/Contents/MacOS/Chromium,
    and any chromium-*/chrome(.exe) subdirectory (cache layout).
    """
    system = platform.system()

    # Direct binary
    candidates = []
    if system == "Windows":
        candidates.append(directory / "chrome.exe")
    elif system == "Darwin":
        candidates.append(directory / "Chromium.app" / "Contents" / "MacOS" / "Chromium")
        candidates.append(directory / "chrome")
    else:
        candidates.append(directory / "chrome")

    for c in candidates:
        if c.is_file():
            return c

    # Cache-dir layout: chromium-{version}/chrome(.exe)
    for child in sorted(directory.iterdir()):
        if child.is_dir() and child.name.startswith("chromium-"):
            if system == "Windows":
                binary = child / "chrome.exe"
            elif system == "Darwin":
                binary = child / "Chromium.app" / "Contents" / "MacOS" / "Chromium"
                if not binary.exists():
                    binary = child / "chrome"
            else:
                binary = child / "chrome"
            if binary.is_file():
                return binary

    return None


def detect_chromium(path: str) -> dict[str, Any]:
    """Validate a user-provided chromium_path.

    Returns:
        {"valid": True, "path": str, "version": str | None} on success.
        {"valid": False, "path": str, "error": str} on failure.
    """
    p = Path(path).expanduser()
    if not p.exists():
        return {"valid": False, "path": str(p), "error": "Path does not exist"}

    binary: Path | None
    if p.is_file():
        binary = p
    elif p.is_dir():
        binary = _find_binary_in_dir(p)
        if binary is None:
            return {"valid": False, "path": str(p), "error": "No Chromium binary found in directory"}
    else:
        return {"valid": False, "path": str(p), "error": "Not a file or directory"}

    # Try to get version
    version = None
    try:
        result = subprocess.run(
            [str(binary), "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            version = result.stdout.strip().split()[-1] if result.stdout.strip() else None
    except Exception:
        pass

    return {"valid": True, "path": str(binary), "version": version}


def resolve_chromium_path() -> str | None:
    """Resolve the Chromium binary path from config.

    Returns the absolute path to a valid binary, or None if not configured
    (fall through to cloakbrowser's ensure_binary() / auto-download).
    """
    config = load_config()
    chromium_path = config.get("chromium_path")
    if not chromium_path:
        return None

    p = Path(chromium_path).expanduser()
    if p.is_file():
        return str(p.resolve())

    if p.is_dir():
        binary = _find_binary_in_dir(p)
        if binary:
            return str(binary.resolve())

    # Path is configured but invalid — log warning, fall through
    logger.warning("Configured chromium_path '%s' is invalid, falling back to auto-download", chromium_path)
    return None
