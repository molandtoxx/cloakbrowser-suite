import { useState, useEffect, useCallback } from "react";
import {
  Settings as SettingsType,
  SettingsUpdate,
  ChromiumDetectResult,
  api,
} from "../lib/api";
import {
  Monitor,
  FolderOpen,
  CheckCircle,
  XCircle,
  Loader2,
  Save,
  RotateCcw,
} from "lucide-react";

export function Settings() {
  const [settings, setSettings] = useState<SettingsType | null>(null);
  const [chromiumPath, setChromiumPath] = useState("");
  const [detecting, setDetecting] = useState(false);
  const [detectResult, setDetectResult] = useState<ChromiumDetectResult | null>(
    null,
  );
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
      setDetectResult({
        valid: false,
        path: chromiumPath,
        error: e.message || "Detection failed",
      });
    } finally {
      setDetecting(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      const data: SettingsUpdate = {
        chromium_path: chromiumPath.trim() || null,
      };
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
            <h3 className="text-sm font-medium text-gray-200">
              Chromium Binary Path
            </h3>
            <p className="text-xs text-gray-500 mt-1">
              Set a custom Chromium binary or directory. Point to the chrome
              executable or a directory containing it. Leave empty to
              auto-download.
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
              <div
                className={`flex items-start gap-2 text-xs p-2 rounded ${
                  detectResult.valid
                    ? "bg-green-900/30 text-green-400"
                    : "bg-red-900/30 text-red-400"
                }`}
              >
                {detectResult.valid ? (
                  <CheckCircle className="h-4 w-4 mt-0.5 shrink-0" />
                ) : (
                  <XCircle className="h-4 w-4 mt-0.5 shrink-0" />
                )}
                <div>
                  <div>
                    {detectResult.valid
                      ? "Valid Chromium binary"
                      : "Invalid path"}
                  </div>
                  <div className="text-gray-500">{detectResult.path}</div>
                  {detectResult.version && (
                    <div className="text-gray-500">
                      Version: {detectResult.version}
                    </div>
                  )}
                  {detectResult.error && <div>{detectResult.error}</div>}
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
                  <span className="text-gray-300">
                    {settings.chromium_resolved}
                  </span>
                ) : (
                  <span className="text-gray-500">
                    Auto-download (default)
                  </span>
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

          {error && <div className="text-xs text-red-400">{error}</div>}
        </div>
      </div>
    </div>
  );
}
