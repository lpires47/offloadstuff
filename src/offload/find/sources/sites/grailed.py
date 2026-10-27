"""Grailed: its website search runs on Algolia with a public search key, including a sold index
with sold price and date (the best pricing comps in fashion resale).

Spec from docs/research/fashion_sites.md §5 (secondary sources, 2026-05; confirm in DevTools).

TERMS: Grailed's ToS (effective 2026-09-03, §12) explicitly bans AI/LLM systems, AI assistants and
third-party tools without written consent. This connector is OFF unless named in
OFFLOAD_ENABLED_SITES; the right path is Grailed's written consent or a partnership.
"""

from __future__ import annotations

import json
import re
from urllib.parse import urlencode

import httpx

from ....find.models import Listing
from ..base import cents
from .base import Blocked, Query, SiteConnector, first

APP_ID = "MNRWEFSS2Q"
ACTIVE_INDEX = "Listing_production"
SOLD_INDEX = "Listing_sold_production"  # [U] community name; confirm


class Grailed(SiteConnector):
    name = "grailed"
    domain = "grailed.com"
    segments = ("menswear", "fashion", "luxury", "sneakers")
    supports_sold = True
    check_robots = False  # the Algolia host has no robots.txt; Grailed's own rules govern (see docstring)

    def __init__(self, api_key: str | None = None) -> None:
        self._key = api_key

    async def _key_from_site(self, client: httpx.AsyncClient) -> str:
        r = await client.get("https://www.grailed.com/", headers=self.headers(Accept="text/html"), timeout=5)
        m = re.search(r'"publicSearchKey"\s*:\s*"([^"]+)"', r.text) or re.search(r'algolia[^"]*Key"\s*:\s*"([^"]+)"', r.text)
        if not m:
            raise Blocked("couldn't find Grailed's public search key")
        return m.group(1)

    async def _search(self, q: Query, client: httpx.AsyncClient) -> list[Listing]:
        if not self._key:
            self._key = await self._key_from_site(client)
        params = {"query": q.text, "hitsPerPage": min(q.limit, 40), "page": 0}
        if q.min_price_cents or q.max_price_cents:
            nf = []
            if q.min_price_cents:
                nf.append(f"price_i>={q.min_price_cents // 100}")
            if q.max_price_cents:
                nf.append(f"price_i<={q.max_price_cents // 100}")
            params["numericFilters"] = json.dumps(nf)
        body = {"requests": [{"indexName": SOLD_INDEX if q.sold else ACTIVE_INDEX, "params": urlencode(params)}]}
        r = await self.post(
            client,
            f"https://{APP_ID}-dsn.algolia.net/1/indexes/*/queries",
            json=body,
            headers=self.headers(**{"x-algolia-application-id": APP_ID, "x-algolia-api-key": self._key,
                                    "Content-Type": "application/json"}),
        )
        hits = first(r.json(), "results.0.hits", default=[])
        return [self.parse(h) for h in hits if h.get("id")]

    @staticmethod
    def parse(h: dict) -> Listing:
        sold = bool(h.get("sold"))
        designers = h.get("designers") or []
        return Listing(
            source="grailed",
            url=f"https://www.grailed.com/listings/{h['id']}",
            title=h.get("title", ""),
            price_cents=cents(h.get("sold_price") if sold else h.get("price")),
            condition="new" if str(h.get("condition", "")).lower() in ("is_new", "new") else "used",
            image_urls=[u for u in [first(h, "cover_photo.url", "cover_photo.image_url")] if u],
            available=not sold,
            seller_type="resale",
            brand=(designers[0].get("name") if designers and isinstance(designers[0], dict) else None),
            status="sold" if sold else "active",
            sold_on=str(h.get("sold_at"))[:10] if sold and h.get("sold_at") else None,
            location=h.get("location"),
            attributes={k: v for k, v in {"size": h.get("size"), "color": h.get("color")}.items() if v},
        )
