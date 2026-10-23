"""Price from matched sold comps. The model never sets the number; this module does.

v1 is statistics over comps that a matcher has already scored. The comp matcher and comp sources
(eBay sold data, platform scrapes) plug in behind `Comp.match_score`.
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from datetime import date
from typing import Literal

Speed = Literal["most", "balanced", "fast"]

# Relative price of each condition vs "very_good", used to adjust comps of a different condition.
CONDITION_FACTOR = {
    "new_with_tags": 1.30,
    "new_without_tags": 1.18,
    "like_new": 1.10,
    "very_good": 1.00,
    "good": 0.85,
    "fair": 0.65,
    "poor": 0.40,
    "unknown": 0.90,
}

# Fallback when there are too few comps: share of current retail by condition (Vinted's rule of thumb).
RETAIL_SHARE = {
    "new_with_tags": 0.75,
    "new_without_tags": 0.65,
    "like_new": 0.55,
    "very_good": 0.45,
    "good": 0.32,
    "fair": 0.2,
    "poor": 0.1,
    "unknown": 0.35,
}

# Where each speed sits in the matched-sales distribution: (list, expected, floor) quantiles.
SPEED_QUANTILES = {
    "most": (0.85, 0.65, 0.45),
    "balanced": (0.70, 0.50, 0.32),
    "fast": (0.50, 0.38, 0.22),
}
MIN_MATCH = 0.7
MIN_COMPS = 5


@dataclass(frozen=True)
class Comp:
    title: str
    price_cents: int
    sold: bool
    platform: str
    condition: str = "unknown"
    match_score: float = 1.0  # 0-1 from the comp matcher: same product, variant, size class
    sold_on: date | None = None
    url: str | None = None


@dataclass
class PriceEstimate:
    list_cents: int
    expected_cents: int
    floor_cents: int
    p10_cents: int
    p90_cents: int
    est_days_to_sell: float | None
    confidence: Literal["high", "medium", "low"]
    comps_used: list[Comp] = field(default_factory=list)
    comps_dropped: int = 0
    method: Literal["sold_comps", "retail_fallback"] = "sold_comps"
    notes: list[str] = field(default_factory=list)


def _quantile(sorted_vals: list[float], q: float) -> float:
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    pos = q * (len(sorted_vals) - 1)
    lo, hi = math.floor(pos), math.ceil(pos)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (pos - lo)


def nice_price(cents: float) -> int:
    """Round to prices people actually list at: whole dollars, $5 steps above $200."""
    dollars = cents / 100
    if dollars >= 200:
        return int(round(dollars / 5) * 5 * 100)
    return int(max(1, round(dollars)) * 100)


def estimate_price(
    comps: list[Comp],
    condition: str,
    speed: Speed = "balanced",
    *,
    retail_cents: int | None = None,
    sell_through: float | None = None,
) -> PriceEstimate:
    """Price an item from comps. `sell_through` = sold / (sold + active) over ~90 days, if known."""
    target = CONDITION_FACTOR.get(condition, CONDITION_FACTOR["unknown"])
    used = [c for c in comps if c.sold and c.match_score >= MIN_MATCH]
    dropped = len(comps) - len(used)
    notes: list[str] = []

    if len(used) < MIN_COMPS:
        if retail_cents:
            base = retail_cents * RETAIL_SHARE.get(condition, RETAIL_SHARE["unknown"])
            q_list, q_exp, q_floor = SPEED_QUANTILES[speed]
            notes.append(f"Only {len(used)} matched sales; priced from retail and condition instead.")
            return PriceEstimate(
                list_cents=nice_price(base * (0.8 + 0.5 * q_list)),
                expected_cents=nice_price(base * (0.8 + 0.4 * q_exp)),
                floor_cents=nice_price(base * (0.7 + 0.4 * q_floor)),
                p10_cents=nice_price(base * 0.7),
                p90_cents=nice_price(base * 1.3),
                est_days_to_sell=None,
                confidence="low",
                comps_used=used,
                comps_dropped=dropped,
                method="retail_fallback",
                notes=notes,
            )
        raise ValueError(f"need at least {MIN_COMPS} matched sold comps or a retail price; got {len(used)}")

    # Normalize every comp to the target condition, weighting closer matches more by repeating them.
    adjusted: list[float] = []
    for c in used:
        factor = target / CONDITION_FACTOR.get(c.condition, CONDITION_FACTOR["unknown"])
        weight = 2 if c.match_score >= 0.9 else 1
        adjusted.extend([c.price_cents * factor] * weight)
    adjusted.sort()

    q_list, q_exp, q_floor = SPEED_QUANTILES[speed]
    list_c = nice_price(_quantile(adjusted, q_list))
    exp_c = nice_price(_quantile(adjusted, q_exp))
    floor_c = min(nice_price(_quantile(adjusted, q_floor)), exp_c)

    days = None
    if sell_through is not None and sell_through > 0:
        # Rough: a 50% sell-through over 90 days -> ~45 days at the median; faster speeds sell sooner.
        median_days = 90 * (1 - sell_through) / max(sell_through, 0.05) * 0.5 + 3
        days = round(median_days * {"most": 2.0, "balanced": 1.0, "fast": 0.4}[speed], 1)

    spread = (_quantile(adjusted, 0.9) - _quantile(adjusted, 0.1)) / max(statistics.median(adjusted), 1)
    confidence = "high" if len(used) >= 15 and spread < 0.8 else "medium" if len(used) >= 8 else "low"
    return PriceEstimate(
        list_cents=list_c,
        expected_cents=exp_c,
        floor_cents=floor_c,
        p10_cents=nice_price(_quantile(adjusted, 0.1)),
        p90_cents=nice_price(_quantile(adjusted, 0.9)),
        est_days_to_sell=days,
        confidence=confidence,
        comps_used=used,
        comps_dropped=dropped,
        notes=notes,
    )
