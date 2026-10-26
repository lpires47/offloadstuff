"""Independent vintage and resale shops on Shopify, searched live through each store's public
predictive-search endpoint (the one the store's own search box uses).

https://shopify.dev/docs/api/ajax/reference/predictive-search
"""

from __future__ import annotations

import asyncio

import httpx

from ..models import Listing
from .base import USER_AGENT, SearchPlan, cents


class ShopifyStores:
    name = "shopify"

    def __init__(self, per_store: int = 6, timeout: float = 3.0) -> None:
        self.per_store, self.timeout = per_store, timeout

    async def _store(self, domain: str, q: str, client: httpx.AsyncClient) -> list[Listing]:
        try:
            r = await client.get(
                f"https://{domain}/search/suggest.json",
                params={"q": q, "resources[type]": "product", "resources[limit]": self.per_store},
                headers={"User-Agent": USER_AGENT},
                timeout=self.timeout,
            )
            if r.status_code != 200:
                return []
            products = r.json().get("resources", {}).get("results", {}).get("products", [])
        except (httpx.HTTPError, ValueError):
            return []
        out = []
        for p in products:
            url = p.get("url", "")
            out.append(
                Listing(
                    source=f"shopify:{domain}",
                    url=url if url.startswith("http") else f"https://{domain}{url.split('?')[0]}",
                    title=p.get("title", ""),
                    price_cents=cents(p.get("price")),
                    condition="unknown",
                    image_urls=[p["image"]] if p.get("image") else [],
                    available=p.get("available"),
                    seller_type="resale",
                    brand=p.get("vendor"),
                    found_via=f"shopify:{q}",
                )
            )
        return out

    async def search(self, plan: SearchPlan, client: httpx.AsyncClient) -> list[Listing]:
        if not plan.shopify_stores:
            return []
        q = (plan.exact_queries or plan.similar_queries or [plan.profile.subcategory])[0]
        batches = await asyncio.gather(*(self._store(d, q, client) for d in plan.shopify_stores))
        return [x for b in batches for x in b]
