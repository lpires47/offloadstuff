"""Chairish: its search pages embed the result set as a JS object, PRODUCT_ID_TO_PRODUCT_JSON_MAP
(48 items per page). Spec: docs/research/furniture_sites.md §2.2 (secondary + live fetch, 2026-10).

TERMS: Chairish's terms couldn't be retrieved; treat automated access as restricted until reviewed.
OFF unless named in OFFLOAD_ENABLED_SITES.
"""

from __future__ import annotations

import json
import re

import httpx

from ....find.models import Listing
from ..base import cents
from .base import Query, SiteConnector, first

_MAP = re.compile(r"PRODUCT_ID_TO_PRODUCT_JSON_MAP\s*=\s*(\{.*?\})\s*;\s*(?:\n|</script>|var |window\.)", re.S)


class Chairish(SiteConnector):
    name = "chairish"
    domain = "chairish.com"
    segments = ("furniture", "decor")

    async def _search(self, q: Query, client: httpx.AsyncClient) -> list[Listing]:
        if q.sold:
            return []
        params = {"q": q.text}
        if q.min_price_cents or q.max_price_cents:
            params["price"] = f"{(q.min_price_cents or 0) // 100 or ''}-{(q.max_price_cents or 0) // 100 or ''}"
        r = await self.get(client, "https://www.chairish.com/search", params=params,
                           headers=self.headers(Accept="text/html"))
        return self.parse_page(r.text)

    @staticmethod
    def parse_page(html: str) -> list[Listing]:
        m = _MAP.search(html)
        if not m:
            return []
        try:
            products = json.loads(m.group(1))
        except json.JSONDecodeError:
            return []
        out = []
        for pid, p in products.items():
            url = first(p, "url", "absolute_url", default=f"/product/{pid}")
            if url.startswith("/"):
                url = "https://www.chairish.com" + url
            dims = {k: first(p, k) for k in ("width", "depth", "height")}
            out.append(Listing(
                source="chairish",
                url=url,
                title=str(first(p, "title", "name", default="")),
                price_cents=cents(first(p, "price", "sale_price", "list_price")),
                condition="used" if first(p, "item_type", default="V") == "V" else "unknown",
                image_urls=[u for u in [first(p, "image_url", "image", "primary_image.url")] if u],
                available=not bool(first(p, "is_sold", default=False)),
                seller_type="resale",
                brand=first(p, "designer", "maker", "brand"),
                attributes={k: str(v) for k, v in {**dims, "period": first(p, "period"),
                                                   "materials": first(p, "materials")}.items() if v},
            ))
        return out
