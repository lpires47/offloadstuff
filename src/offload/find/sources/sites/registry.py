"""Which direct site connectors exist, and which are switched on.

A connector runs only if its site is named in OFFLOAD_ENABLED_SITES (comma-separated), because every
one of these sites' terms restricts automated access and enabling one is a business and legal
decision, not a technical one. Sites without an enabled connector are still covered by web search.
Status per site lives in docs/research/fashion_sites.md and furniture_sites.md.
"""

from __future__ import annotations

import os

from .base import SiteConnector
from .grailed import Grailed
from .poshmark import Poshmark

CONNECTORS: dict[str, type[SiteConnector]] = {
    "poshmark": Poshmark,
    "grailed": Grailed,
}

# Why each site isn't a connector (yet). Shown by `offload sites`.
NOT_CONNECTED = {
    "mercari": "search needs a browser-issued token behind Cloudflare; no bypass. Web search + partnership",
    "depop": "paging API behind Cloudflare; owned by eBay: ask for partner access",
    "vinted": "Cloudflare + DataDome, ToS bans bots. Web search + partnership",
    "therealreal": "PerimeterX. Affiliate feed via Impact",
    "vestiairecollective": "Cloudflare challenge on every route. Affiliate feed via Rakuten",
    "thredup": "ToS not reviewed; affiliate feed via Rakuten",
    "stockx": "PerimeterX/Cloudflare. StockX Developer Program",
    "goat": "Cloudflare; affiliate via Awin",
    "fashionphile": "endpoint unconfirmed; affiliate via Rakuten",
    "facebook": "no read API; hand-off links to the shopper's own Marketplace search",
}


def enabled_names() -> list[str]:
    raw = os.environ.get("OFFLOAD_ENABLED_SITES", "")
    return [s.strip().lower() for s in raw.split(",") if s.strip()]


def enabled_connectors(segment: str) -> list[SiteConnector]:
    out = []
    for name in enabled_names():
        cls = CONNECTORS.get(name)
        if cls is not None and segment in cls.segments:
            out.append(cls())
    return out
