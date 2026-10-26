"""Etsy Open API v3: active listings by keyword (vintage and handmade).

https://developers.etsy.com/documentation/reference#operation/findAllListingsActive
"""

from __future__ import annotations

import httpx

from ..models import Listing
from .base import SearchPlan


class EtsySource:
    name = "etsy"
    URL = "https://openapi.etsy.com/v3/application/listings/active"

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    async def search(self, plan: SearchPlan, client: httpx.AsyncClient) -> list[Listing]:
        out: list[Listing] = []
        for q in (plan.exact_queries[:1] + plan.similar_queries[:1]) or [plan.profile.subcategory]:
            r = await client.get(
                self.URL,
                params={"keywords": q, "limit": min(plan.per_source_limit, 50), "includes": "Images"},
                headers={"x-api-key": self.api_key},
            )
            r.raise_for_status()
            for x in r.json().get("results", []):
                price = x.get("price") or {}
                amount = price.get("amount")
                divisor = price.get("divisor") or 100
                when = str(x.get("when_made", ""))
                vintage = when.startswith("before_") or (when[:2].isdigit() and when < "2006")
                images = [i.get("url_570xN") for i in x.get("images", []) if i.get("url_570xN")]
                out.append(
                    Listing(
                        source="etsy",
                        url=x.get("url", ""),
                        title=x.get("title", ""),
                        price_cents=int(amount * 100 / divisor) if amount is not None else None,
                        currency=price.get("currency_code", "USD"),
                        condition="used" if vintage else "unknown",
                        image_urls=images,
                        available=x.get("state") == "active",
                        seller_type="resale" if vintage else "unknown",
                        found_via=f"etsy:{q}",
                    )
                )
        return out
