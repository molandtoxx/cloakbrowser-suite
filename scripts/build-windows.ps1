# ──────────────────────────────────────────────────────────────────────────────
# Build CloakBrowser Suite for Windows (x86_64)
#
# Prerequisites:
#   - Python 3.11+ (on PATH)
#   - Node.js 18+ (on PATH)
#   - pip install pyinstaller
#
# Usage (PowerShell):
#   .\scripts\build-windows.ps1
#
# Output: dist\cloakbrowser-suite\   (portable single-directory bundle)
# ──────────────────────────────────────────────────────────────────────────────
$ErrorActionPreference = "Stop"
Push-Location (Split-Path $PSScriptRoot -Parent)

Write-Host "=== 1/5  Installing Python dependencies ==="
pip install --quiet -e .

Write-Host "=== 2/5  Building frontend ==="
Set-Location frontend
npm install --silent
npm run build
Set-Location ..
if (!(Test-Path frontend/dist/index.html)) { throw "frontend/dist/index.html not found - frontend build may have failed" }

Write-Host "=== 3/5  Downloading Chromium (cloakbrowser) ==="
python -c "from cloakbrowser.download import ensure_binary; path = ensure_binary(); print(f'Chromium ready: {path}')"

Write-Host "=== 4/5  Running PyInstaller ==="
pyinstaller build/build.spec --clean --noconfirm

Write-Host "=== 5/5  Creating archive ==="
Set-Location dist
$ARCHIVE = "cloakbrowser-suite-windows-x64.zip"
if (Test-Path $ARCHIVE) { Remove-Item $ARCHIVE }
Compress-Archive -Path cloakbrowser-suite -DestinationPath $ARCHIVE
Write-Host "===> dist\$ARCHIVE  ($((Get-Item $ARCHIVE).Length / 1MB -as [int]) MB)"

Pop-Location
