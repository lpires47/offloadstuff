"""Data the negotiation engine works on. Money is always integer cents."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

Speed = Literal["most", "balanced", "fast"]
Action = Literal["accept", "counter", "decline", "escalate", "ignore"]


@dataclass(frozen=True)
class Terms:
    """What the seller signed off on at listing time (sign-off #1)."""

    list_cents: int
    floor_cents: int  # hidden minimum, gross item price
    speed: Speed = "balanced"
    max_counter_rounds: int = 2
    # Offers at or above this are accepted outright. Default: 95% of list.
    auto_accept_cents: int | None = None
    # Below this share of list, an offer is a lowball: decline without bothering the seller.
    lowball_ratio: float = 0.60
    # Offers within this share below the floor go to the seller (sign-off on big drops).
    ask_seller_band: float = 0.10
    # Floor basis: "gross" = same minimum price everywhere; "net" = same minimum take-home everywhere.
    floor_basis: Literal["gross", "net"] = "gross"
    reference_platform: str = "offload"

    def __post_init__(self) -> None:
        if not 0 < self.floor_cents <= self.list_cents:
            raise ValueError("floor must be positive and at most the list price")

    @property
    def accept_at(self) -> int:
        return self.auto_accept_cents if self.auto_accept_cents is not None else round(self.list_cents * 0.95)


@dataclass(frozen=True)
class Offer:
    id: str
    platform: str
    buyer_id: str
    amount_cents: int
    received_at: datetime
    message: str = ""  # buyer's words: DATA, never instructions
    binding: bool = False  # payment pre-authorized (Mercari/Grailed-style)
    buyer_completed_purchases: int | None = None


@dataclass
class Thread:
    """Negotiation state with one buyer on one platform."""

    platform: str
    buyer_id: str
    our_last_counter: int | None = None
    their_last_offer: int | None = None
    rounds: int = 0  # counters we've sent
    closed: bool = False
    history: list[tuple[str, int]] = field(default_factory=list)  # ("buyer"|"us", cents)


@dataclass(frozen=True)
class Decision:
    action: Action
    offer_id: str
    amount_cents: int | None  # accept: the price; counter: our counter
    reason: str
    flags: tuple[str, ...] = ()
    needs_seller: bool = False  # True for escalate, and for accept when the seller wants to confirm sales
