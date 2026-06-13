#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# Build CloakBrowser Suite for Linux (x86_64)
#
# Prerequisites:
#   - Python 3.11+
#   - Node.js 18+ (for frontend build)
#   - pip install pyinstaller
#
# Usage:
#   bash scripts/build-linux.sh
#
# Output: dist/cloakbrowser-suite/     (portable single-directory bundle)
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
from cloakbrowser.download import download_chromium
download_chromium()
print('Chromium downloaded')
"

echo "=== 4/5  Running PyInstaller ==="
pyinstaller build/build.spec --clean --noconfirm

echo "=== 5/5  Creating archive ==="
cd dist
ARCHIVE="cloakbrowser-suite-linux-x64.tar.gz"
tar czf "$ARCHIVE" cloakbrowser-suite/
echo "===> dist/$ARCHIVE  ($(du -sh "$ARCHIVE" | cut -f1))"
