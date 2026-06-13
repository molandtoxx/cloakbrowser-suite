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
# Output: dist/CloakBrowser Suite.app/  (macOS .app bundle)
#         dist/CloakBrowser Suite-macOS-arm64.tar.gz
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

echo "=== 3/5  Downloading Chromium (cloakbrowser) ==="
python3 -c "
from cloakbrowser.download import ensure_binary
path = ensure_binary()
print(f'Chromium ready: {path}')
"

echo "=== 4/5  Running PyInstaller (creates .app bundle) ==="
pyinstaller build/build.spec --clean --noconfirm

echo "=== 5/5  Creating archive ==="
cd dist
ARCHIVE="CloakBrowser-Suite-macOS-$(uname -m).tar.gz"
# macOS .app is a directory → tar it
tar czf "$ARCHIVE" "CloakBrowser Suite.app/"
echo "===> dist/$ARCHIVE  ($(du -sh "$ARCHIVE" | cut -f1))"
