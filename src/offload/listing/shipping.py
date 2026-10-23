"""Packed size and weight -> shipping tier. Estimating this from the photo avoids overweight charges."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Tier = Literal["envelope", "small", "medium", "large", "xl", "local_only"]

# Typical packed size (in) and weight (lb) by category when the model can't estimate the item.
CATEGORY_DEFAULTS = {
    "apparel": ((12, 10, 3), 1.0),
    "footwear": ((14, 9, 5), 2.5),
    "bags": ((14, 12, 6), 1.8),
    "accessories": ((9, 6, 2), 0.4),
    "jewelry": ((6, 4, 2), 0.2),
    "watches": ((6, 4, 3), 0.5),
    "electronics": ((12, 9, 4), 2.0),
    "books_media": ((10, 7, 2), 1.2),
    "home_decor": ((14, 12, 8), 4.0),
    "kitchen": ((14, 12, 8), 4.0),
    "toys_games": ((14, 12, 6), 2.0),
    "collectibles": ((8, 6, 3), 0.6),
    "sports_outdoors": ((18, 14, 8), 5.0),
    "beauty": ((8, 6, 3), 0.6),
    "furniture": ((40, 30, 30), 40.0),
    "other": ((12, 10, 6), 2.0),
}


@dataclass(frozen=True)
class Package:
    length_in: float
    width_in: float
    height_in: float
    weight_lb: float
    tier: Tier
    estimated: bool


def tier_for(dims: tuple[float, float, float], weight_lb: float) -> Tier:
    longest = max(dims)
    girth_len = longest + 2 * sum(sorted(dims)[:2])
    if weight_lb > 50 or girth_len > 130:
        return "local_only"
    if weight_lb <= 0.5 and min(dims) <= 1 and longest <= 12:
        return "envelope"
    if weight_lb <= 1:
        return "small"
    if weight_lb <= 2:
        return "medium"
    if weight_lb <= 10:
        return "large"
    return "xl"


def package_for(category: str, weight_lb: float | None = None, item_dims: tuple[float, float, float] | None = None) -> Package:
    default_dims, default_weight = CATEGORY_DEFAULTS.get(category, CATEGORY_DEFAULTS["other"])
    estimated = weight_lb is None or item_dims is None
    # Add packaging: ~10% weight + 0.2 lb, 1 inch per side for rigid goods. Apparel folds into default mailer size.
    if category == "apparel" or item_dims is None:
        dims = default_dims
    else:
        dims = tuple(round(d + 2, 1) for d in sorted(item_dims, reverse=True))  # type: ignore[assignment]
    weight = round((weight_lb if weight_lb is not None else default_weight) * 1.1 + 0.2, 1)
    return Package(dims[0], dims[1], dims[2], weight, tier_for(dims, weight), estimated)
