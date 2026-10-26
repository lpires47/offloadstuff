"""Seller side of the same engine: the Find-it ladder supplies the comps and the retail anchor.

Exact-used listings are the comps; exact-new listings give the current retail price for the fallback.
Comps are current asking prices on non-eBay sites, discounted to what such items typically sell
for, and the estimate says so. eBay's API terms (9.5) bar using eBay content to suggest or model
prices without written consent, so eBay listings never enter pricing.
"""

from __future__ import annotations

from ..find.models import NO_PRICING_SOURCES, Ladder
from ..pricing import Comp, PriceEstimate, estimate_price
from ..pricing.estimate import MIN_COMPS

ASK_TO_SALE = 0.85  # asking prices run above sale prices; replace with a learned ratio per segment


def comps_from_ladder(ladder: Ladder) -> list[Comp]:
    comps = []
    for r in ladder.exact_used:
        if not r.listing.price_cents or r.listing.available is False or r.listing.source in NO_PRICING_SOURCES:
            continue
        comps.append(
            Comp(
                title=r.listing.title,
                price_cents=int(r.listing.price_cents * ASK_TO_SALE),
                sold=True,  # treated as a sale estimate; see module docstring
                platform=r.listing.source,
                condition="unknown",
                match_score=r.confidence,
                url=r.listing.url,
            )
        )
    return comps


def price_from_ladder(ladder: Ladder, condition: str, speed: str = "balanced") -> PriceEstimate | None:
    comps = comps_from_ladder(ladder)
    new_prices = sorted(
        r.listing.price_cents for r in ladder.exact_new if r.listing.price_cents and r.listing.source not in NO_PRICING_SOURCES
    )
    retail = new_prices[len(new_prices) // 2] if new_prices else None
    if len([c for c in comps if c.match_score >= 0.7]) < MIN_COMPS and retail is None:
        return None
    est = estimate_price(comps, condition, speed, retail_cents=retail)  # type: ignore[arg-type]
    if est.method == "sold_comps":
        est.notes.append(
            f"Based on {len(est.comps_used)} current listings of this exact item, adjusted to typical sale "
            "prices. Real sold prices replace this once sold data is connected."
        )
    return est
