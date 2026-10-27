"""Direct site connectors: query each marketplace's own search the way its website does.

Rules every connector follows (see docs/research/fashion_sites.md and furniture_sites.md):
- one on-demand query per shopper search (plus a sold query when pricing), never bulk crawling;
- logged out, public results only; no accounts, no CAPTCHA solving, no proxy rotation to dodge blocks;
- robots.txt respected for the paths we call; a polite, identifying User-Agent;
- a site that answers 403/429 or a challenge page is benched for a while (circuit breaker), and the
  engine falls back to web search for it. We never try to get around a block.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from urllib.parse import urlparse

import httpx

from ...models import Listing
from ..base import USER_AGENT, SearchPlan
from ..pagefetch import Robots

BROWSER_ACCEPT = "application/json, text/plain, */*"


class Blocked(Exception):
    """The site refused us (403/429/challenge). We stop, we don't retry around it."""


@dataclass
class Breaker:
    """Per-site circuit breaker: after a refusal, don't call that site again for `cooldown_s`."""

    cooldown_s: float = 900
    _until: dict[str, float] = field(default_factory=dict)

    def open(self, site: str) -> bool:
        return time.time() < self._until.get(site, 0)

    def trip(self, site: str, seconds: float | None = None) -> None:
        self._until[site] = time.time() + (seconds or self.cooldown_s)


BREAKER = Breaker()
ROBOTS = Robots()
_HOST_LOCKS: dict[str, asyncio.Semaphore] = {}


@dataclass
class Query:
    text: str
    sold: bool = False  # sold/completed listings, for pricing
    min_price_cents: int | None = None
    max_price_cents: int | None = None
    size: str | None = None
    limit: int = 30


class SiteConnector:
    """Subclass per site: set `name`, `domain`, `segments`, implement `_search`."""

    name: str = ""
    domain: str = ""
    segments: tuple[str, ...] = ()  # router segments this site is good for
    supports_sold: bool = False
    sold_price_is_list: bool = False  # site shows the last ask on sold items, not what was paid
    check_robots: bool = True

    async def search(self, plan: SearchPlan, client: httpx.AsyncClient) -> list[Listing]:
        """Engine entry point: exact queries first, then one similar query; sold when supported."""
        if BREAKER.open(self.name):
            raise Blocked(f"{self.name} is cooling down after refusing us")
        queries = [Query(q) for q in plan.exact_queries[:2]] + [Query(q) for q in plan.similar_queries[:1]]
        if self.supports_sold and plan.exact_queries:
            queries.append(Query(plan.exact_queries[0], sold=True))
        results = await asyncio.gather(*(self._guarded(q, client) for q in queries), return_exceptions=True)
        out: list[Listing] = []
        errors = []
        for q, r in zip(queries, results):
            if isinstance(r, Exception):
                errors.append(r)
                continue
            for listing in r:
                listing.found_via = f"{self.name}:{'sold' if q.sold else 'search'}:{q.text}"
                if q.sold:
                    listing.status = "sold"
                    listing.sold_price_is_list = self.sold_price_is_list
            out += r
        if errors and not out:
            raise errors[0]
        return out

    async def _guarded(self, q: Query, client: httpx.AsyncClient) -> list[Listing]:
        lock = _HOST_LOCKS.setdefault(self.domain, asyncio.Semaphore(2))  # at most 2 in flight per site
        async with lock:
            return await self._search(q, client)

    async def _search(self, q: Query, client: httpx.AsyncClient) -> list[Listing]:
        raise NotImplementedError

    # ---- helpers for subclasses ----

    def headers(self, **extra: str) -> dict:
        return {"User-Agent": USER_AGENT, "Accept": BROWSER_ACCEPT, "Accept-Language": "en-US,en;q=0.9", **extra}

    async def get(self, client: httpx.AsyncClient, url: str, **kw) -> httpx.Response:
        return await self._send(client, "GET", url, **kw)

    async def post(self, client: httpx.AsyncClient, url: str, **kw) -> httpx.Response:
        return await self._send(client, "POST", url, **kw)

    async def _send(self, client: httpx.AsyncClient, method: str, url: str, **kw) -> httpx.Response:
        if self.check_robots and not await ROBOTS.allowed(url, client):
            raise Blocked(f"robots.txt disallows {urlparse(url).path} on {self.domain}")
        kw.setdefault("headers", self.headers())
        kw.setdefault("timeout", 5.0)
        r = await client.request(method, url, **kw)
        if r.status_code in (401, 403, 429) or _is_challenge(r):
            retry = r.headers.get("retry-after")
            BREAKER.trip(self.name, float(retry) if retry and retry.isdigit() else None)
            raise Blocked(f"{self.name} answered {r.status_code}")
        r.raise_for_status()
        return r


def _is_challenge(r: httpx.Response) -> bool:
    """Bot-protection interstitials (Cloudflare, PerimeterX, DataDome) come back 200 or 403 with HTML."""
    if "json" in r.headers.get("content-type", ""):
        return False
    head = r.text[:3000].lower() if r.content else ""
    return any(s in head for s in ("cf-challenge", "challenge-platform", "px-captcha", "datadome", "captcha-delivery"))


def first(d: dict | None, *paths: str, default=None):
    """first(item, 'price.amount', 'price') -> the first dotted path that exists and isn't empty."""
    for path in paths:
        cur = d
        for part in path.split("."):
            if isinstance(cur, dict):
                cur = cur.get(part)
            elif isinstance(cur, list) and part.isdigit() and int(part) < len(cur):
                cur = cur[int(part)]
            else:
                cur = None
                break
        if cur not in (None, "", []):
            return cur
    return default
