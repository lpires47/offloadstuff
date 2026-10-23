"""Price drops when nothing sells: a visible schedule, never below the floor.

Each cut is sized to clear the platform's buyer-notification threshold, so a drop actually reaches the
people who liked the item (Poshmark notifies likers at >=10% and >=$10; Mercari at >=5% under the
lowest price so far).
"""

from __future__ import annotations

from dataclasses import dataclass

from .policy import round_price

CADENCE_DAYS = {"fast": 2, "balanced": 4, "most": 7}
STEP = {"fast": 0.10, "balanced": 0.08, "most": 0.06}

NOTIFY_MIN = {
    "poshmark": (0.10, 1000),
    "mercari": (0.05, 0),
}


@dataclass(frozen=True)
class Drop:
    new_price_cents: int
    reason: str


def next_drop(
    current_cents: int,
    floor_cents: int,
    *,
    speed: str,
    days_since_last_change: float,
    had_offers_recently: bool,
    platform: str | None = None,
) -> Drop | None:
    if had_offers_recently or days_since_last_change < CADENCE_DAYS[speed] or current_cents <= floor_cents:
        return None
    step = STEP[speed]
    min_pct, min_abs = NOTIFY_MIN.get(platform or "", (0.0, 0))
    cut = max(current_cents * max(step, min_pct), min_abs)
    target = max(round_price(current_cents - cut), floor_cents)
    if target >= current_cents:
        return None
    if platform in NOTIFY_MIN and target != floor_cents:
        # Make sure rounding didn't take the cut back under the notification threshold.
        if (current_cents - target) < max(current_cents * min_pct, min_abs):
            target = max(floor_cents, target - 100)
    return Drop(target, f"no offers for {days_since_last_change:g} days")
