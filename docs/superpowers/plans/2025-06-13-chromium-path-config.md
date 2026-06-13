# Chromium Path Configuration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow users to configure a custom Chromium binary path via Web UI or config file, falling back to auto-download when not set.

**Architecture:** Add a `backend/config.py` module for config.json load/save and Chromium path resolution. Add `/api/settings` endpoints to main.py. In browser_manager.py, check config before calling `ensure_binary()`. Add a Settings page to the frontend.

**Tech Stack:** Python/FastAPI (backend), React/TypeScript (frontend), SQLite (existing), JSON config file (new)

---

### Task 1: Backend Config Module

**Files:**
- Create: `backend/config.py`

- [ ] **Step 1: Create `backend/config.py` with config load/save and path resolution**

```python
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
import os
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
```

- [ ] **Step 2: Add `get_data_dir()` export to `backend/database.py`**

Add at the end of `database.py`, after the existing `_db_path` setup, a public function:

```python
def get_data_dir() -> str:
    """Return the data directory path (parent of the database file)."""
    return str(_db_path.parent)
```

Check that `_db_path` is defined in database.py (it should be). If the variable has a different name, adapt accordingly.

- [ ] **Step 3: Commit**

```bash
git add backend/config.py backend/database.py
git commit -m "feat: add config module for chromium path settings"
```

---

### Task 2: Backend Settings API

**Files:**
- Modify: `backend/models.py`
- Modify: `backend/main.py`

- [ ] **Step 1: Add settings models to `backend/models.py`**

Append at the end:

```python
class SettingsUpdate(BaseModel):
    chromium_path: str | None = None


class SettingsResponse(BaseModel):
    chromium_path: str | None
    chromium_resolved: str | None
    chromium_version: str | None
```

- [ ] **Step 2: Add settings endpoints to `backend/main.py`**

Add imports at top (with existing imports):

```python
from .config import detect_chromium, load_config, resolve_chromium_path, save_config
```

Add these endpoints before the static file mount (find `app.mount("", StaticFiles(...))` and insert before it):

```python
# ── Settings ───────────────────────────────────────────────────────────────


@app.get("/api/settings", response_model=SettingsResponse)
async def get_settings():
    """Return current settings including resolved Chromium info."""
    config = load_config()
    chromium_path = config.get("chromium_path")
    resolved = resolve_chromium_path()

    version = None
    if resolved:
        try:
            result = subprocess.run(
                [resolved, "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                version = result.stdout.strip().split()[-1] if result.stdout.strip() else None
        except Exception:
            pass

    return SettingsResponse(
        chromium_path=chromium_path,
        chromium_resolved=resolved,
        chromium_version=version,
    )


@app.patch("/api/settings", response_model=SettingsResponse)
async def update_settings(req: SettingsUpdate):
    """Update settings. Set chromium_path to null/empty to clear (revert to auto-download)."""
    config = load_config()

    if req.chromium_path is not None:
        # Empty string means clear
        if req.chromium_path.strip() == "":
            config.pop("chromium_path", None)
        else:
            # Validate the path
            result = detect_chromium(req.chromium_path)
            if not result["valid"]:
                raise HTTPException(status_code=400, detail=result["error"])
            config["chromium_path"] = req.chromium_path
    # If chromium_path is None in request, don't touch it (partial update)

    save_config(config)

    # Re-resolve after saving
    resolved = resolve_chromium_path()
    version = None
    if resolved:
        try:
            result = subprocess.run(
                [resolved, "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                version = result.stdout.strip().split()[-1] if result.stdout.strip() else None
        except Exception:
            pass

    return SettingsResponse(
        chromium_path=config.get("chromium_path"),
        chromium_resolved=resolved,
        chromium_version=version,
    )


@app.post("/api/settings/chromium/detect")
async def detect_chromium_path(req: SettingsUpdate):
    """Test if a given path resolves to a valid Chromium binary.
    Returns validation result with version info.
    """
    if not req.chromium_path:
        raise HTTPException(status_code=400, detail="chromium_path is required")

    return detect_chromium(req.chromium_path)
```

Also add `import subprocess` at the top of `main.py` if not already imported.

- [ ] **Step 3: Make BrowserManager use configured path**

In `backend/browser_manager.py`, add import at top:

```python
from .config import resolve_chromium_path
```

In the `launch()` method, BEFORE the `ensure_binary()` / `launch_persistent_context_async` call, add chromium path resolution. Find the line that currently reads:

```python
context = await asyncio.wait_for(
    launch_persistent_context_async(
```

Just before that block, add:

```python
# Use configured Chromium path if set, otherwise auto-download
custom_path = resolve_chromium_path()
if custom_path:
    os.environ["CLOAKBROWSER_BINARY_PATH"] = custom_path
else:
    os.environ.pop("CLOAKBROWSER_BINARY_PATH", None)
```

Also ensure `import os` is present at the top of `browser_manager.py` (it already is).

- [ ] **Step 4: Commit**

```bash
git add backend/models.py backend/main.py backend/browser_manager.py
git commit -m "feat: add /api/settings endpoints and chromium path resolution"
```

---

### Task 3: Frontend Settings API Client

**Files:**
- Modify: `frontend/src/lib/api.ts`

- [ ] **Step 1: Add settings API functions and types**

Add these types to the `api.ts` type section (before the `api` object):

```typescript
export interface Settings {
  chromium_path: string | null;
  chromium_resolved: string | null;
  chromium_version: string | null;
}

export interface SettingsUpdate {
  chromium_path?: string | null;
}

export interface ChromiumDetectResult {
  valid: boolean;
  path: string;
  version?: string | null;
  error?: string;
}
```

Add these methods to the `api` object:

```typescript
settings: {
  get: () => request<Settings>("/api/settings"),
  update: (data: SettingsUpdate) =>
    request<Settings>("/api/settings", {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  detect: (chromium_path: string) =>
    request<ChromiumDetectResult>("/api/settings/chromium/detect", {
      method: "POST",
      body: JSON.stringify({ chromium_path }),
    }),
},
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/lib/api.ts
git commit -m "feat: add settings API client functions"
```

---

### Task 4: Frontend Settings Page

**Files:**
- Create: `frontend/src/components/Settings.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Create `Settings.tsx`**

```tsx
import { useState, useEffect, useCallback } from "react";
import { Settings, SettingsUpdate, ChromiumDetectResult, api } from "../lib/api";
import { Monitor, FolderOpen, CheckCircle, XCircle, Loader2, Save, RotateCcw } from "lucide-react";

export function Settings() {
  const [settings, setSettings] = useState<Settings | null>(null);
  const [chromiumPath, setChromiumPath] = useState("");
  const [detecting, setDetecting] = useState(false);
  const [detectResult, setDetectResult] = useState<ChromiumDetectResult | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadSettings = useCallback(async () => {
    try {
      const s = await api.settings.get();
      setSettings(s);
      setChromiumPath(s.chromium_path || "");
      setDetectResult(null);
    } catch (e: any) {
      setError(e.message || "Failed to load settings");
    }
  }, []);

  useEffect(() => {
    loadSettings();
  }, [loadSettings]);

  const handleDetect = async () => {
    if (!chromiumPath.trim()) return;
    setDetecting(true);
    setDetectResult(null);
    try {
      const result = await api.settings.detect(chromiumPath.trim());
      setDetectResult(result);
    } catch (e: any) {
      setDetectResult({ valid: false, path: chromiumPath, error: e.message || "Detection failed" });
    } finally {
      setDetecting(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      const data: SettingsUpdate = { chromium_path: chromiumPath.trim() || null };
      const updated = await api.settings.update(data);
      setSettings(updated);
      setChromiumPath(updated.chromium_path || "");
      setDetectResult(null);
    } catch (e: any) {
      setError(e.message || "Failed to save settings");
    } finally {
      setSaving(false);
    }
  };

  const handleClear = async () => {
    setSaving(true);
    setError(null);
    try {
      const updated = await api.settings.update({ chromium_path: "" });
      setSettings(updated);
      setChromiumPath("");
      setDetectResult(null);
    } catch (e: any) {
      setError(e.message || "Failed to clear settings");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="max-w-2xl mx-auto space-y-6">
        <div className="flex items-center gap-3">
          <Monitor className="h-5 w-5 text-gray-400" />
          <h2 className="text-lg font-semibold text-gray-200">Settings</h2>
        </div>

        {/* Chromium Binary Path */}
        <div className="bg-surface-1 rounded-lg p-5 space-y-4">
          <div>
            <h3 className="text-sm font-medium text-gray-200">Chromium Binary Path</h3>
            <p className="text-xs text-gray-500 mt-1">
              Set a custom Chromium binary or directory. Point to the chrome executable or a directory
              containing it. Leave empty to auto-download.
            </p>
          </div>

          <div className="space-y-2">
            <label className="label">Path</label>
            <div className="flex gap-2">
              <input
                type="text"
                className="input flex-1"
                placeholder="e.g. /opt/chrome/chrome or C:\Users\you\chromium-146.0"
                value={chromiumPath}
                onChange={(e) => {
                  setChromiumPath(e.target.value);
                  setDetectResult(null);
                }}
                onKeyDown={(e) => {
                  if (e.key === "Enter") handleDetect();
                }}
              />
              <button
                className="btn-secondary flex items-center gap-1.5"
                onClick={handleDetect}
                disabled={detecting || !chromiumPath.trim()}
              >
                {detecting ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <FolderOpen className="h-3.5 w-3.5" />
                )}
                Detect
              </button>
            </div>

            {/* Detection result */}
            {detectResult && (
              <div className={`flex items-start gap-2 text-xs p-2 rounded ${
                detectResult.valid
                  ? "bg-green-900/30 text-green-400"
                  : "bg-red-900/30 text-red-400"
              }`}>
                {detectResult.valid ? (
                  <CheckCircle className="h-4 w-4 mt-0.5 shrink-0" />
                ) : (
                  <XCircle className="h-4 w-4 mt-0.5 shrink-0" />
                )}
                <div>
                  <div>{detectResult.valid ? "Valid Chromium binary" : "Invalid path"}</div>
                  <div className="text-gray-500">{detectResult.path}</div>
                  {detectResult.version && (
                    <div className="text-gray-500">Version: {detectResult.version}</div>
                  )}
                  {detectResult.error && (
                    <div>{detectResult.error}</div>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Current status */}
          {settings && (
            <div className="text-xs text-gray-500 space-y-1">
              <div>
                Current:{" "}
                {settings.chromium_resolved ? (
                  <span className="text-gray-300">{settings.chromium_resolved}</span>
                ) : (
                  <span className="text-gray-500">Auto-download (default)</span>
                )}
              </div>
              {settings.chromium_version && (
                <div>Version: {settings.chromium_version}</div>
              )}
            </div>
          )}

          <div className="flex gap-2">
            <button
              className="btn-primary flex items-center gap-1.5"
              onClick={handleSave}
              disabled={saving}
            >
              {saving && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
              <Save className="h-3.5 w-3.5" />
              {saving ? "Saving…" : "Save"}
            </button>
            <button
              className="btn-secondary flex items-center gap-1.5"
              onClick={handleClear}
              disabled={saving}
            >
              <RotateCcw className="h-3.5 w-3.5" />
              Reset to Auto-Download
            </button>
          </div>

          {error && (
            <div className="text-xs text-red-400">{error}</div>
          )}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Add Settings route to App.tsx**

In `App.tsx`, add import:

```tsx
import { Settings } from "./components/Settings";
```

In the sidebar section, add a Settings nav button. Find the existing sidebar items (the ones that render profile list items or create button). Add a Settings button at the bottom of the sidebar:

In the sidebar `<nav>` or sidebar content area, add:

```tsx
<button
  className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-400 hover:text-gray-200 hover:bg-surface-2 rounded-lg transition-colors"
  onClick={() => setView("settings")}
>
  <Settings className="h-4 w-4" />
  Settings
</button>
```

In the content area, add the settings view rendering. Find where `view === "create"` etc. are conditionally rendered and add:

```tsx
{view === "settings" && <Settings />}
```

Also update the `View` type to include `"settings"`:

```tsx
type View = "empty" | "create" | "edit" | "view" | "settings";
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/Settings.tsx frontend/src/App.tsx
git commit -m "feat: add Settings page with Chromium path configuration"
```

---

### Task 5: Integration Test & Polish

**Files:**
- Modify: all touched files for final polish

- [ ] **Step 1: Verify Python syntax**

```bash
cd /home/molandtoxx/dpan/development/dev-repos/cloakbrowser-suite
python3 -c "import py_compile; py_compile.compile('backend/config.py', doraise=True); print('config.py OK')"
python3 -c "import py_compile; py_compile.compile('backend/main.py', doraise=True); print('main.py OK')"
python3 -c "import py_compile; py_compile.compile('backend/models.py', doraise=True); print('models.py OK')"
python3 -c "import py_compile; py_compile.compile('backend/browser_manager.py', doraise=True); print('browser_manager.py OK')"
python3 -c "import py_compile; py_compile.compile('backend/database.py', doraise=True); print('database.py OK')"
```

- [ ] **Step 2: Verify frontend builds**

```bash
cd /home/molandtoxx/dpan/development/dev-repos/cloakbrowser-suite/frontend
npm run build 2>&1 | tail -5
```

- [ ] **Step 3: Test the API manually**

Start the server and test:

```bash
cd /home/molandtoxx/dpan/development/dev-repos/cloakbrowser-suite
python -m backend.main &
# Test GET settings
curl -s http://127.0.0.1:8080/api/settings | python3 -m json.tool
# Test detect endpoint
curl -s -X POST http://127.0.0.1:8080/api/settings/chromium/detect \
  -H 'Content-Type: application/json' \
  -d '{"chromium_path": "/usr/bin/google-chrome"}' | python3 -m json.tool
```

- [ ] **Step 4: Final commit if any fixes needed**

```bash
git add -A
git commit -m "fix: polish and integration fixes for settings feature"
```