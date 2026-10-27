"""AptDeco: a Next.js site; catalog pages carry results in __NEXT_DATA__ (props.pageProps).
Spec: docs/research/furniture_sites.md §2.4. The field layout inside pageProps is unconfirmed [U]:
the parser walks it for product-shaped objects. Confirm on first live run.

TERMS not retrieved; affiliate program on Awin (merchant 93197) is the clean route. OFF unless
named in OFFLOAD_ENABLED_SITES.
"""

from __future__ import annotations

import json
import re

import httpx

from ....find.models import Listing
from ..base import cents
from .base import Query, SiteConnector, first

_NEXT = re.compile(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S)


def _products(node, out: list[dict]) -> None:
    if isinstance(node, dict):
        if ("price" in node or "salePrice" in node) and ("slug" in node or "url" in node) and ("title" in node or "name" in node):
            out.append(node)
            return
        for v in node.values():
            _products(v, out)
    elif isinstance(node, list):
        for v in node:
            _products(v, out)


class AptDeco(SiteConnector):
    name = "aptdeco"
    domain = "aptdeco.com"
    segments = ("furniture", "decor")

    async def _search(self, q: Query, client: httpx.AsyncClient) -> list[Listing]:
        if q.sold:
            return []
        r = await self.get(client, "https://www.aptdeco.com/catalog/furniture", params={"search": q.text},
                           headers=self.headers(Accept="text/html"))
        return self.parse_page(r.text)

    @staticmethod
    def parse_page(html: str) -> list[Listing]:
        m = _NEXT.search(html)
        if not m:
            return []
        found: list[dict] = []
        _products(json.loads(m.group(1)).get("props", {}).get("pageProps", {}), found)
        out = []
        for p in found:
            slug = first(p, "url", "slug", default="")
            url = slug if slug.startswith("http") else f"https://www.aptdeco.com/{slug.lstrip('/')}"
            out.append(Listing(
                source="aptdeco",
                url=url,
                title=str(first(p, "title", "name", default="")),
                price_cents=cents(first(p, "salePrice", "price")),
                condition="used",
                image_urls=[u for u in [first(p, "image", "imageUrl", "images.0.url", "images.0")] if isinstance(u, str)],
                available=True,
                seller_type="resale",
                brand=first(p, "brand", "brandName"),
                location=first(p, "city", "location"),
                attributes={k: str(v) for k, v in {"retail": first(p, "retailPrice", "estimatedRetail"),
                                                   "condition": first(p, "condition")}.items() if v},
            ))
        return out
