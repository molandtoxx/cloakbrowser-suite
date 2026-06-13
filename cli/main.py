"""CloakBrowser Suite — CLI entry point.

Usage:
    cloakbrowser-suite start                   # Start the web server
    cloakbrowser-suite profile list            # List all profiles
    cloakbrowser-suite profile create          # Create a new profile
    cloakbrowser-suite profile delete <id>     # Delete a profile
    cloakbrowser-suite browser launch <id>     # Launch a browser
    cloakbrowser-suite browser stop <id>       # Stop a browser
    cloakbrowser-suite browser list            # List running browsers
    cloakbrowser-suite status                  # Show system status
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

import click
import httpx


DEFAULT_BASE_URL = "http://127.0.0.1:8080"
AUTH_TOKEN = os.environ.get("CLOAKBROWSER_AUTH_TOKEN", "")


def _client(base_url: str = DEFAULT_BASE_URL) -> httpx.Client:
    headers = {}
    if AUTH_TOKEN:
        headers["Authorization"] = f"Bearer {AUTH_TOKEN}"
    return httpx.Client(base_url=base_url.rstrip("/"), headers=headers, trust_env=False)


def _fmt(profile: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": profile.get("id", "")[:8] + "…",
        "name": profile.get("name", ""),
        "platform": profile.get("platform", ""),
        "status": profile.get("status", ""),
        "tags": ",".join(t["tag"] for t in profile.get("tags", [])),
        "proxy": (profile.get("proxy") or "")[:40],
        "auto_launch": "✓" if profile.get("auto_launch") else "",
    }


def _print_table(rows: list[dict], cols: list[str] | None = None) -> None:
    if not rows:
        click.echo("(no profiles)")
        return
    if cols:
        keys = cols
    else:
        keys = list(rows[0].keys())
    widths = [len(k) for k in keys]
    for r in rows:
        for i, k in enumerate(keys):
            widths[i] = max(widths[i], len(str(r.get(k, ""))))
    sep = " | ".join("-" * w for w in widths)
    header = " | ".join(k.ljust(w) for k, w in zip(keys, widths))
    click.echo(header)
    click.echo(sep)
    for r in rows:
        row = " | ".join(str(r.get(k, "")).ljust(w) for k, w in zip(keys, widths))
        click.echo(row)


# ── CLI Group ─────────────────────────────────────────────────────────────────


@click.group()
def main():
    """CloakBrowser Suite — cross-platform fingerprint browser manager."""


# ── Profile Commands ──────────────────────────────────────────────────────────


@main.group()
def profile():
    """Manage browser profiles."""


@profile.command("list")
@click.option("--status", type=click.Choice(["running", "stopped"]), help="Filter by status")
@click.option("--tag", multiple=True, help="Filter by tag")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def profile_list(status: str | None, tag: tuple[str, ...], as_json: bool):
    """List all browser profiles."""
    c = _client()
    r = c.get("/api/profiles")
    r.raise_for_status()
    profiles: list[dict] = r.json()

    if status:
        profiles = [p for p in profiles if p.get("status") == status]
    if tag:
        filter_tags = set(tag)
        profiles = [p for p in profiles if {t["tag"] for t in p.get("tags", [])} & filter_tags]

    if as_json:
        click.echo(json.dumps(profiles, indent=2, default=str))
        return

    if not profiles:
        click.echo("(no matching profiles)")
        return

    rows = [_fmt(p) for p in profiles]
    cols = ["id", "name", "platform", "status", "tags", "proxy", "auto_launch"]
    _print_table(rows, cols)
    click.echo(f"\nTotal: {len(profiles)} profiles")


@profile.command("create")
@click.option("--name", prompt=True, help="Profile name")
@click.option("--platform", type=click.Choice(["windows", "macos", "linux"]), default="windows")
@click.option("--proxy", help="Proxy URL (http://user:pass@host:port)")
@click.option("--seed", type=int, help="Fingerprint seed (random if not set)")
@click.option("--humanize", is_flag=True, help="Enable human-like behavior")
@click.option("--headless", is_flag=True, help="Headless mode (no window)")
@click.option("--geoip", is_flag=True, help="Enable GeoIP location")
@click.option("--auto-launch", is_flag=True, help="Auto-launch on server start")
def profile_create(name: str, platform: str, proxy: str | None,
                   seed: int | None, humanize: bool, headless: bool,
                   geoip: bool, auto_launch: bool):
    """Create a new browser profile."""
    c = _client()
    data: dict[str, Any] = {
        "name": name,
        "platform": platform,
        "humanize": humanize,
        "headless": headless,
        "geoip": geoip,
        "auto_launch": auto_launch,
    }
    if proxy:
        data["proxy"] = proxy
    if seed is not None:
        data["fingerprint_seed"] = seed

    r = c.post("/api/profiles", json=data)
    if r.status_code == 201:
        result = r.json()
        click.echo(f"Created profile: {result['name']} (id={result['id'][:8]}…)")
    else:
        click.echo(f"Error: {r.json().get('detail', r.text)}", err=True)
        sys.exit(1)


@profile.command("delete")
@click.argument("profile_id")
@click.option("--force", is_flag=True, help="Skip confirmation")
def profile_delete(profile_id: str, force: bool):
    """Delete a profile and its data."""
    c = _client()

    r = c.get(f"/api/profiles/{profile_id}")
    if r.status_code != 200:
        click.echo(f"Profile not found: {profile_id}", err=True)
        sys.exit(1)

    profile = r.json()
    if not force:
        click.confirm(
            f"Delete profile '{profile['name']}' ({profile_id[:8]}…)?",
            abort=True,
        )

    r = c.delete(f"/api/profiles/{profile_id}")
    if r.status_code == 200:
        click.echo(f"Deleted profile {profile_id[:8]}…")
    else:
        click.echo(f"Error: {r.json().get('detail', r.text)}", err=True)
        sys.exit(1)


@profile.command("update")
@click.argument("profile_id")
@click.option("--name", help="New name")
@click.option("--proxy", help="Proxy URL")
@click.option("--auto-launch", type=bool, help="Auto-launch on server start")
def profile_update(profile_id: str, **kwargs):
    """Update profile settings."""
    c = _client()
    data = {k: v for k, v in kwargs.items() if v is not None}
    r = c.put(f"/api/profiles/{profile_id}", json=data)
    if r.status_code == 200:
        click.echo(f"Updated profile {profile_id[:8]}…")
    else:
        click.echo(f"Error: {r.json().get('detail', r.text)}", err=True)
        sys.exit(1)


# ── Browser Commands ──────────────────────────────────────────────────────────


@main.group()
def browser():
    """Launch and control browsers."""


@browser.command("launch")
@click.argument("profile_id")
def browser_launch(profile_id: str):
    """Launch a browser profile (opens native window)."""
    c = _client()
    r = c.post(f"/api/profiles/{profile_id}/launch")
    if r.status_code == 200:
        data = r.json()
        click.echo(f"Launched {profile_id[:8]}… (CDP available)")
    elif r.status_code == 409:
        click.echo("Profile is already running")
    else:
        click.echo(f"Error: {r.json().get('detail', r.text)}", err=True)
        sys.exit(1)


@browser.command("stop")
@click.argument("profile_id")
def browser_stop(profile_id: str):
    """Stop a running browser."""
    c = _client()
    r = c.post(f"/api/profiles/{profile_id}/stop")
    if r.status_code == 200:
        click.echo(f"Stopped {profile_id[:8]}…")
    elif r.status_code == 404:
        click.echo("Profile is not running")
    else:
        click.echo(f"Error: {r.json().get('detail', r.text)}", err=True)
        sys.exit(1)


@browser.command("list")
def browser_list():
    """List running browsers."""
    c = _client()
    r = c.get("/api/profiles")
    r.raise_for_status()
    running = [p for p in r.json() if p.get("status") == "running"]
    if not running:
        click.echo("No running browsers")
        return

    rows = []
    for p in running:
        rows.append({
            "id": p["id"][:8] + "…",
            "name": p["name"],
            "platform": p.get("platform", ""),
            "cdp": f"/api/profiles/{p['id']}/cdp",
        })
    _print_table(rows, ["id", "name", "platform", "cdp"])
    click.echo(f"\nTotal: {len(running)} running")


@browser.command("screenshot")
@click.argument("profile_id")
@click.option("--output", "-o", default=None, help="Output path for PNG")
def browser_screenshot(profile_id: str, output: str | None):
    """Take a screenshot of a running browser."""
    c = _client()
    r = c.get(f"/api/profiles/{profile_id}/screenshot")
    if r.status_code != 200:
        click.echo(f"Error: {r.json().get('detail', r.text)}", err=True)
        sys.exit(1)

    if output:
        Path(output).write_bytes(r.content)
        click.echo(f"Screenshot saved to {output}")
    else:
        safe_name = f"screenshot-{profile_id[:8]}-{int(time.time())}.png"
        Path(safe_name).write_bytes(r.content)
        click.echo(f"Screenshot saved to {safe_name}")


# ── Server Commands ───────────────────────────────────────────────────────────


@main.command()
@click.option("--port", default=8080, help="Server port (default: 8080)")
@click.option("--host", default="127.0.0.1", help="Bind address (default: 127.0.0.1)")
@click.option("--no-open", is_flag=True, help="Don't open browser on start")
def start(port: int, host: str, no_open: bool):
    """Start the CloakBrowser Suite server.

    Launches the web UI at http://<host>:<port> and opens it
    in your default browser.
    """
    from backend.main import app
    import webbrowser
    import uvicorn

    url = f"http://{host}:{port}"
    click.echo(f"Starting CloakBrowser Suite at {url}")

    if not no_open:
        # Brief delay then open browser
        import threading
        threading.Timer(2.0, lambda: webbrowser.open(url)).start()

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="warning",
    )


# ── Status Command ────────────────────────────────────────────────────────────


@main.command()
@click.option("--detail", is_flag=True, help="Show per-profile details")
def status(detail: bool):
    """Show system status."""
    c = _client()
    try:
        r = c.get("/api/status")
        r.raise_for_status()
        s = r.json()
    except httpx.ConnectError:
        click.echo("Server is not running. Use 'cloakbrowser-suite start' to start it.")
        sys.exit(1)

    click.echo(f"Running:   {s.get('running_count', '?')} browser(s)")
    click.echo(f"Profiles:  {s.get('profiles_total', '?')} total")
    click.echo(f"Binary:    {s.get('binary_version', '?')}")

    if detail:
        r2 = c.get("/api/profiles")
        r2.raise_for_status()
        profiles = r2.json()
        running = [p for p in profiles if p.get("status") == "running"]
        stopped = [p for p in profiles if p.get("status") == "stopped"]
        click.echo(f"\nRunning ({len(running)}):")
        for p in running:
            click.echo(f"  {p['id'][:8]}…  {p['name']}")
        click.echo(f"\nStopped ({len(stopped)}):")
        for p in stopped[:10]:
            click.echo(f"  {p['id'][:8]}…  {p['name']}")
        if len(stopped) > 10:
            click.echo(f"  … and {len(stopped) - 10} more")


if __name__ == "__main__":
    main()
