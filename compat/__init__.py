"""Platform detection and environment setup.

Detects the current OS and provides platform-appropriate
environment variables and settings for launching Chromium.
"""

import os
import platform as _platform
import sys
from dataclasses import dataclass, field
from typing import NoReturn


_PLATFORM = _platform.system().lower()  # "linux", "darwin", "windows"


@dataclass
class PlatformConfig:
    """Platform-specific settings for browser launches."""

    name: str
    display_env: dict[str, str] = field(default_factory=dict)
    extra_chrome_args: list[str] = field(default_factory=list)


def _detect_linux() -> PlatformConfig:
    """Detect a running X11 or Wayland display on Linux."""
    display = os.environ.get("DISPLAY")
    # If DISPLAY is already set by the user's session, use it.
    if display:
        return PlatformConfig(
            name="linux",
            display_env={"DISPLAY": display},
        )
    # Fall back to :0 if the DISPLAY variable is not set
    # but we're likely in a desktop session.
    return PlatformConfig(
        name="linux",
        display_env={"DISPLAY": ":0"},
    )


def _detect_windows() -> PlatformConfig:
    """Windows does not need a DISPLAY env var."""
    return PlatformConfig(
        name="windows",
        extra_chrome_args=[
            # Disable GPU sandbox on Windows for compatibility
            "--disable-gpu-sandbox",
        ],
    )


def _detect_darwin() -> PlatformConfig:
    """macOS does not need a DISPLAY env var."""
    return PlatformConfig(
        name="darwin",
        extra_chrome_args=[],
    )


_DETECTORS = {
    "linux": _detect_linux,
    "windows": _detect_windows,
    "darwin": _detect_darwin,
}


def get_config() -> PlatformConfig:
    """Detect and return the current platform's configuration.

    Raises RuntimeError if the platform is not supported.
    """
    detector = _DETECTORS.get(_PLATFORM)
    if detector is None:
        raise RuntimeError(
            f"Unsupported platform: {_PLATFORM}. "
            f"Supported: linux, windows, darwin"
        )
    return detector()


def get_data_dir() -> str:
    """Return the platform-appropriate data directory."""
    base = os.environ.get("CLOAKBROWSER_DATA_DIR")
    if base:
        return os.path.abspath(base)

    if _PLATFORM == "linux":
        xdg = os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))
        return os.path.join(xdg, "cloakbrowser-suite")
    elif _PLATFORM == "darwin":
        return os.path.join(
            os.path.expanduser("~"), "Library", "Application Support",
            "CloakBrowser Suite",
        )
    elif _PLATFORM == "windows":
        appdata = os.environ.get("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local"))
        return os.path.join(appdata, "CloakBrowser Suite")
    else:
        # Fallback
        return os.path.join(os.path.expanduser("~"), ".cloakbrowser-suite")


def is_headless() -> bool:
    """Check if the environment likely has no GUI (SSH, CI, etc.).

    On Linux this checks for $DISPLAY. On Windows/macOS it always
    returns False since those platforms always have a GUI.
    """
    if _PLATFORM == "linux":
        return "DISPLAY" not in os.environ and "WAYLAND_DISPLAY" not in os.environ
    # Windows and macOS always have a GUI
    return False


def platform_name() -> str:
    """Return the normalized platform name: linux, windows, darwin."""
    return _PLATFORM
