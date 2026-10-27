"""Which direct site connectors exist, and which are switched on.

A connector runs only if its site is named in OFFLOAD_ENABLED_SITES (comma-separated), because every
one of these sites' terms restricts automated access and enabling one is a business and legal
decision, not a technical one. Sites without an enabled connector are still covered by web search.
Status per site lives in docs/research/fashion_sites.md and furniture_sites.md.
"""

from __future__ import annotations

import os

from .base import SiteConnector
from .aptdeco import AptDeco
from .chairish import Chairish
from .firstdibs import FirstDibs
from .grailed import Grailed
from .poshmark import Poshmark

CONNECTORS: dict[str, type[SiteConnector]] = {
    "poshmark": Poshmark,
    "grailed": Grailed,
    "1stdibs": FirstDibs,  # official MCP server: on by default
    "chairish": Chairish,
    "aptdeco": AptDeco,
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
    "kaiyo": "plain requests refused (bot wall); partnership or affiliate",
    "liveauctioneers": "ToS bans automated access; sold prices behind login. Ask for a data license",
    "invaluable": "ToS bans automated access; sold prices behind login. Ask for a data license",
    "offerup": "ToS bans third-party apps",
    "rubylane": "challenge page on plain requests",
    "pamono": "terms silent on automation; connector not built yet (cross-lists with Chairish)",
}


def enabled_names() -> list[str]:
    """Official interfaces are on unless named in OFFLOAD_DISABLED_SITES; the rest only if named in
    OFFLOAD_ENABLED_SITES."""
    raw = os.environ.get("OFFLOAD_ENABLED_SITES", "")
    named = [s.strip().lower() for s in raw.split(",") if s.strip()]
    off = {s.strip().lower() for s in os.environ.get("OFFLOAD_DISABLED_SITES", "").split(",") if s.strip()}
    official = [n for n, c in CONNECTORS.items() if getattr(c, "official", False)]
    return [n for n in dict.fromkeys(official + named) if n not in off]


def enabled_connectors(segment: str) -> list[SiteConnector]:
    out = []
    for name in enabled_names():
        cls = CONNECTORS.get(name)
        if cls is not None and segment in cls.segments:
            out.append(cls())
    return out
