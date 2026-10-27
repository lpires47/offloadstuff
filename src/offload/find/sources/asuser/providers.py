"""Where the user's browser session lives.

LocalProvider: Chromium on our server, with each user's per-site session (cookies) stored after they
sign in themselves (`offload login`, or the live-view sign-in in production). Good for development.

BrowserbaseProvider: a hosted browser per user with a persistent "context" (their cookies), and a
Live View link the user opens to sign in or pass a check themselves; we never see passwords.
Docs: https://docs.browserbase.com/platform/identity/authentication.md
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import httpx

from ....config import settings
from ...sources.base import USER_AGENT

VIEWPORT = {"width": 1280, "height": 800}


def _safe(s: str) -> str:
    return "".join(ch for ch in s if ch.isalnum() or ch in "-_")


class LocalProvider:
    def __init__(self, root: Path | None = None, headless: bool = True) -> None:
        self.root = root or settings().sessions_dir
        self.headless = headless
        self._pw = None
        self._browser = None
        self._contexts: dict[tuple[str, str], object] = {}

    def path(self, user_id: str, site: str) -> Path:
        return self.root / _safe(user_id) / f"{_safe(site)}.json"

    async def _ensure(self):
        if self._browser is None:
            from playwright.async_api import async_playwright

            self._pw = await async_playwright().start()
            self._browser = await self._pw.chromium.launch(headless=self.headless)
        return self._browser

    async def context(self, user_id: str, site: str):
        key = (user_id, site)
        if key not in self._contexts:  # kept warm between searches: no launch cost per search
            browser = await self._ensure()
            path = self.path(user_id, site)
            self._contexts[key] = await browser.new_context(
                viewport=VIEWPORT, locale="en-US", timezone_id="America/Los_Angeles",
                storage_state=str(path) if path.exists() else None,
            )
        return self._contexts[key]

    async def save(self, user_id: str, site: str, context) -> None:
        path = self.path(user_id, site)
        path.parent.mkdir(parents=True, exist_ok=True)
        await context.storage_state(path=str(path))

    async def close(self) -> None:
        for c in self._contexts.values():
            await c.close()
        if self._browser:
            await self._browser.close()
        if self._pw:
            await self._pw.stop()


class BrowserbaseProvider:
    """One hosted browser session per user, reusing their persistent context id per site [verify API]."""

    API = "https://api.browserbase.com/v1"

    def __init__(self, api_key: str | None = None, project_id: str | None = None, registry: Path | None = None):
        self.api_key = api_key or os.environ["BROWSERBASE_API_KEY"]
        self.project_id = project_id or os.environ["BROWSERBASE_PROJECT_ID"]
        self.registry = registry or (settings().sessions_dir / "browserbase_contexts.json")
        self._pw = None
        self._browsers: dict[str, object] = {}

    def _contexts(self) -> dict:
        return json.loads(self.registry.read_text()) if self.registry.exists() else {}

    async def _context_id(self, client: httpx.AsyncClient, user_id: str) -> str:
        reg = self._contexts()
        if user_id not in reg:
            r = await client.post(f"{self.API}/contexts", headers={"X-BB-API-Key": self.api_key},
                                  json={"projectId": self.project_id})
            r.raise_for_status()
            reg[user_id] = r.json()["id"]
            self.registry.parent.mkdir(parents=True, exist_ok=True)
            self.registry.write_text(json.dumps(reg))
        return reg[user_id]

    async def session(self, user_id: str) -> dict:
        """A hosted browser for this user (one context holds all their sites' sign-ins)."""
        async with httpx.AsyncClient(timeout=20, headers={"User-Agent": USER_AGENT}) as client:
            ctx = await self._context_id(client, user_id)
            r = await client.post(f"{self.API}/sessions", headers={"X-BB-API-Key": self.api_key}, json={
                "projectId": self.project_id,
                "browserSettings": {"context": {"id": ctx, "persist": True}, "viewport": VIEWPORT},
                "keepAlive": True,
            })
            r.raise_for_status()
            return r.json()  # includes connectUrl and id; live view via /sessions/{id}/debug

    async def live_view_url(self, session_id: str) -> str:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(f"{self.API}/sessions/{session_id}/debug", headers={"X-BB-API-Key": self.api_key})
            r.raise_for_status()
            return r.json()["debuggerFullscreenUrl"]

    async def context(self, user_id: str, site: str):
        if user_id not in self._browsers:
            from playwright.async_api import async_playwright

            self._pw = self._pw or await async_playwright().start()
            s = await self.session(user_id)
            self._browsers[user_id] = await self._pw.chromium.connect_over_cdp(s["connectUrl"])
        return self._browsers[user_id].contexts[0]

    async def save(self, user_id: str, site: str, context) -> None:
        return None  # persist=True saves the context when the session ends


class Consents:
    """Which sites each user has connected and allowed us to act on, and for what."""

    SCOPES = ("search", "list", "message", "buy")

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or (settings().sessions_dir / "consents")

    def _path(self, user_id: str) -> Path:
        return self.root / f"{_safe(user_id)}.json"

    def get(self, user_id: str) -> dict:
        p = self._path(user_id)
        return json.loads(p.read_text()) if p.exists() else {}

    def grant(self, user_id: str, site: str, scopes: list[str]) -> None:
        bad = set(scopes) - set(self.SCOPES)
        if bad:
            raise ValueError(f"unknown scopes {bad}")
        data = self.get(user_id)
        data[site] = {"scopes": sorted(set(scopes)), "granted_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
        p = self._path(user_id)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data, indent=1))

    def revoke(self, user_id: str, site: str) -> None:
        data = self.get(user_id)
        data.pop(site, None)
        self._path(user_id).write_text(json.dumps(data, indent=1))

    def sites_for(self, user_id: str, scope: str = "search") -> set[str]:
        return {s for s, v in self.get(user_id).items() if scope in v.get("scopes", [])}
