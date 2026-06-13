"""Launch/stop/track CloakBrowser instances per profile.

Simplified for native OS operation — no VNC, no Docker.
Browsers create their own native windows on each platform.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import socket
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cloakbrowser import launch_persistent_context_async

from compat import get_config as get_platform_config, is_headless

logger = logging.getLogger("cloakbrowser.suite.browser")


def _normalize_proxy(raw: str) -> str:
    """Convert common proxy formats to http://user:pass@host:port."""
    if raw.startswith(("http://", "https://", "socks5://")):
        return raw
    parts = raw.split(":")
    if len(parts) == 4:
        host, port, user, passwd = parts
        return f"http://{user}:{passwd}@{host}:{port}"
    if len(parts) == 2:
        return f"http://{raw}"
    return raw


def _validate_proxy(url: str) -> None:
    from urllib.parse import urlparse
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https", "socks5"):
        raise ValueError(
            f"Invalid proxy scheme '{parsed.scheme}'. Must be http, https, or socks5."
        )
    if not parsed.hostname:
        raise ValueError(f"Proxy URL missing hostname: {url}")
    if not parsed.port:
        raise ValueError(f"Proxy URL missing port: {url}")


def _init_profile_defaults(user_data_dir: Path) -> None:
    """Set up bookmarks and default search engine on first launch."""
    default_dir = user_data_dir / "Default"
    default_dir.mkdir(parents=True, exist_ok=True)

    bookmarks_path = default_dir / "Bookmarks"
    if not bookmarks_path.exists():
        ts = str(int(time.time() * 1_000_000))
        _id = 1

        def bm(name: str, url: str) -> dict:
            nonlocal _id
            _id += 1
            return {"type": "url", "id": str(_id), "name": name, "url": url, "date_added": ts}

        def folder(name: str, children: list) -> dict:
            nonlocal _id
            _id += 1
            return {"type": "folder", "id": str(_id), "name": name, "children": children,
                    "date_added": ts, "date_modified": ts}

        bookmarks = {
            "checksum": "",
            "roots": {
                "bookmark_bar": {
                    "type": "folder", "id": "1", "name": "Bookmarks bar",
                    "date_added": ts, "date_modified": ts,
                    "children": [
                        folder("Detection Tests", [
                            bm("Rebrowser Bot Detector", "https://bot-detector.rebrowser.net/"),
                            bm("Incolumitas", "https://bot.incolumitas.com/"),
                            bm("SannySort", "https://bot.sannysoft.com/"),
                            bm("BrowserScan Bot", "https://www.browserscan.net/bot-detection"),
                            bm("FingerprintJS Demo", "https://demo.fingerprint.com/web-scraping"),
                            bm("Pixelscan", "https://pixelscan.net/fingerprint-check"),
                            bm("CreepJS", "https://abrahamjuliot.github.io/creepjs/"),
                            bm("fingerprint-scan", "https://fingerprint-scan.com/"),
                            bm("DeviceInfo Bot", "https://deviceandbrowserinfo.com/are_you_a_bot"),
                        ]),
                        folder("Fingerprint", [
                            bm("BrowserLeaks Canvas", "https://browserleaks.com/canvas"),
                            bm("BrowserLeaks WebGL", "https://browserleaks.com/webgl"),
                            bm("BrowserLeaks Fonts", "https://browserleaks.com/fonts"),
                            bm("BrowserLeaks JS", "https://browserleaks.com/javascript"),
                            bm("FingerprintJS OSS", "https://fingerprintjs.github.io/fingerprintjs/"),
                            bm("Audio FP", "https://audiofingerprint.openwpm.com/"),
                            bm("DeviceInfo", "https://deviceandbrowserinfo.com/info_device"),
                        ]),
                        folder("Headers & TLS", [
                            bm("httpbin headers", "https://httpbin.org/headers"),
                            bm("httpbin IP", "https://httpbin.org/ip"),
                            bm("TLS Fingerprint", "https://tls.browserleaks.com/"),
                        ]),
                        folder("reCAPTCHA", [
                            bm("Google v3 Demo", "https://recaptcha-demo.appspot.com/recaptcha-v3-request-scores.php"),
                            bm("2captcha v3", "https://2captcha.com/demo/recaptcha-v3"),
                            bm("Turnstile", "https://peet.ws/turnstile-test/non-interactive.html"),
                        ]),
                    ],
                },
                "other": {"type": "folder", "id": "2", "name": "Other bookmarks", "children": []},
                "synced": {"type": "folder", "id": "3", "name": "Mobile bookmarks", "children": []},
            },
            "version": 1,
        }
        bookmarks_path.write_text(json.dumps(bookmarks, indent=2))
        logger.info("Created default bookmarks for %s", user_data_dir.name)

    # DuckDuckGo as default search engine
    prefs_path = default_dir / "Preferences"
    if not prefs_path.exists():
        prefs = {
            "default_search_provider_data": {
                "template_url_data": {
                    "keyword": "duckduckgo.com",
                    "short_name": "DuckDuckGo",
                    "url": "https://duckduckgo.com/?q={searchTerms}",
                    "suggestions_url": "https://duckduckgo.com/ac/?q={searchTerms}&type=list",
                    "favicon_url": "https://duckduckgo.com/favicon.ico",
                }
            },
            "default_search_provider": {"enabled": True},
        }
        prefs_path.write_text(json.dumps(prefs, indent=2))
        logger.info("Set DuckDuckGo as default search for %s", user_data_dir.name)


BASE_CDP_PORT = 5100
CDP_PORT_RANGE = 100


@dataclass
class RunningProfile:
    profile_id: str
    context: Any  # Playwright BrowserContext
    cdp_port: int


class BrowserManager:
    """Manages browser instance lifecycle.

    On Linux, sets $DISPLAY so Chrome creates a native X11/Wayland window.
    On Windows and macOS, Chrome creates native windows automatically.
    When no GUI is available (headless Linux), launches headless by default.
    """

    def __init__(self):
        self.running: dict[str, RunningProfile] = {}
        self._launching: set[str] = set()
        self._lock = asyncio.Lock()
        self._next_cdp_port = BASE_CDP_PORT
        self._auto_launch_task: asyncio.Task | None = None
        self._platform_config = get_platform_config()

    async def launch(self, profile: dict[str, Any]) -> RunningProfile:
        """Launch a browser instance for the given profile."""
        profile_id = profile["id"]

        async with self._lock:
            if profile_id in self.running or profile_id in self._launching:
                raise RuntimeError(f"Profile {profile_id} is already running")
            self._launching.add(profile_id)

        cdp_port = self._allocate_cdp_port()

        user_data_dir = Path(profile["user_data_dir"])
        user_data_dir.mkdir(parents=True, exist_ok=True)

        # Clean stale lock files
        for lock_file in ("SingletonLock", "SingletonCookie", "SingletonSocket"):
            (user_data_dir / lock_file).unlink(missing_ok=True)

        _init_profile_defaults(user_data_dir)

        try:
            extra_args = self._build_fingerprint_args(profile)
            extra_args += profile.get("launch_args") or []
            extra_args.append(f"--remote-debugging-port={cdp_port}")

            # Check for headless environment
            headless = bool(profile.get("headless", False))
            if not headless and is_headless():
                logger.info("No GUI detected, falling back to headless mode for %s", profile_id)
                headless = True

            raw_proxy = profile.get("proxy") or None
            proxy = _normalize_proxy(raw_proxy) if raw_proxy else None
            if proxy:
                _validate_proxy(proxy)

            # Build environment: start with platform-specific env (DISPLAY on Linux)
            env = dict(os.environ)
            env.update(self._platform_config.display_env)

            context = await asyncio.wait_for(
                launch_persistent_context_async(
                    user_data_dir=str(user_data_dir),
                    headless=headless,
                    proxy=proxy,
                    args=extra_args,
                    timezone=profile.get("timezone") or None,
                    locale=profile.get("locale") or None,
                    humanize=bool(profile.get("humanize", False)),
                    human_preset=profile.get("human_preset", "default"),
                    geoip=bool(profile.get("geoip", False)),
                    color_scheme=profile.get("color_scheme") or None,
                    user_agent=profile.get("user_agent") or None,
                    viewport={
                        "width": profile.get("screen_width", 1920),
                        "height": profile.get("screen_height", 1080) - 133,
                    },
                    env=env,
                ),
                timeout=60.0,
            )

            # Clipboard capture init script
            _clipboard_init_js = """
                window.__clipboardText = '';
                const _captureSelection = () => {
                    const sel = window.getSelection();
                    let text = sel ? sel.toString() : '';
                    if (!text) {
                        const el = document.activeElement;
                        if (el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA')
                            && el.selectionStart != null && el.selectionEnd != null) {
                            text = el.value.substring(el.selectionStart, el.selectionEnd);
                        }
                    }
                    if (text) window.__clipboardText = text;
                };
                document.addEventListener('copy', _captureSelection);
                document.addEventListener('keydown', (e) => {
                    if ((e.ctrlKey || e.metaKey) && e.key === 'c' && !e.altKey && !e.shiftKey) {
                        _captureSelection();
                    }
                });
            """
            await context.add_init_script(_clipboard_init_js)
            for p in context.pages:
                try:
                    await p.evaluate(_clipboard_init_js)
                except Exception as exc:
                    logger.debug("Clipboard init failed on existing page: %s", exc)

            running = RunningProfile(
                profile_id=profile_id,
                context=context,
                cdp_port=cdp_port,
            )

            context.on("close", lambda: asyncio.ensure_future(
                self._on_browser_closed(profile_id)
            ))

            async with self._lock:
                self.running[profile_id] = running
                self._launching.discard(profile_id)

            logger.info("Launched profile %s (cdp_port=%d)", profile_id, cdp_port)
            return running

        except BaseException:
            async with self._lock:
                self._launching.discard(profile_id)
            raise

    async def _on_browser_closed(self, profile_id: str):
        async with self._lock:
            running = self.running.pop(profile_id, None)

        if running:
            logger.info("Browser closed for profile %s", profile_id)

    async def stop(self, profile_id: str):
        async with self._lock:
            running = self.running.pop(profile_id, None)

        if not running:
            return

        logger.info("Stopping profile %s", profile_id)
        try:
            await running.context.close()
        except Exception as exc:
            logger.warning("Error closing context for %s: %s", profile_id, exc)

    def get_status(self, profile_id: str) -> dict[str, Any]:
        running = self.running.get(profile_id)
        if running:
            return {
                "status": "running",
                "cdp_url": f"/api/profiles/{profile_id}/cdp",
            }
        return {"status": "stopped", "cdp_url": None}

    async def cleanup_all(self):
        async with self._lock:
            profile_ids = list(self.running.keys())
        for pid in profile_ids:
            await self.stop(pid)

    async def auto_launch_all(self):
        from . import database as db

        profiles = db.list_profiles()
        auto_profiles = [p for p in profiles if p.get("auto_launch")]
        if not auto_profiles:
            logger.info("No profiles configured for auto-launch")
            return

        logger.info("Auto-launching %d profile(s)...", len(auto_profiles))
        for profile in auto_profiles:
            try:
                await asyncio.wait_for(self.launch(profile), timeout=60)
                logger.info("Auto-launched profile %s (%s)", profile["name"], profile["id"])
            except Exception as exc:
                logger.error("Auto-launch failed for %s (%s): %s",
                             profile["name"], profile["id"], exc)
        logger.info("Auto-launch complete: %d running", len(self.running))

    def _allocate_cdp_port(self) -> int:
        for _ in range(CDP_PORT_RANGE):
            port = self._next_cdp_port
            self._next_cdp_port = BASE_CDP_PORT + (
                (self._next_cdp_port + 1 - BASE_CDP_PORT) % CDP_PORT_RANGE
            )
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(("127.0.0.1", port))
                    return port
                except OSError:
                    continue
        raise ValueError(f"No free CDP ports in range {BASE_CDP_PORT}-{BASE_CDP_PORT + CDP_PORT_RANGE - 1}")

    def _build_fingerprint_args(self, profile: dict[str, Any]) -> list[str]:
        args: list[str] = [
            "--disable-infobars",
            "--test-type",
        ]

        # SwiftShader (software GPU) causes address bar to not render on
        # Windows and conflicts with GPU renderer spoofing.  Only use it on
        # headless Linux where no real GPU is available.
        if self._platform_config.name == "linux" and is_headless():
            args.append("--use-angle=swiftshader")

        # Add platform-specific extra args
        args.extend(self._platform_config.extra_chrome_args)

        seed = profile.get("fingerprint_seed")
        if seed is not None:
            args.append(f"--fingerprint={seed}")

        p = profile.get("platform")
        if p:
            args.append(f"--fingerprint-platform={p}")

        vendor = profile.get("gpu_vendor")
        if vendor:
            args.append(f"--fingerprint-gpu-vendor={vendor}")

        renderer = profile.get("gpu_renderer")
        if renderer:
            args.append(f"--fingerprint-gpu-renderer={renderer}")

        hw = profile.get("hardware_concurrency")
        if hw is not None:
            args.append(f"--fingerprint-hardware-concurrency={hw}")

        sw = profile.get("screen_width")
        sh = profile.get("screen_height")
        if sw:
            args.append(f"--fingerprint-screen-width={sw}")
        if sh:
            args.append(f"--fingerprint-screen-height={sh}")

        return args
