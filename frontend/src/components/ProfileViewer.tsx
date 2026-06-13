import { useState } from "react";
import { ClipboardCopy, Code2, Camera, RotateCcw } from "lucide-react";
import { api } from "../lib/api";

interface ProfileViewerProps {
  profileId: string;
  cdpUrl: string | null;
}

export function ProfileViewer({ profileId, cdpUrl }: ProfileViewerProps) {
  const [cdpCopied, setCdpCopied] = useState(false);
  const [screenshotUrl, setScreenshotUrl] = useState<string | null>(null);
  const [screenshotLoading, setScreenshotLoading] = useState(false);

  const takeScreenshot = async () => {
    setScreenshotLoading(true);
    try {
      const blob = await api.screenshot(profileId);
      const url = URL.createObjectURL(blob);
      setScreenshotUrl((prev) => {
        if (prev) URL.revokeObjectURL(prev);
        return url;
      });
    } catch (err) {
      console.error("[screenshot] failed:", err);
    } finally {
      setScreenshotLoading(false);
    }
  };

  return (
    <div className="relative h-full flex flex-col">
      <div className="flex items-center justify-between px-3 py-1.5 bg-surface-1 border-b border-border">
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-emerald-400" />
          <span className="text-xs text-gray-400">Running</span>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={takeScreenshot}
            disabled={screenshotLoading}
            className={`p-1 ${screenshotLoading ? "text-gray-600" : "text-gray-500 hover:text-gray-300"}`}
            title="Take screenshot"
          >
            {screenshotLoading ? (
              <RotateCcw className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Camera className="h-3.5 w-3.5" />
            )}
          </button>
          {cdpUrl && (
            <button
              onClick={() => {
                const base = `${window.location.protocol}//${window.location.host}${cdpUrl}`;
                navigator.clipboard
                  ?.writeText(base)
                  .then(() => {
                    setCdpCopied(true);
                    setTimeout(() => setCdpCopied(false), 2000);
                  })
                  .catch((err) => console.warn("[cdp] copy failed:", err));
              }}
              className={`p-1 ${cdpCopied ? "text-emerald-400" : "text-gray-500 hover:text-gray-300"}`}
              title={cdpCopied ? "Copied!" : "Copy CDP endpoint URL"}
            >
              <Code2 className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
      </div>

      <div
        className="flex-1 flex flex-col items-center justify-center bg-surface-0 p-8"
        style={{ minHeight: 0 }}
      >
        <div className="max-w-lg w-full text-center space-y-4">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-surface-2 mb-2">
            <Code2 className="h-6 w-6 text-gray-400" />
          </div>
          <h3 className="text-sm font-medium text-gray-300">Browser Running</h3>
          <p className="text-xs text-gray-500 leading-relaxed">
            The browser is running with a native window on your desktop. Connect
            via the Chrome DevTools Protocol (CDP) for automated control.
          </p>

          {cdpUrl && (
            <div className="bg-surface-1 rounded-lg p-3 text-left">
              <label className="text-xs text-gray-500 mb-1 block">
                CDP Endpoint URL
              </label>
              <div className="flex items-center gap-2">
                <code className="flex-1 text-xs bg-surface-2 px-2 py-1.5 rounded text-gray-300 truncate font-mono">
                  {window.location.protocol}//{window.location.host}
                  {cdpUrl}
                </code>
                <button
                  onClick={() => {
                    const base = `${window.location.protocol}//${window.location.host}${cdpUrl}`;
                    navigator.clipboard?.writeText(base).then(() => {
                      setCdpCopied(true);
                      setTimeout(() => setCdpCopied(false), 2000);
                    });
                  }}
                  className={`flex-shrink-0 p-1.5 rounded ${cdpCopied ? "text-emerald-400 bg-emerald-400/10" : "text-gray-400 hover:text-gray-200 hover:bg-surface-2"}`}
                >
                  <ClipboardCopy className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
          )}

          <div className="bg-surface-1 rounded-lg p-3 text-left">
            <label className="text-xs text-gray-500 mb-1 block">
              Quick Start &mdash; Playwright
            </label>
            <pre className="text-xs bg-surface-2 px-2 py-1.5 rounded text-gray-400 font-mono overflow-x-auto">{`const browser = await playwright.chromium.connectOverCDP(
  "${window.location.protocol}//${window.location.host}${cdpUrl}"
);`}</pre>
          </div>

          <button
            onClick={takeScreenshot}
            disabled={screenshotLoading}
            className="inline-flex items-center gap-1.5 text-xs bg-accent text-white px-3 py-1.5 rounded hover:bg-accent/90 disabled:opacity-50"
          >
            {screenshotLoading ? (
              <>
                <RotateCcw className="h-3 w-3 animate-spin" /> Capturing...
              </>
            ) : (
              <>
                <Camera className="h-3 w-3" /> Take Screenshot
              </>
            )}
          </button>
        </div>

        {screenshotUrl && (
          <div className="mt-6 w-full max-w-4xl">
            <div className="bg-surface-1 rounded-lg overflow-hidden border border-border">
              <div className="flex items-center justify-between px-3 py-1.5 bg-surface-2 border-b border-border">
                <span className="text-xs text-gray-500">Screenshot</span>
                <button
                  onClick={() => {
                    setScreenshotUrl((prev) => {
                      if (prev) URL.revokeObjectURL(prev);
                      return null;
                    });
                  }}
                  className="text-xs text-gray-500 hover:text-gray-300"
                >
                  Close
                </button>
              </div>
              <img
                src={screenshotUrl}
                alt="Browser screenshot"
                className="w-full h-auto"
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
