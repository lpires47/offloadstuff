"""An in-memory marketplace with scripted buyers, for tests and the simulator."""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from datetime import datetime

from ..negotiation.models import Decision, Offer
from .base import Event, MessageEvent, OfferEvent, PlatformListing, SaleEvent


@dataclass
class ScriptedBuyer:
    """Opens at `opening_cents`, will pay up to `max_cents`, raises by `step_cents` after each counter."""

    buyer_id: str
    opening_cents: int
    max_cents: int
    step_cents: int = 500
    message: str = ""
    completed_purchases: int = 5
    patience: int = 3  # counters before walking away


@dataclass
class FakePlatform:
    name: str
    log: list[str] = field(default_factory=list)
    listings: dict[str, PlatformListing] = field(default_factory=dict)
    _queue: list[Event] = field(default_factory=list)
    _buyers: dict[tuple[str, str], ScriptedBuyer] = field(default_factory=dict)
    _ids: itertools.count = field(default_factory=lambda: itertools.count(1))

    # ---- PlatformAdapter ----
    def create_listing(self, listing: dict, *, photos: list[str]) -> PlatformListing:
        assert "floor_cents" not in listing, "the hidden minimum must never reach a platform"
        lid = f"{self.name}-{next(self._ids)}"
        pl = PlatformListing(self.name, lid, f"https://{self.name}.example/{lid}", listing["price_cents"])
        self.listings[lid] = pl
        self.log.append(f"listed {lid} at {listing['price_cents']}")
        return pl

    def update_price(self, listing: PlatformListing, price_cents: int) -> None:
        listing.price_cents = price_cents
        self.log.append(f"price {listing.listing_id} -> {price_cents}")

    def delist(self, listing: PlatformListing) -> None:
        if listing.status == "live":
            listing.status = "delisted"
        self.log.append(f"delisted {listing.listing_id}")

    def poll(self, listing: PlatformListing, since: datetime | None) -> list[Event]:
        mine = [e for e in self._queue if e.listing_id == listing.listing_id]
        self._queue = [e for e in self._queue if e.listing_id != listing.listing_id]
        return mine

    def respond_to_offer(self, listing: PlatformListing, offer: Offer, decision: Decision, message: str) -> None:
        self.log.append(f"{decision.action} {offer.id} {decision.amount_cents} :: {message}")
        if decision.action == "accept":
            return
        buyer = self._buyers.get((listing.listing_id, offer.buyer_id))
        if decision.action == "counter" and buyer and decision.amount_cents is not None:
            buyer.patience -= 1
            if decision.amount_cents <= buyer.max_cents:
                # Buyer takes the counter: on most platforms that completes the purchase.
                self._queue.append(SaleEvent(listing.listing_id, self.name, buyer.buyer_id, decision.amount_cents, offer.received_at))
            elif buyer.patience > 0:
                nxt = min(buyer.max_cents, offer.amount_cents + buyer.step_cents)
                self._queue.append(OfferEvent(listing.listing_id, self._offer(listing, buyer, nxt, offer.received_at)))

    def send_message(self, listing: PlatformListing, thread_id: str, text: str) -> None:
        self.log.append(f"message {thread_id} :: {text}")

    # ---- test controls ----
    def _offer(self, listing: PlatformListing, buyer: ScriptedBuyer, cents: int, at: datetime) -> Offer:
        return Offer(
            id=f"{self.name}-o{next(self._ids)}",
            platform=self.name,
            buyer_id=buyer.buyer_id,
            amount_cents=cents,
            received_at=at,
            message=buyer.message,
            buyer_completed_purchases=buyer.completed_purchases,
        )

    def buyer_offers(self, listing: PlatformListing, buyer: ScriptedBuyer, at: datetime) -> Offer:
        self._buyers[(listing.listing_id, buyer.buyer_id)] = buyer
        offer = self._offer(listing, buyer, buyer.opening_cents, at)
        self._queue.append(OfferEvent(listing.listing_id, offer))
        return offer

    def buyer_messages(self, listing: PlatformListing, buyer_id: str, text: str, at: datetime) -> None:
        self._queue.append(MessageEvent(listing.listing_id, self.name, f"t-{buyer_id}", buyer_id, text, at))

    def buy_now(self, listing: PlatformListing, buyer_id: str, at: datetime) -> None:
        self._queue.append(SaleEvent(listing.listing_id, self.name, buyer_id, listing.price_cents, at))
