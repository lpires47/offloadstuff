"""The interface every platform implements, whether through an official API or the user's browser."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, Protocol

from ..negotiation.models import Decision, Offer


@dataclass
class PlatformListing:
    platform: str
    listing_id: str
    url: str | None
    price_cents: int
    status: Literal["live", "sold", "delisted", "pending"] = "live"
    extra: dict = field(default_factory=dict)  # platform ids we need later (eBay offerId, sku, ...)


@dataclass(frozen=True)
class OfferEvent:
    listing_id: str
    offer: Offer


@dataclass(frozen=True)
class MessageEvent:
    listing_id: str
    platform: str
    thread_id: str
    buyer_id: str
    text: str
    received_at: datetime


@dataclass(frozen=True)
class SaleEvent:
    """A completed purchase on the platform: buy-now, or the buyer took our counter."""

    listing_id: str
    platform: str
    buyer_id: str
    price_cents: int
    at: datetime
    order_id: str | None = None


Event = OfferEvent | MessageEvent | SaleEvent


class PlatformAdapter(Protocol):
    name: str

    def create_listing(self, listing: dict, *, photos: list[str]) -> PlatformListing:
        """`listing` is ListingDraft.public_view() plus any platform-specific fields. Never includes the floor."""

    def update_price(self, listing: PlatformListing, price_cents: int) -> None: ...

    def delist(self, listing: PlatformListing) -> None: ...

    def poll(self, listing: PlatformListing, since: datetime | None) -> list[Event]: ...

    def respond_to_offer(self, listing: PlatformListing, offer: Offer, decision: Decision, message: str) -> None: ...

    def send_message(self, listing: PlatformListing, thread_id: str, text: str) -> None: ...
