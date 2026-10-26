"""Where to look first for a given item.

A static prior per category (which sites carry this kind of thing), reordered by what has actually
worked: every time a result from a site is shown and clicked or bought, that site moves up for that
category. Sites are grouped so one web-search query covers a few of them at once.
"""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from pathlib import Path

from .models import ItemProfile

# Ordered by how likely they are to carry the item, best first. Domains only; no logged-in sites.
PRIORS: dict[str, list[str]] = {
    "sneakers": ["stockx.com", "goat.com", "grailed.com", "flightclub.com", "poshmark.com", "depop.com", "mercari.com"],
    "luxury": ["therealreal.com", "vestiairecollective.com", "fashionphile.com", "rebag.com", "poshmark.com", "grailed.com"],
    "menswear": ["grailed.com", "poshmark.com", "depop.com", "mercari.com", "vinted.com", "thredup.com"],
    "fashion": ["poshmark.com", "depop.com", "mercari.com", "vinted.com", "thredup.com", "therealreal.com", "vestiairecollective.com"],
    "furniture": ["chairish.com", "1stdibs.com", "kaiyo.com", "aptdeco.com", "liveauctioneers.com", "invaluable.com"],
    "decor": ["chairish.com", "1stdibs.com", "liveauctioneers.com", "kaiyo.com", "mercari.com"],
    "general": ["mercari.com", "poshmark.com", "depop.com", "chairish.com"],
}

LUXURY_BRANDS = {
    "chanel", "hermes", "hermès", "louis vuitton", "gucci", "prada", "dior", "celine", "céline", "bottega veneta",
    "saint laurent", "ysl", "balenciaga", "fendi", "loewe", "goyard", "the row", "miu miu", "valentino", "cartier",
}
FASHION = {"apparel", "bags", "accessories", "jewelry", "watches"}
GROUP_SIZE = 4  # sites per web-search query


def segment(profile: ItemProfile) -> str:
    brand = (profile.brand or "").lower()
    if "sneaker" in profile.subcategory.lower() or "trainer" in profile.subcategory.lower():
        return "sneakers"
    if brand in LUXURY_BRANDS and profile.category in FASHION | {"footwear"}:
        return "luxury"
    if profile.category == "furniture":
        return "furniture"
    if profile.category in ("home_decor", "kitchen"):
        return "decor"
    if profile.category in FASHION | {"footwear"}:
        return "fashion"
    return "general"


@dataclass
class RouterStats:
    """Shown/clicked counts per segment and site, persisted as JSON. Thread-safe enough for one process."""

    path: Path | None = None
    counts: dict[str, dict[str, list[int]]] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    @classmethod
    def load(cls, path: Path) -> "RouterStats":
        counts = json.loads(path.read_text()) if path.exists() else {}
        return cls(path=path, counts=counts)

    def record(self, seg: str, domain: str, *, shown: int = 0, clicked: int = 0) -> None:
        with self._lock:
            row = self.counts.setdefault(seg, {}).setdefault(domain, [0, 0])
            row[0] += shown
            row[1] += clicked
            if self.path:
                self.path.write_text(json.dumps(self.counts))

    def rate(self, seg: str, domain: str) -> float:
        shown, clicked = self.counts.get(seg, {}).get(domain, [0, 0])
        return (clicked + 1) / (shown + 10)  # smoothed click-through; unseen sites sit at 0.1


@dataclass
class Route:
    segment: str
    resale_groups: list[list[str]]  # each group is one web-search query, best group first
    shopify_stores: list[str]


def route(profile: ItemProfile, stats: RouterStats | None = None, shopify: dict[str, list[str]] | None = None) -> Route:
    seg = segment(profile)
    prior = PRIORS[seg]
    if stats is not None:
        # Learned rate dominates once a site has real traffic; the prior order breaks ties.
        prior = sorted(prior, key=lambda d: (-stats.rate(seg, d), prior.index(d)))
    groups = [prior[i : i + GROUP_SIZE] for i in range(0, len(prior), GROUP_SIZE)]
    stores = (shopify or {}).get(seg, []) or (shopify or {}).get("general", [])
    return Route(seg, groups, stores)


def load_shopify_stores(path: Path) -> dict[str, list[str]]:
    """YAML-free format: lines of `segment: domain`. Lines starting with # are ignored."""
    stores: dict[str, list[str]] = {}
    if not path.exists():
        return stores
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        seg, domain = (x.strip() for x in line.split(":", 1))
        stores.setdefault(seg, []).append(domain)
    return stores
