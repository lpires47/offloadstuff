"""Seller side of the same engine: the Find-it ladder becomes the market the pricing engine reads.

Every listing the search found becomes an Observation: exact items weigh most, other variants and
similar pieces less. Sold listings are sales; active and expired ones are unsold asks (evidence the
ask was too high, stronger the longer they sat). Counts of live and sold exact items give supply and
sell-through. The retail price of the new item anchors the prior.

eBay's API terms (9.5) bar using eBay content to suggest or model prices without written consent,
so eBay listings never enter pricing.
"""

from __future__ import annotations

from datetime import date

from ..find.models import NO_PRICING_SOURCES, Ladder, Result
from ..pricing import PriceEstimate
from ..pricing.engine import ItemFacts, MarketState, Observation, Speed, Valuation, value

SIMILARITY = {"exact_used": 1.0, "exact_new": 1.0}


def _similarity(r: Result) -> float:
    if r.rung in SIMILARITY:
        return SIMILARITY[r.rung] * min(1.0, 0.4 + r.confidence)
    # "Same model, other version" scores >1 in the ladder; plain similar pieces score lower.
    return 0.7 if r.score >= 1.0 and r.reason.startswith("Same model") else min(0.45, 0.2 + 0.25 * r.score)


def observations(ladder: Ladder) -> list[Observation]:
    obs = []
    for r in [*ladder.exact_used, *ladder.similar, *ladder.sold]:
        x = r.listing
        if not x.price_cents or x.source in NO_PRICING_SOURCES:
            continue
        obs.append(
            Observation(
                price_cents=x.unit_price_cents,  # a pair at $400 is $200 a chair
                status=x.status,
                platform=x.source.split(":")[-1].removesuffix(".com"),
                similarity=_similarity(r),
                condition="unknown",
                days_listed=x.days_listed,
                observed_on=date.fromisoformat(x.sold_on) if x.sold_on else None,
                shipping_cents=x.shipping_cents,
                sold_price_is_list=x.sold_price_is_list,
                likes=x.likes,
                url=x.url,
                title=x.title,
                size=x.attributes.get("size"),
            )
        )
    return obs


def market_state(ladder: Ladder) -> MarketState:
    exact = [r.listing for r in [*ladder.exact_used, *ladder.sold]
             if r.rung != "similar" and r.listing.source not in NO_PRICING_SOURCES]
    sold = [x for x in exact if x.status == "sold"]
    active = [x for x in exact if x.status == "active"]
    recent_new = [x for x in active if x.days_listed is not None and x.days_listed <= 30]
    has_ages = any(x.days_listed is not None for x in active)
    return MarketState(
        active_count=len(active) if active else None,
        sold_last_90d=len(sold) if sold else None,
        new_listings_last_30d=len(recent_new) if has_ages else None,
    )


def retail_cents(ladder: Ladder) -> int | None:
    prices = sorted(
        r.listing.price_cents for r in ladder.exact_new
        if r.listing.price_cents and r.listing.source not in NO_PRICING_SOURCES
    )
    return prices[len(prices) // 2] if prices else None


def value_from_ladder(
    ladder: Ladder,
    *,
    segment: str,
    condition: str,
    speed: Speed = "balanced",
    platforms: list[str] | None = None,
    season_family: str = "default",
    identification=None,
    photo_count: int = 0,
) -> Valuation | None:
    facts = ItemFacts(segment=segment, condition=condition, retail_cents=retail_cents(ladder),
                      season_family=season_family, photo_count=photo_count)
    if identification is not None:  # what this specific item is, has and lacks
        i = identification
        facts.authenticity_risk = i.authenticity_risk
        facts.flaws = [f.severity for f in i.flaws]
        facts.size = i.size.value if i.size.value and i.size.confidence >= 0.8 else None
        named = {a.name.lower(): (a.value or "").lower() for a in i.attributes}
        for key in ("original box", "dust bag", "box and papers", "tags"):
            if named.get(key) in ("no", "missing", "none", "without"):
                facts.complete = False
    if platforms:
        facts.platforms = platforms
    obs = observations(ladder)
    if not obs and not facts.retail_cents:
        return None
    return value(facts, obs, market=market_state(ladder), speed=speed)


def as_estimate(v: Valuation) -> PriceEstimate:
    """The listing composer's price shape, from the best platform's plan."""
    b = v.best
    return PriceEstimate(
        list_cents=b.list_cents,
        expected_cents=b.expected_sale_cents,
        floor_cents=b.floor_cents,
        p10_cents=v.range_cents[0],
        p90_cents=v.range_cents[1],
        est_days_to_sell=v.median_days,
        confidence=v.confidence,
        notes=v.drivers + v.flags,
    )


def price_from_ladder(ladder: Ladder, condition: str, speed: str = "balanced", segment: str = "general"):
    """Back-compat wrapper: a PriceEstimate for the best platform, or None without any evidence."""
    v = value_from_ladder(ladder, segment=segment, condition=condition, speed=speed)  # type: ignore[arg-type]
    return as_estimate(v) if v else None
