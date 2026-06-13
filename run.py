#!/usr/bin/env python3
"""Quick-start entry point: run the server and open the dashboard.

Usage:
    python run.py                        # Start server, open browser
    python run.py --port 9090            # Custom port
    python run.py --no-open              # Don't open browser
    python run.py --host 0.0.0.0         # Listen on all interfaces
"""

from __future__ import annotations

import os
import sys

# Ensure the project root is on sys.path
_project_root = os.path.dirname(os.path.abspath(__file__))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)


def main():
    """Parse arguments and start the CloakBrowser Suite server."""
    import argparse

    parser = argparse.ArgumentParser(
        description="CloakBrowser Suite — cross-platform fingerprint browser manager",
    )
    parser.add_argument("--port", type=int, default=8080, help="Server port (default: 8080)")
    parser.add_argument("--host", default="127.0.0.1", help="Bind address (default: 127.0.0.1)")
    parser.add_argument("--no-open", action="store_true", help="Don't open browser")
    args = parser.parse_args()

    url = f"http://{args.host}:{args.port}"
    print(f"  CloakBrowser Suite starting at {url}")
    print()

    if not args.no_open:
        import threading
        import webbrowser
        threading.Timer(2.0, lambda: webbrowser.open(url)).start()

    from backend.main import app
    import uvicorn
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level="warning",
    )


if __name__ == "__main__":
    main()
