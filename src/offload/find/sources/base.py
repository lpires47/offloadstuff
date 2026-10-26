"""Common shape for every place we search. A source turns a SearchPlan into Listings, fast, or fails."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

import httpx

from offload.images import Photo

from ..models import ItemProfile, Listing

USER_AGENT = "OffloadBot/0.1 (+https://offload.example/bot; shopping search on behalf of a user)"


@dataclass
class SearchPlan:
    profile: ItemProfile
    exact_queries: list[str]
    similar_queries: list[str]
    photo: Photo | None = None
    domains: list[str] = field(default_factory=list)  # for web search: resale sites worth querying first
    retail_domains: list[str] = field(default_factory=list)
    shopify_stores: list[str] = field(default_factory=list)
    per_source_limit: int = 30


class Source(Protocol):
    name: str

    async def search(self, plan: SearchPlan, client: httpx.AsyncClient) -> list[Listing]:
        """Return listings for the plan. Raise on failure; the engine records it and moves on."""


def cents(value) -> int | None:
    """'129.00' / 129 / '$129' -> 12900. None when it isn't a price."""
    if value is None:
        return None
    try:
        text = str(value).replace("$", "").replace(",", "").strip()
        return int(round(float(text) * 100))
    except ValueError:
        return None
