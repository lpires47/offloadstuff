"""Per-site recipes for searching as the user, in the user's own logged-in browser session.

Each recipe says where the site's own search page is and what a listing link looks like. The reader
(reader.py) opens that page in the user's session and collects listings from, in order:
  1. the JSON the page itself fetches while loading results (captured, not re-requested),
  2. data the page embeds (__NEXT_DATA__, JSON-LD, known globals),
  3. the rendered result cards (links matching `item_path` plus the price near them).
Field names inside each site's JSON are not hard-coded: the walker finds listing-shaped objects.
Site specifics from docs/research/*_sites.md; all of it needs confirming on first live run.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import quote_plus


@dataclass(frozen=True)
class Recipe:
    name: str
    domain: str
    search: str  # URL template with {q} (and {city} where local)
    item_path: str  # regex for a listing's URL path
    segments: tuple[str, ...]
    sold: str | None = None  # template for sold/completed search, when the site has one
    xhr: tuple[str, ...] = ()  # substrings of the site's own result requests to capture
    embedded: tuple[str, ...] = ()  # JS expressions returning embedded result data
    id_url: str | None = None  # listing URL from an id found in the site's JSON
    login: bool = False  # results need (or are much better) logged in
    sold_price_is_list: bool = False
    notes: str = ""

    def search_url(self, q: str, city: str = "sanfrancisco") -> str:
        return self.search.format(q=quote_plus(q), city=city)

    def sold_url(self, q: str, city: str = "sanfrancisco") -> str | None:
        return self.sold.format(q=quote_plus(q), city=city) if self.sold else None


FASHION = ("fashion", "menswear", "luxury", "sneakers", "general")
HOME = ("furniture", "decor", "general")

RECIPES: dict[str, Recipe] = {r.name: r for r in [
    Recipe("facebook", "facebook.com", "https://www.facebook.com/marketplace/{city}/search/?query={q}",
           r"/marketplace/item/\d+", FASHION + HOME, xhr=("/api/graphql",), login=True,
           id_url="https://www.facebook.com/marketplace/item/{id}/",
           notes="local pickup and shipped; results arrive through the page's own GraphQL calls"),
    Recipe("poshmark", "poshmark.com", "https://poshmark.com/search?query={q}&type=listings",
           r"/listing/[^/?#]+", FASHION, sold="https://poshmark.com/search?query={q}&type=listings&availability=sold_out",
           xhr=("/vm-rest/",), sold_price_is_list=True, id_url="https://poshmark.com/listing/{id}"),
    Recipe("mercari", "mercari.com", "https://www.mercari.com/search/?keyword={q}",
           r"/us/item/m\d+", FASHION + HOME, sold="https://www.mercari.com/search/?keyword={q}&itemStatuses=2",
           xhr=("/v1/api/search", "/v1/api"), id_url="https://www.mercari.com/us/item/{id}/", notes="search API needs the browser's own token: fine in a real session"),
    Recipe("depop", "depop.com", "https://www.depop.com/us/search/?q={q}", r"/products/[^/?#]+",
           FASHION, xhr=("/api/v", "search/products")),
    Recipe("grailed", "grailed.com", "https://www.grailed.com/shop?query={q}", r"/listings/\d+",
           ("menswear", "fashion", "luxury", "sneakers"), sold="https://www.grailed.com/sold?query={q}",
           xhr=("algolia.net",), id_url="https://www.grailed.com/listings/{id}"),
    Recipe("vinted", "vinted.com", "https://www.vinted.com/catalog?search_text={q}", r"/items/\d+",
           FASHION, xhr=("/api/v2/catalog/items",), id_url="https://www.vinted.com/items/{id}"),
    Recipe("therealreal", "therealreal.com", "https://www.therealreal.com/search?keywords={q}", r"/products/[^?#]+",
           ("luxury", "fashion"), xhr=("graphql",), embedded=("window.__NEXT_DATA__",)),
    Recipe("vestiaire", "vestiairecollective.com", "https://us.vestiairecollective.com/search/?q={q}",
           r"/[a-z0-9-]+-\d+\.shtml", ("luxury", "fashion"), xhr=("/v1/product/search", "search.vestiairecollective")),
    Recipe("thredup", "thredup.com", "https://www.thredup.com/search?search_text={q}", r"/product/[^?#]+",
           ("fashion",), xhr=("graphql",)),
    Recipe("stockx", "stockx.com", "https://stockx.com/search?s={q}", r"^/[a-z0-9-]{8,}$", ("sneakers", "luxury"),
           xhr=("/api/p/e", "graphql"), embedded=("window.__NEXT_DATA__",)),
    Recipe("goat", "goat.com", "https://www.goat.com/search?query={q}", r"/sneakers/[^?#]+|/apparel/[^?#]+",
           ("sneakers",), xhr=("cnstrc.com",)),
    Recipe("chairish", "chairish.com", "https://www.chairish.com/search?q={q}", r"/product/\d+",
           HOME, embedded=("window.PRODUCT_ID_TO_PRODUCT_JSON_MAP",)),
    Recipe("1stdibs", "1stdibs.com", "https://www.1stdibs.com/search/?q={q}", r"/id-[a-z]_\d+",
           HOME + ("luxury",), xhr=("graphql", "soa/graphql")),
    Recipe("kaiyo", "kaiyo.com", "https://kaiyo.com/furniture/?q={q}", r"/products?/[^?#]+", HOME, xhr=("api",)),
    Recipe("aptdeco", "aptdeco.com", "https://www.aptdeco.com/catalog/furniture?search={q}", r"/products?/[^?#]+",
           HOME, embedded=("window.__NEXT_DATA__",)),
    Recipe("pamono", "pamono.com", "https://www.pamono.com/catalogsearch/result/?q={q}", r"/[a-z0-9-]+-\d+$", HOME),
    Recipe("liveauctioneers", "liveauctioneers.com",
           "https://www.liveauctioneers.com/search/?keyword={q}&status=online", r"/item/\d+", HOME + ("luxury",),
           sold="https://www.liveauctioneers.com/search/?keyword={q}&status=archive", login=True,
           notes="winning bids show when signed in"),
    Recipe("invaluable", "invaluable.com", "https://www.invaluable.com/search?query={q}&keyword={q}",
           r"/auction-lot/[^?#]+", HOME + ("luxury",), sold="https://www.invaluable.com/search?query={q}&keyword={q}&upcoming=false",
           xhr=("algolia.net",), login=True, notes="sold prices show when signed in"),
    Recipe("offerup", "offerup.com", "https://offerup.com/search?q={q}", r"/item/detail/[^?#]+", FASHION + HOME,
           xhr=("graphql",)),
    Recipe("craigslist", "craigslist.org", "https://{city}.craigslist.org/search/sss?query={q}", r"/d/[^?#]+\.html",
           HOME + ("general",)),
    Recipe("rubylane", "rubylane.com", "https://www.rubylane.com/search?q={q}", r"/item/[^?#]+", HOME + ("luxury",)),
    Recipe("etsy_web", "etsy.com", "https://www.etsy.com/search?q={q}&explicit=1&is_vintage=true", r"/listing/\d+",
           HOME + FASHION, notes="prefer the official API when a key is set"),
]}

# Never driven as the user: eBay's user agreement (2026-02-20) bans LLM-driven bots; we use its API.
NEVER = {"ebay": "use the official Browse API"}


def for_segment(segment: str, consented: set[str] | None = None) -> list[Recipe]:
    out = [r for r in RECIPES.values() if segment in r.segments]
    if consented is not None:
        out = [r for r in out if r.name in consented]
    return out
