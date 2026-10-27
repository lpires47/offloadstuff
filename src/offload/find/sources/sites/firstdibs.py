"""1stDibs through its official MCP server (search_items, item_details, read_taxonomy).

This is 1stDibs' own published agent interface, the sanctioned route, so it is ON by default.
Output fields aren't documented [U]: the parser looks for the usual keys and keeps what it finds.
Confirm on first live run (offload sites --check) and pin the fields.
"""

from __future__ import annotations

import httpx

from ....find.models import Listing
from ..base import cents
from .base import Blocked, Query, SiteConnector, first
from .mcp import MCPClient, MCPError

ENDPOINT = "https://www.1stdibs.com/soa/mcp/"


def _items(payload) -> list[dict]:
    """Find the list of item dicts in whatever shape the tool returns."""
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if isinstance(payload, dict):
        for key in ("items", "results", "data", "edges", "hits"):
            if isinstance(payload.get(key), list):
                return [x.get("node", x) if isinstance(x, dict) else x for x in payload[key] if isinstance(x, dict)]
    return []


class FirstDibs(SiteConnector):
    name = "1stdibs"
    domain = "1stdibs.com"
    segments = ("furniture", "decor", "luxury", "general")
    official = True  # on by default
    check_robots = False

    def __init__(self) -> None:
        self.client = MCPClient(ENDPOINT, transport="curl")  # their firewall stalls Python TLS clients

    async def _search(self, q: Query, client: httpx.AsyncClient) -> list[Listing]:
        if q.sold:
            return []
        args: dict = {"query": q.text}
        if q.min_price_cents or q.max_price_cents:
            lo = q.min_price_cents // 100 if q.min_price_cents else ""
            hi = q.max_price_cents // 100 if q.max_price_cents else ""
            args["filters"] = f"price={lo}-{hi}"
        try:
            payload = await self.client.call(client, "search_items", args)
        except MCPError as e:
            raise Blocked(str(e)) from e
        return [self.parse(x) for x in _items(payload)[: q.limit]]

    @staticmethod
    def parse(x: dict) -> Listing:
        url = first(x, "productDetailUrl", "url", "link", "itemUrl", default="")
        url = url.split("?")[0] if "utm_" in url else url
        if url and url.startswith("/"):
            url = "https://www.1stdibs.com" + url
        price = first(x, "price.amount", "price.value", "price", "convertedAmounts.USD")
        images = first(x, "images", "imageUrls", "photos", default=[])
        if isinstance(images, str):
            images = [images]
        primary = first(x, "primaryImage")
        extra = first(x, "additionalImages", default=[])
        if isinstance(extra, str):
            extra = [e.strip(" '\"") for e in extra.strip("[]").split(",") if e.strip()]
        images = ([primary] if primary else []) + list(extra) + list(images)
        images = [i.get("url") if isinstance(i, dict) else i for i in images][:4]
        sold = bool(first(x, "isSold", default=False)) or first(x, "available", default=True) is False
        attrs = {k: str(v) for k, v in {
            "designer": first(x, "creator.name", "creator", "designer"),
            "period": first(x, "period", "productionDate"),
            "materials": first(x, "materials"),
            "dimensions": first(x, "dimensions"),
            "origin": first(x, "origin", "placeOfOrigin"),
        }.items() if v}
        return Listing(
            source="1stdibs",
            url=url,
            title=str(first(x, "title", "name", default="")),
            price_cents=cents(price) if not isinstance(price, dict) else None,
            condition="used" if str(first(x, "condition", default="")).lower() not in ("new", "") else "unknown",
            image_urls=[i for i in images if i],
            available=not sold,
            seller_type="resale",
            brand=attrs.get("designer"),
            status="sold" if sold else "active",
            location=first(x, "dealer.location", "location"),
            attributes=attrs,
        )
