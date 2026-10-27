"""Reach platforms that have no public API through a web search API, then read each listing page.

Search engines already index Poshmark, Depop, Grailed, Chairish, 1stDibs and the rest. We ask for the
item on the sites the router picked, then read the top pages for price and condition. Pages we may
not read stay in the results as links with the search snippet.
"""

from __future__ import annotations

import asyncio
from typing import Protocol
from urllib.parse import urlparse

import httpx

from ..models import Listing
from ..router import PRIORS
from .base import SearchPlan

RESALE_DOMAINS = {d for ds in PRIORS.values() for d in ds} | {"ebay.com", "etsy.com"}
from .pagefetch import Robots, fetch_listing


class SearchHit(Protocol):
    url: str
    title: str
    snippet: str
    thumbnail: str | None


class _Hit:
    def __init__(self, url: str, title: str, snippet: str = "", thumbnail: str | None = None) -> None:
        self.url, self.title, self.snippet, self.thumbnail = url, title, snippet, thumbnail


class BraveSearch:
    """Brave Search API (independent index). https://api-dashboard.search.brave.com/app/documentation"""

    name = "brave"
    URL = "https://api.search.brave.com/res/v1/web/search"

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    async def query(self, q: str, client: httpx.AsyncClient, count: int = 20) -> list[_Hit]:
        r = await client.get(
            self.URL,
            params={"q": q, "count": count, "country": "us", "safesearch": "moderate"},
            headers={"X-Subscription-Token": self.api_key, "Accept": "application/json"},
        )
        r.raise_for_status()
        results = r.json().get("web", {}).get("results", [])
        return [
            _Hit(x["url"], x.get("title", ""), x.get("description", ""), (x.get("thumbnail") or {}).get("src"))
            for x in results
        ]


def site_query(q: str, domains: list[str]) -> str:
    return f"{q} ({' OR '.join(f'site:{d}' for d in domains)})" if domains else q


def _looks_like_listing(url: str) -> bool:
    """Skip category, search and blog pages; keep item pages."""
    path = urlparse(url).path.lower()
    if "/products/" in path or "/product/" in path:
        return True
    skip = ("/search", "/blog", "/category", "/categories", "/collections/", "/brand/", "/designers/")
    return len(path) > 1 and not any(s in path for s in skip)


class WebSearchSource:
    """One source per site group, e.g. fashion resale or furniture resale."""

    def __init__(
        self,
        name: str,
        engine: BraveSearch,
        *,
        domains: list[str] | None = None,
        fetch_top: int = 8,
        group: str = "resale",
    ) -> None:
        self.name = name
        self.engine = engine
        self.domains = domains
        self.fetch_top = fetch_top
        self.group = group  # "resale" -> plan.domains, "retail" -> plan.retail_domains or the open web
        self.robots = Robots()

    async def search(self, plan: SearchPlan, client: httpx.AsyncClient) -> list[Listing]:
        domains = self.domains if self.domains is not None else (
            plan.domains if self.group == "resale" else plan.retail_domains
        )
        queries = [site_query(q, domains) for q in plan.exact_queries[:2]]
        if self.group == "resale":
            queries += [site_query(q, domains) for q in plan.similar_queries[:1]]
        else:
            queries = [f"{q} buy new" for q in plan.exact_queries[:1]] if not domains else queries
        batches = await asyncio.gather(*(self.engine.query(q, client) for q in queries))
        hits: dict[str, _Hit] = {}
        for batch in batches:
            for h in batch:
                if _looks_like_listing(h.url):
                    hits.setdefault(h.url, h)
        top = list(hits.values())[: self.fetch_top * 2]

        async def read(h: _Hit) -> Listing:
            listing = None
            try:
                # A page that's slow to answer becomes a link, not a hold-up for everyone else.
                listing = await asyncio.wait_for(fetch_listing(h.url, client, self.robots, timeout=2.5), 3.0)
            except (httpx.HTTPError, asyncio.TimeoutError):
                listing = None
            if listing is None:  # link-only result: we can show it, not price it
                listing = Listing(
                    source=urlparse(h.url).netloc.removeprefix("www."),
                    url=h.url,
                    title=h.title,
                    price_cents=None,
                    image_urls=[h.thumbnail] if h.thumbnail else [],
                    found_via="search:link",
                )
            domain = urlparse(h.url).netloc.removeprefix("www.")
            is_resale = self.group == "resale" or any(domain.endswith(d) for d in RESALE_DOMAINS)
            listing.seller_type = "resale" if is_resale else "retail"
            if not is_resale and listing.condition == "unknown":
                listing.condition = "new"
            listing.found_via = f"{self.name}:{listing.found_via}"
            return listing

        sem = asyncio.Semaphore(self.fetch_top)

        async def guarded(h: _Hit) -> Listing:
            async with sem:
                return await read(h)

        return list(await asyncio.gather(*(guarded(h) for h in top)))
