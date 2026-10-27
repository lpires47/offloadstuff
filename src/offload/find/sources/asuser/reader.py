"""Search a site as the user: their own logged-in browser session opens the site's own search page,
and we read the results that page loads, the way they would see them.

This is the "acting as the real user" path the founders chose: each user connects their own accounts
and consents per site; we run one search per site per request, at a person's pace, in their session.
What we do not do: solve CAPTCHAs, spoof browser fingerprints, rotate proxies, or use anyone else's
account. If a site challenges or asks for sign-in, we stop and ask the user to step in through the
live view. Purchases and messages always need the user's tap (see posting/browser/tasks.py).
"""

from __future__ import annotations

import asyncio
import json
import re
import time
from dataclasses import dataclass, field
from typing import Protocol
from urllib.parse import urljoin, urlparse

from ...models import Listing
from ..base import SearchPlan, cents
from ..pagefetch import parse_listing
from .recipes import Recipe


class NeedsUser(Exception):
    """The site wants the user: sign in, or a human check. Shown as 'Connect / continue in live view'."""


class BrowserProvider(Protocol):
    async def context(self, user_id: str, site: str): ...  # -> playwright.async_api.BrowserContext
    async def save(self, user_id: str, site: str, context) -> None: ...


# ---------- finding listings in whatever the page loads ----------

TITLE_KEYS = ("title", "name", "marketplace_listing_title", "item_name", "product_name", "productName")
PRICE_KEYS = ("price", "price_amount", "listing_price", "sold_price", "salePrice", "current_price", "priceResult",
              "amount", "price_i", "formatted_price")
ID_KEYS = ("id", "listing_id", "itemId", "item_id", "objectID", "slug")
URL_KEYS = ("url", "link", "itemUrl", "item_url", "permalink", "story_url", "lotUrl", "absolute_url")
IMG_KEYS = ("image", "image_url", "imageUrl", "cover_shot", "cover_photo", "primary_listing_photo", "photo",
            "photos", "pictures", "images", "thumbnail")


def _price(v) -> int | None:
    if isinstance(v, dict):
        for k in ("amount", "val", "value", "formatted_amount", "amount_with_offset_in_currency"):
            if k in v:
                got = _price(v[k])
                if got:
                    return got
        return None
    if isinstance(v, (int, float)):
        return int(round(v * 100)) if v < 1_000_000 else None
    if isinstance(v, str):
        m = re.search(r"\d[\d,]*(\.\d{1,2})?", v)
        return cents(m.group().replace(",", "")) if m else None
    return None


def _img(v) -> str | None:
    if isinstance(v, str) and v.startswith("http"):
        return v
    if isinstance(v, dict):
        for k in ("uri", "url", "src", "url_small", "image_url", "thumbnail"):
            got = _img(v.get(k))
            if got:
                return got
        for vv in v.values():
            if isinstance(vv, dict):
                got = _img(vv)
                if got:
                    return got
    if isinstance(v, list) and v:
        return _img(v[0])
    return None


def walk_listings(node, recipe: Recipe, out: list[Listing], depth: int = 0) -> None:
    """Find listing-shaped objects (a title, a price, and an id or link) anywhere in a JSON blob."""
    if depth > 14:
        return
    if isinstance(node, dict):
        title = next((node[k] for k in TITLE_KEYS if isinstance(node.get(k), str) and node[k].strip()), None)
        price_key = next((k for k in PRICE_KEYS if k in node and node[k] not in (None, "", 0)), None)
        ident = next((node[k] for k in ID_KEYS if node.get(k) not in (None, "")), None)
        link = next((node[k] for k in URL_KEYS if isinstance(node.get(k), str)), None)
        if title and price_key and (ident is not None or link):
            url = urljoin(f"https://www.{recipe.domain}/", link) if link else (
                recipe.id_url.format(id=ident) if recipe.id_url else "")
            if url:
                raw = node.get("status")
                if isinstance(node.get("inventory"), dict):
                    raw = node["inventory"].get("status", raw)
                status = str(raw or "").lower()
                sold = bool(node.get("sold") or node.get("isSold") or node.get("is_sold")) or status in ("sold", "sold_out")
                img = next((_img(node[k]) for k in IMG_KEYS if k in node and _img(node[k])), None)
                loc = node.get("location")
                if isinstance(loc, dict):
                    geo = loc.get("reverse_geocode") or loc
                    loc = ", ".join(str(geo[k]) for k in ("city", "state") if geo.get(k)) or None
                out.append(Listing(
                    source=recipe.name,
                    url=url,
                    title=title.strip(),
                    price_cents=_price(node[price_key]),
                    image_urls=[img] if img else [],
                    seller_type="resale",
                    status="sold" if sold else "active",
                    location=loc if isinstance(loc, str) else None,
                    sold_price_is_list=recipe.sold_price_is_list and sold,
                    found_via=f"asuser:{recipe.name}:json",
                ))
                return
        for v in node.values():
            walk_listings(v, recipe, out, depth + 1)
    elif isinstance(node, list):
        for v in node:
            walk_listings(v, recipe, out, depth + 1)


# Runs inside the page: result cards are links to listings with a price nearby.
CARDS_JS = r"""
(pattern) => {
  const re = new RegExp(pattern);
  const seen = new Set(); const out = [];
  for (const a of document.querySelectorAll('a[href]')) {
    let u; try { u = new URL(a.href, location.href); } catch { continue; }
    if (!re.test(u.pathname) || seen.has(u.pathname)) continue;
    let card = a, price = null;
    for (let i = 0; i < 5 && card; i++) {
      const m = (card.innerText || '').match(/\$\s?\d[\d,]*(\.\d{2})?/);
      if (m) { price = m[0]; break; }
      card = card.parentElement;
    }
    const img = (card || a).querySelector('img');
    const title = (a.getAttribute('aria-label') || (img && img.alt) || a.innerText || '').trim().split('\n')[0];  // full label: parsed in Python
    seen.add(u.pathname);
    out.push({url: u.href.split('?')[0], title, price, img: img ? (img.currentSrc || img.src) : null,
              sold: /\bsold\b/i.test((card || a).innerText || '')});
    if (out.length >= 60) break;
  }
  return out;
}
"""

CHALLENGE_JS = r"""
() => {
  const t = (document.title + ' ' + (document.body ? document.body.innerText.slice(0, 2000) : '')).toLowerCase();
  const login = /log in to continue|sign in to continue|you must log in|log into facebook|create new account/.test(t);
  const human = /verify you are human|are you a robot|unusual traffic|press & hold|captcha/.test(t)
    || !!document.querySelector('iframe[src*="captcha"], iframe[src*="challenge"], #px-captcha');
  return {login, human};
}
"""


@dataclass
class PacePolicy:
    """Human pace: one search page per site at a time, a few seconds apart, a handful of tabs."""

    min_interval_s: float = 3.0
    max_tabs: int = 6
    _last: dict[tuple[str, str], float] = field(default_factory=dict)

    async def wait(self, user_id: str, site: str) -> None:
        key = (user_id, site)
        delay = self.min_interval_s - (time.time() - self._last.get(key, 0))
        if delay > 0:
            await asyncio.sleep(delay)
        self._last[key] = time.time()


async def read_page(context, recipe: Recipe, url: str, *, timeout_s: float = 8.0) -> list[Listing]:
    """Open the site's own search page in the user's session and collect the listings it shows."""
    captured: list = []

    async def on_response(resp):
        if recipe.xhr and any(p in resp.url for p in recipe.xhr):
            try:
                if "json" in (resp.headers.get("content-type") or "") or resp.url.endswith(".json"):
                    captured.append(await resp.json())
                else:
                    text = await resp.text()
                    for line in text.splitlines():  # GraphQL streams several JSON objects per response
                        line = line.strip()
                        if line.startswith("{"):
                            try:
                                captured.append(json.loads(line))
                            except json.JSONDecodeError:
                                pass
            except Exception:  # noqa: BLE001 - a body we can't read is just skipped
                pass

    page = await context.new_page()
    page.on("response", on_response)

    async def light(route):  # skip heavy media; we read data, the user isn't watching this tab
        if route.request.resource_type in ("image", "media", "font"):
            await route.abort()
        else:
            await route.fallback()  # let any context-level handler (or the network) take it

    await page.route("**/*", light)
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=timeout_s * 1000)
        try:
            await page.wait_for_load_state("networkidle", timeout=min(4000, timeout_s * 500))
        except Exception:  # noqa: BLE001 - busy pages never go idle; we read what's there
            pass
        state = await page.evaluate(CHALLENGE_JS)
        if state["human"]:
            raise NeedsUser(f"{recipe.name} wants a human check: continue in the live view")
        listings: list[Listing] = []
        for blob in captured:
            walk_listings(blob, recipe, listings)
        for expr in recipe.embedded:
            try:
                data = await page.evaluate(f"() => {{ const v = {expr}; return typeof v === 'string' ? JSON.parse(v) : v; }}")
            except Exception:  # noqa: BLE001
                data = None
            if data:
                walk_listings(data, recipe, listings)
        if not listings:
            for block in await page.eval_on_selector_all(
                'script[type="application/ld+json"]', "els => els.map(e => e.textContent)"
            ):
                got = parse_listing(f'<script type="application/ld+json">{block}</script>', url, recipe.name)
                if got:
                    listings.append(got)
        if not listings:
            for c in await page.evaluate(CARDS_JS, recipe.item_path):
                listings.append(card_listing(recipe, c))
        if not listings and state["login"] and recipe.login:
            raise NeedsUser(f"connect your {recipe.name} account to search it")
        return listings
    finally:
        await page.close()


# Card labels like Facebook's: "Title, $150, reduced from $195, San Francisco, CA, listing 1606..."
_LABEL = re.compile(
    r"^(?P<title>.+?), (?P<price>\$[\d,]+(?:\.\d{2})?)(?:, reduced from (?P<was>\$[\d,]+(?:\.\d{2})?))?"
    r"(?:, (?P<loc>[^,]*(?:, [A-Z]{2})?))?, listing \d+$"
)


def card_listing(recipe: Recipe, c: dict) -> Listing:
    title, price, loc, attrs = c["title"], _price(c["price"]), None, {}
    m = _LABEL.match(title or "")
    if m:
        title, price = m["title"], _price(m["price"])
        loc = (m["loc"] or "").strip(", ") or None
        if m["was"]:
            attrs["was_price"] = m["was"]
    return Listing(
        source=recipe.name, url=c["url"], title=title, price_cents=price,
        image_urls=[c["img"]] if c.get("img") else [], seller_type="resale", location=loc,
        status="sold" if c.get("sold") else "active", attributes=attrs,
        found_via=f"asuser:{recipe.name}:cards",
    )


class AsUserSource:
    """One site, searched in one user's session. Implements the engine's Source protocol."""

    def __init__(self, recipe: Recipe, user_id: str, provider: BrowserProvider, pace: PacePolicy,
                 city: str = "sanfrancisco") -> None:
        self.recipe, self.user_id, self.provider, self.pace, self.city = recipe, user_id, provider, pace, city
        self.name = f"asuser:{recipe.name}"

    async def search(self, plan: SearchPlan, client=None) -> list[Listing]:
        q = (plan.exact_queries or plan.similar_queries or [plan.profile.subcategory])[0]
        await self.pace.wait(self.user_id, self.recipe.name)
        context = await self.provider.context(self.user_id, self.recipe.name)
        urls = [(self.recipe.search_url(q, self.city), False)]
        sold_url = self.recipe.sold_url(q, self.city)
        if sold_url and plan.exact_queries:
            urls.append((sold_url, True))
        out: list[Listing] = []
        pages = await asyncio.gather(*(read_page(context, self.recipe, url) for url, _ in urls), return_exceptions=True)
        for (url, sold), got in zip(urls, pages):
            if isinstance(got, Exception):
                if not sold:  # the main search failing is an error; a failed sold page just means fewer comps
                    raise got
                continue
            for x in got:
                if sold:
                    x.status = "sold"
                    x.sold_price_is_list = self.recipe.sold_price_is_list
            out += got
        await self.provider.save(self.user_id, self.recipe.name, context)
        seen, unique = set(), []
        for x in out:
            key = urlparse(x.url).path.rstrip("/")
            if key not in seen:
                seen.add(key)
                unique.append(x)
        return unique
