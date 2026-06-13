# Chromium Path Configuration

## Problem

Users sometimes need to manually install Chromium (e.g., offline environments, custom builds, network
restrictions). Currently the only way to skip auto-download is via `CLOAKBROWSER_BINARY_PATH` env var,
which is inconvenient for end users of the packaged Suite app.

## Design

### Configuration Priority

When resolving the Chromium binary path, check in this order:

1. **Web UI setting** (`chromium_path` in settings database)
2. **Config file** (`data_dir/config.json` → `chromium_path` field)
3. **Auto-download** (existing `ensure_binary()` behavior with `CLOAKBROWSER_CACHE_DIR`)

### Path Resolution

The `chromium_path` field accepts:

- **File path** (e.g., `/opt/chrome/chrome`, `C:\Users\foo\chrome.exe`):
  → Used directly as the executable. Must be executable and exist.

- **Directory path** (e.g., `/opt/chrome`, `C:\Users\foo\chromium-146.0.7680.177.5`):
  → Auto-detect the browser executable inside:
  - Linux: `{dir}/chrome`
  - macOS: `{dir}/Chromium.app/Contents/MacOS/Chromium`
  - Windows: `{dir}/chrome.exe`
  - Also checks `{dir}/chromium-{version}/chrome(.exe)` pattern (cache dir layout)

### Config File

Location: `{data_dir}/config.json` (same dir as profiles database)

```json
{
  "chromium_path": "/opt/chrome/chrome"
}
```

If the file doesn't exist, it's treated as empty (fall through to auto-download).

### Web UI

- **Settings page** (new): add a "Chromium" section with:
  - Input field for Chromium path (file or directory)
  - "Browse" button to select path (future, requires file picker)
  - "Auto-detect" button that checks if the path resolves to a valid binary
  - Status display: current binary version, whether it's bundled/downloaded/custom
- **API endpoint** `GET /api/settings` / `PATCH /api/settings` — read/write config

### Backend Changes

**`backend/config.py`** (new) — load/save config from `data_dir/config.json`:

```python
def load_config() -> dict:
    """Load config.json from data directory. Returns {} if missing."""

def save_config(config: dict) -> None:
    """Save config.json to data directory."""

def resolve_chromium_path() -> str | None:
    """Resolve chromium_path from config (UI > config file > None).
    
    Returns:
        File path if path points to a file.
        Auto-detected binary path if path points to a directory.
        None if not configured (fall through to auto-download).
    """
```

**`backend/browser_manager.py`** — before calling `ensure_binary()`, check config:

```python
# In BrowserManager.launch(), before browser launch:
from .config import resolve_chromium_path

custom_path = resolve_chromium_path()
if custom_path:
    # Override CLOAKBROWSER_BINARY_PATH for this process
    os.environ["CLOAKBROWSER_BINARY_PATH"] = custom_path
```

**`backend/main.py`** — add settings API endpoints:

- `GET /api/settings` — return current config (including resolved chromium path and version)
- `PATCH /api/settings` — update config (validate chromium_path if provided)
- `POST /api/settings/chromium/detect` — test if a given path resolves to a valid Chromium binary

**`backend/database.py`** — no changes needed; config is separate from profiles DB.

### Files to Create/Modify

| File | Action |
|------|--------|
| `backend/config.py` | Create — config load/save, chromium path resolution |
| `backend/browser_manager.py` | Modify — check config before `ensure_binary()` |
| `backend/main.py` | Modify — add settings API endpoints |
| `backend/models.py` | Modify — add SettingsUpdate model |
| `frontend/src/components/Settings.tsx` | Create — settings page UI |
| `frontend/src/lib/api.ts` | Modify — add settings API calls |
| `frontend/src/App.tsx` | Modify — add settings route |

### Validation

When user sets `chromium_path`:

1. Check path exists
2. If directory, check it contains a browser executable for this platform
3. If resolved binary exists, verify it's executable (not on Windows)
4. Try running `{binary} --version` to confirm it's Chromium-based
5. Return success with version info, or error with reason