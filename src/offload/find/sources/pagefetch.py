"""Read one public listing page the way a browser would, and pull price, condition and photos.

Most store and resale pages publish schema.org Product/Offer data (JSON-LD) for search engines; we
read that, falling back to Open Graph tags. One page per user-initiated lookup, robots.txt respected,
no logins, no CAPTCHA solving. If a site says no, we show the search result as a link instead.
"""

from __future__ import annotations

import json
import re
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx

from ..models import Listing
from .base import USER_AGENT, cents

_LD = re.compile(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', re.S | re.I)
_META = re.compile(r'<meta\s+[^>]*(?:property|name)=["\']([^"\']+)["\'][^>]*content=["\']([^"\']*)["\']', re.I)

CONDITION_MAP = {
    "newcondition": "new",
    "usedcondition": "used",
    "refurbishedcondition": "used",
    "damagedcondition": "used",
}


class Robots:
    """Per-host robots.txt cache. Unreachable robots.txt -> allowed (standard behavior)."""

    def __init__(self) -> None:
        self._cache: dict[str, RobotFileParser | None] = {}

    async def allowed(self, url: str, client: httpx.AsyncClient) -> bool:
        host = urlparse(url)
        root = f"{host.scheme}://{host.netloc}"
        if root not in self._cache:
            parser: RobotFileParser | None = None
            try:
                r = await client.get(f"{root}/robots.txt", headers={"User-Agent": USER_AGENT}, timeout=3)
                if r.status_code == 200:
                    parser = RobotFileParser()
                    parser.parse(r.text.splitlines())
                elif r.status_code in (401, 403):
                    parser = RobotFileParser()
                    parser.disallow_all = True
            except httpx.HTTPError:
                parser = None
            self._cache[root] = parser
        parser = self._cache[root]
        return True if parser is None else parser.can_fetch(USER_AGENT, url)


def _walk(node):
    """Yield every dict inside a JSON-LD blob (handles lists and @graph)."""
    if isinstance(node, dict):
        yield node
        for v in node.values():
            yield from _walk(v)
    elif isinstance(node, list):
        for v in node:
            yield from _walk(v)


def _is_type(d: dict, name: str) -> bool:
    t = d.get("@type")
    return t == name or (isinstance(t, list) and name in t)


def _images(value, base: str) -> list[str]:
    if value is None:
        return []
    items = value if isinstance(value, list) else [value]
    out = []
    for i in items:
        url = i.get("url") or i.get("contentUrl") if isinstance(i, dict) else i
        if isinstance(url, str):
            out.append(urljoin(base, url))
    return out


def parse_listing(html: str, url: str, source: str | None = None) -> Listing | None:
    """Best-effort Product/Offer extraction. Returns None if the page isn't a product page."""
    source = source or urlparse(url).netloc.removeprefix("www.")
    product = None
    for block in _LD.findall(html):
        try:
            data = json.loads(block.strip())
        except json.JSONDecodeError:
            continue
        for d in _walk(data):
            if _is_type(d, "Product") or _is_type(d, "IndividualProduct"):
                product = d
                break
        if product:
            break
    meta = {k.lower(): v for k, v in _META.findall(html)}

    if product is None:
        if meta.get("og:type", "").lower() not in ("product", "og:product", "product.item"):
            return None
        price = meta.get("product:price:amount") or meta.get("og:price:amount")
        return Listing(
            source=source,
            url=url,
            title=meta.get("og:title", ""),
            price_cents=cents(price),
            currency=meta.get("product:price:currency", "USD"),
            condition=CONDITION_MAP.get(meta.get("product:condition", "").lower() + "condition", "unknown"),  # type: ignore[arg-type]
            image_urls=[meta["og:image"]] if meta.get("og:image") else [],
            found_via="page:og",
        )

    offers = product.get("offers") or {}
    if isinstance(offers, list):
        offers = offers[0] if offers else {}
    price = offers.get("price") or offers.get("lowPrice")
    if price is None and isinstance(offers.get("priceSpecification"), dict):
        price = offers["priceSpecification"].get("price")
    availability = str(offers.get("availability", "")).lower()
    cond = str(offers.get("itemCondition") or product.get("itemCondition") or "").rsplit("/", 1)[-1].lower()
    brand = product.get("brand")
    if isinstance(brand, dict):
        brand = brand.get("name")
    gtin = next((product.get(k) for k in ("gtin13", "gtin12", "gtin14", "gtin8", "gtin") if product.get(k)), None)
    return Listing(
        source=source,
        url=url,
        title=str(product.get("name") or meta.get("og:title", "")),
        price_cents=cents(price),
        currency=str(offers.get("priceCurrency") or "USD"),
        condition=CONDITION_MAP.get(cond, "unknown"),  # type: ignore[arg-type]
        image_urls=_images(product.get("image"), url) or ([meta["og:image"]] if meta.get("og:image") else []),
        available=None if not availability else ("instock" in availability or "limitedavailability" in availability),
        gtin=str(gtin) if gtin else None,
        mpn=product.get("mpn") or product.get("sku"),
        brand=brand if isinstance(brand, str) else None,
        found_via="page:jsonld",
    )


async def fetch_listing(url: str, client: httpx.AsyncClient, robots: Robots, timeout: float = 4.0) -> Listing | None:
    if not await robots.allowed(url, client):
        return None
    r = await client.get(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html"}, timeout=timeout, follow_redirects=True)
    if r.status_code != 200 or "html" not in r.headers.get("content-type", "html"):
        return None
    return parse_listing(r.text, str(r.url))
