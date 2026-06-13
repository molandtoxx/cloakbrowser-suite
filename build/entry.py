"""Packaged entry point — detects CLI vs server mode.

- No arguments or server flags → start web server
- CLI subcommands (profile, browser, status) → CLI mode

When running inside a PyInstaller bundle, the Chromium binary is included
in the ``_internal/`` directory.  We set ``CLOAKBROWSER_CACHE_DIR`` so that
``cloakbrowser`` finds it there instead of downloading.
"""
from __future__ import annotations

import os
import sys


# ── Point cloakbrowser at the bundled Chromium ──────────────────────────
# In a PyInstaller single-directory bundle, sys._MEIPASS is the _internal/
# directory where all data files (including chromium-{ver}/) live.
_MEI = getattr(sys, "_MEIPASS", None)
if _MEI is not None:
    # Check if any chromium-* directory exists in the bundle
    _has_chromium = any(
        p.startswith("chromium-") and os.path.isdir(os.path.join(_MEI, p))
        for p in os.listdir(_MEI)
    )
    if _has_chromium:
        # Set env before any cloakbrowser import so get_cache_dir() picks it up
        os.environ.setdefault("CLOAKBROWSER_CACHE_DIR", _MEI)

# Ensure the bundle root is on sys.path so backend/ cli/ packages resolve
_bundle_dir = os.path.dirname(os.path.abspath(__file__))
if _bundle_dir not in sys.path:
    sys.path.insert(0, _bundle_dir)

# ── Known server flags (anything else → CLI) ─────────────────────────────
_SERVER_FLAGS = frozenset({
    "--port", "--host", "--no-open",
})


def _wants_help(argv: list[str]) -> bool:
    return "--help" in argv[1:] or "-h" in argv[1:]


def _is_server_mode(argv: list[str]) -> bool:
    if len(argv) <= 1:
        return True  # bare executable → server
    if _wants_help(argv):
        return False
    for a in argv[1:]:
        if a.startswith("-"):
            if a in _SERVER_FLAGS or a.startswith("--port=") or a.startswith("--host="):
                return True
            return False
        return a in ("profile", "browser", "start", "status")
    return True


def main() -> None:
    if _wants_help(sys.argv):
        print("""CloakBrowser Suite — fingerprint browser manager

Usage:
  cloakbrowser-suite [options]              Start web server (default)
  cloakbrowser-suite profile list           List profiles
  cloakbrowser-suite profile create         Create a profile
  cloakbrowser-suite browser launch <id>    Launch a browser
  cloakbrowser-suite browser stop <id>      Stop a browser
  cloakbrowser-suite status                 Show status

Options:
  --port PORT       Server port (default: 8080)
  --host HOST       Bind address (default: 127.0.0.1)
  --no-open         Don't open browser on start
  -h, --help        Show this help message
""")
        sys.exit(0)

    if _is_server_mode(sys.argv):
        from backend.main import app
        import uvicorn

        port = 8080
        host = "127.0.0.1"
        no_open = False

        args = sys.argv[1:]
        it = iter(args)
        for a in it:
            if a == "--port":
                port = int(next(it))
            elif a == "--host":
                host = next(it)
            elif a == "--no-open":
                no_open = True

        if not no_open:
            import threading
            import webbrowser
            threading.Timer(2.0, lambda: webbrowser.open(f"http://{host}:{port}")).start()

        print(f"  CloakBrowser Suite starting at http://{host}:{port}\n")
        uvicorn.run(app, host=host, port=port, log_level="warning")
    else:
        from cli.main import main as cli_main
        cli_main()


if __name__ == "__main__":
    main()
