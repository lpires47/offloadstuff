"""eBay Browse API: keyword search split by new vs used, plus search by image.

Uses an application token (client credentials), so no user login. Docs:
https://developer.ebay.com/api-docs/buy/browse/resources/item_summary/methods/search
"""

from __future__ import annotations

import base64
import time

import httpx

from ..models import Listing
from .base import SearchPlan, cents

API = "https://api.ebay.com"
SCOPE = "https://api.ebay.com/oauth/api_scope"
NEW_IDS = "1000|1500"  # New, New other
USED_IDS = "2750|3000|4000|5000|6000"  # Like new (cards/apparel), Used, Very good, Good, Acceptable


class EbayBrowse:
    name = "ebay"

    def __init__(self, app_id: str, cert_id: str, marketplace: str = "EBAY_US") -> None:
        self.app_id, self.cert_id, self.marketplace = app_id, cert_id, marketplace
        self._token: str | None = None
        self._token_expires = 0.0

    async def _auth(self, client: httpx.AsyncClient) -> str:
        if self._token and time.time() < self._token_expires - 60:
            return self._token
        basic = base64.b64encode(f"{self.app_id}:{self.cert_id}".encode()).decode()
        r = await client.post(
            f"{API}/identity/v1/oauth2/token",
            headers={"Authorization": f"Basic {basic}", "Content-Type": "application/x-www-form-urlencoded"},
            data={"grant_type": "client_credentials", "scope": SCOPE},
        )
        r.raise_for_status()
        body = r.json()
        self._token, self._token_expires = body["access_token"], time.time() + int(body.get("expires_in", 7200))
        return self._token

    def _headers(self, token: str) -> dict:
        return {"Authorization": f"Bearer {token}", "X-EBAY-C-MARKETPLACE-ID": self.marketplace}

    async def search(self, plan: SearchPlan, client: httpx.AsyncClient) -> list[Listing]:
        token = await self._auth(client)
        out: list[Listing] = []
        limit = min(plan.per_source_limit, 50)
        # Exact queries, split so new and used both show up even when one dominates.
        for q in plan.exact_queries[:2]:
            for cond, ids in (("new", NEW_IDS), ("used", USED_IDS)):
                r = await client.get(
                    f"{API}/buy/browse/v1/item_summary/search",
                    params={"q": q, "limit": limit, "filter": f"conditionIds:{{{ids}}}"},
                    headers=self._headers(token),
                )
                r.raise_for_status()
                out += [self._listing(s, f"ebay:{cond}:{q}") for s in r.json().get("itemSummaries", [])]
        for q in plan.similar_queries[:1]:
            r = await client.get(
                f"{API}/buy/browse/v1/item_summary/search",
                params={"q": q, "limit": limit},
                headers=self._headers(token),
            )
            r.raise_for_status()
            out += [self._listing(s, f"ebay:similar:{q}") for s in r.json().get("itemSummaries", [])]
        if plan.photo is not None:
            out += await self.search_by_image(plan.photo, client, limit)
        return out

    async def search_by_image(self, photo, client: httpx.AsyncClient, limit: int = 50) -> list[Listing]:
        """Needs no identification, so the engine fires it the moment the photo arrives."""
        token = await self._auth(client)
        img = base64.b64encode(photo.jpeg_bytes(quality=85)).decode()
        r = await client.post(
            f"{API}/buy/browse/v1/item_summary/search_by_image",
            params={"limit": limit},
            json={"image": img},
            headers={**self._headers(token), "Content-Type": "application/json"},
        )
        r.raise_for_status()
        return [self._listing(s, "ebay:image") for s in r.json().get("itemSummaries", [])]

    @staticmethod
    def _listing(s: dict, via: str) -> Listing:
        cond_id = str(s.get("conditionId", ""))
        condition = "new" if cond_id in NEW_IDS.split("|") else "used" if cond_id else "unknown"
        images = [s.get("image", {}).get("imageUrl")] + [i.get("imageUrl") for i in s.get("additionalImages", [])]
        ship = (s.get("shippingOptions") or [{}])[0].get("shippingCost", {}).get("value")
        loc = s.get("itemLocation", {})
        return Listing(
            source="ebay",
            url=s.get("itemWebUrl", ""),
            title=s.get("title", ""),
            price_cents=cents(s.get("price", {}).get("value")),
            currency=s.get("price", {}).get("currency", "USD"),
            condition=condition,  # type: ignore[arg-type]
            image_urls=[u for u in images if u],
            available=True,
            seller_type="resale" if condition == "used" else "unknown",
            location=", ".join(x for x in (loc.get("city"), loc.get("stateOrProvince"), loc.get("country")) if x) or None,
            shipping_cents=cents(ship),
            found_via=via,
        )
