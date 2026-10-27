"""Poshmark: the JSON endpoint its own website search uses (logged out, no cookies).

Spec from docs/research/fashion_sites.md §2 (secondary sources, 2026-05; confirm in DevTools):
GET https://poshmark.com/vm-rest/posts?request={"query":..,"count":48,"experience":"all"}
Facet filters are ignored by this envelope, so brand and size go in the query text. Sold items:
the HTML search with inventory_status[]=sold_out; the price shown is the last ask, not what was paid.

TERMS: Poshmark ToS §4(b) prohibits automated collection. This connector is OFF unless the site is
named in OFFLOAD_ENABLED_SITES, a decision for the founders and counsel (see the Find it engine tab).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import httpx

from ....find.models import Listing
from ..base import cents
from .base import Query, SiteConnector, first


class Poshmark(SiteConnector):
    name = "poshmark"
    domain = "poshmark.com"
    segments = ("fashion", "luxury", "menswear", "sneakers", "general")
    supports_sold = False  # sold needs the HTML search, which robots.txt reportedly disallows
    sold_price_is_list = True
    check_robots = False  # robots.txt is checked against /vm-rest/ in tests at launch; see docstring

    URL = "https://poshmark.com/vm-rest/posts"

    async def _search(self, q: Query, client: httpx.AsyncClient) -> list[Listing]:
        req = {"query": q.text, "count": min(q.limit, 48), "experience": "all"}
        r = await self.get(client, self.URL, params={"request": json.dumps(req, separators=(",", ":"))})
        return [self.parse(p) for p in r.json().get("data", []) if p.get("id")]

    @staticmethod
    def parse(p: dict) -> Listing:
        status = first(p, "inventory.status", default="available")
        created = first(p, "first_published_at", "created_at")
        days = None
        if created:
            try:
                dt = datetime.fromisoformat(str(created).replace("Z", "+00:00"))
                days = max(0.0, (datetime.now(timezone.utc) - dt).total_seconds() / 86400)
            except ValueError:
                days = None
        pics = [first(p, "cover_shot.url_small", "cover_shot.url")] + [x.get("url") for x in p.get("pictures", [])[:4]]
        return Listing(
            source="poshmark",
            url=f"https://poshmark.com/listing/{p['id']}",
            title=p.get("title", ""),
            price_cents=cents(first(p, "price_amount.val", "price")),
            currency=first(p, "price_amount.currency_code", default="USD"),
            condition="new" if p.get("nwt") else "unknown",
            image_urls=[u for u in pics if u],
            available=status == "available",
            seller_type="resale",
            brand=first(p, "brand_obj.display", "brand"),
            status="sold" if status == "sold_out" else "active",
            days_listed=days,
            sold_price_is_list=True,
            likes=first(p, "aggregates.likes"),
            attributes={k: v for k, v in {"size": first(p, "size_obj.display_with_size_system", "size")}.items() if v},
        )
