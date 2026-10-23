"""Across platforms: which acceptable offer wins, and how long to wait for a better one.

An item listed in five places can draw several acceptable offers at once. The arbiter compares them on
what the seller takes home (net), not the headline price, and holds briefly when a better outcome is
plausibly seconds away (an open counter the buyer is likely to take).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from .fees import net_payout
from .models import Offer

# How long to hold an acceptable offer while a higher-net negotiation is still open.
HOLD_WINDOW = {"fast": timedelta(minutes=15), "balanced": timedelta(hours=2), "most": timedelta(hours=8)}


@dataclass(frozen=True)
class Ranked:
    offer: Offer
    net_cents: int


@dataclass(frozen=True)
class Pick:
    winner: Ranked | None
    hold_until: datetime | None
    reason: str


def rank(offers: list[Offer]) -> list[Ranked]:
    """Highest net first; ties go to binding offers, then experienced buyers, then the earliest."""
    ranked = [Ranked(o, net_payout(o.platform, o.amount_cents)) for o in offers]
    return sorted(
        ranked,
        key=lambda r: (-r.net_cents, not r.offer.binding, -(r.offer.buyer_completed_purchases or 0), r.offer.received_at),
    )


def pick(
    acceptable: list[Offer],
    *,
    open_counters: dict[str, int],  # offer/thread id -> our open counter price, per platform
    counter_platforms: dict[str, str],
    speed: str,
    now: datetime,
    first_acceptable_at: datetime | None,
) -> Pick:
    """Choose the winner among offers we'd accept, or hold for an open counter that would net more."""
    if not acceptable:
        return Pick(None, None, "no acceptable offers")
    best = rank(acceptable)[0]
    better_pending = [
        (tid, cents)
        for tid, cents in open_counters.items()
        if net_payout(counter_platforms[tid], cents) > best.net_cents
    ]
    if better_pending:
        start = first_acceptable_at or now
        deadline = start + HOLD_WINDOW.get(speed, HOLD_WINDOW["balanced"])
        if now < deadline:
            return Pick(None, deadline, f"holding: {len(better_pending)} open counter(s) would net more")
    return Pick(best, None, f"best net ${best.net_cents / 100:.2f} on {best.offer.platform}")
