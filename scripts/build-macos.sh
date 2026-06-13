#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# Build CloakBrowser Suite for macOS (arm64 / x86_64)
#
# Prerequisites:
#   - Python 3.11+
#   - Node.js 18+ (for frontend build)
#   - pip install pyinstaller
#
# Usage:
#   bash scripts/build-macos.sh
#
# Output: dist/cloakbrowser-suite/     (single-directory bundle)
#         dist/CloakBrowser-Suite-macOS-<arch>.tar.gz
# ──────────────────────────────────────────────────────────────────────────────
set -euo pipefail
cd "$(dirname "$0")/.."

echo "=== 1/5  Installing Python dependencies ==="
pip install --quiet -e .

echo "=== 2/5  Building frontend ==="
cd frontend
npm install --silent
npm run build
cd ..
test -f frontend/dist/index.html || { echo "ERROR: frontend/dist/index.html not found - frontend build may have failed"; exit 1; }

echo "=== 3/5  Downloading Chromium (cloakbrowser) ==="
python3 -c "
from cloakbrowser.download import ensure_binary
path = ensure_binary()
print(f'Chromium ready: {path}')
"

echo "=== 4/5  Running PyInstaller ==="
# Clear PyInstaller binary cache to avoid stale codesign failures on macOS
rm -rf ~/Library/Application\ Support/pyinstaller/bincache* 2>/dev/null || true
pyinstaller build/build.spec --clean --noconfirm

echo "=== 5/5  Creating archive ==="
cd dist
ARCHIVE="CloakBrowser-Suite-macOS-$(uname -m).tar.gz"
# Bundle is a single-directory tar
tar czf "$ARCHIVE" cloakbrowser-suite/
echo "===> dist/$ARCHIVE  ($(du -sh "$ARCHIVE" | cut -f1))"
