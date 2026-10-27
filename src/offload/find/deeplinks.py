"""Searches we hand to the shopper instead of running ourselves.

Facebook Marketplace has no read API for companies (the Partnership Program is inbound-only), and
Meta's terms bar automated collection; a logged-in agent or our own scraping is off the table (see
docs/research/fb_marketplace.md). So we open the shopper's own Marketplace search, pre-filled with
our query, in their app or browser: they see live local results, we never touch Meta's data.
Parameter names other than `query` come from scraper docs and are unverified [U]: test them.
"""

from __future__ import annotations

from urllib.parse import quote, urlencode


def facebook_marketplace(query: str, city_slug: str = "sanfrancisco", *, min_price: int | None = None,
                         max_price: int | None = None, used_only: bool = False) -> str:
    params: dict[str, str] = {"query": query}
    if min_price:
        params["minPrice"] = str(min_price // 100)
    if max_price:
        params["maxPrice"] = str(max_price // 100)
    if used_only:
        params["itemCondition"] = "used_like_new,used_good,used_fair"
    return f"https://www.facebook.com/marketplace/{quote(city_slug)}/search/?{urlencode(params)}"


def handoff_links(exact_queries: list[str], similar_queries: list[str], segment: str, city_slug: str) -> list[dict]:
    q = (exact_queries or similar_queries or [""])[0]
    if not q:
        return []
    links = [{"site": "Facebook Marketplace", "url": facebook_marketplace(q, city_slug),
              "label": f"See “{q}” near you on Facebook Marketplace"}]
    if segment in ("furniture", "decor"):
        sim = (similar_queries or [q])[0]
        if sim != q:
            links.append({"site": "Facebook Marketplace", "url": facebook_marketplace(sim, city_slug),
                          "label": f"Similar pieces near you: “{sim}”"})
    return links
