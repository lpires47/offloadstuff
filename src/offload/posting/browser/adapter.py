"""PlatformAdapter for platforms without a seller API: the user's account, operated via computer use."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from ...llm import LLM
from ...negotiation.models import Decision, Offer
from ..base import Event, MessageEvent, OfferEvent, PlatformListing, SaleEvent
from . import tasks
from .computer_use import ComputerUseRunner, TaskResult
from .sessions import browser_page


class BrowserTaskError(RuntimeError):
    def __init__(self, result: TaskResult):
        super().__init__(f"{result.status}: {result.summary}")
        self.result = result

    @property
    def needs_user(self) -> bool:
        return self.result.needs_user


def _usd_to_cents(value) -> int:
    return round(float(str(value).replace("$", "").replace(",", "").strip()) * 100)


@dataclass
class BrowserAdapter:
    name: str  # platform key in tasks.PLATFORMS
    user_id: str
    llm: LLM
    approve: Callable[[str], bool] = lambda summary: False
    headless: bool = True
    sessions_root: Path | None = None

    def _run(self, task: tasks.BrowserTask) -> TaskResult:
        with browser_page(self.user_id, self.name, headless=self.headless, root=self.sessions_root) as page:
            result = ComputerUseRunner(self.llm, page, approve=self.approve).run(task)
        if result.status != "done":
            raise BrowserTaskError(result)
        return result

    def create_listing(self, listing: dict, *, photos: list[str]) -> PlatformListing:
        r = self._run(tasks.create_listing(self.name, listing, photos)).result
        url = r.get("listing_url")
        lid = r.get("listing_id") or (hashlib.sha1(url.encode()).hexdigest()[:12] if url else "unknown")
        return PlatformListing(self.name, lid, url, listing["price_cents"], extra={"fields_guessed": r.get("fields_guessed", [])})

    def update_price(self, listing: PlatformListing, price_cents: int) -> None:
        self._run(tasks.update_price(self.name, listing.url, price_cents))
        listing.price_cents = price_cents

    def delist(self, listing: PlatformListing) -> None:
        self._run(tasks.delist(self.name, listing.url))
        listing.status = "delisted"

    def poll(self, listing: PlatformListing, since: datetime | None) -> list[Event]:
        r = self._run(tasks.read_inbox(self.name, listing.url)).result
        now = datetime.now(timezone.utc)
        events: list[Event] = []
        for o in r.get("offers") or []:
            buyer = str(o.get("buyer") or "unknown")
            oid = o.get("offer_id") or hashlib.sha1(f"{buyer}{o.get('amount_usd')}{o.get('received')}".encode()).hexdigest()[:12]
            offer = Offer(
                id=f"{self.name}-{oid}", platform=self.name, buyer_id=buyer,
                amount_cents=_usd_to_cents(o["amount_usd"]), received_at=now, message=str(o.get("message") or ""),
            )
            events.append(OfferEvent(listing.listing_id, offer))
        for m in r.get("messages") or []:
            buyer = str(m.get("buyer") or "unknown")
            events.append(MessageEvent(listing.listing_id, self.name, str(m.get("thread_id") or buyer), buyer, str(m.get("text") or ""), now))
        if r.get("sold"):
            events.append(SaleEvent(listing.listing_id, self.name, "unknown", listing.price_cents, now))
        return events

    def respond_to_offer(self, listing: PlatformListing, offer: Offer, decision: Decision, message: str) -> None:
        self._run(tasks.respond_to_offer(self.name, listing.url, offer.buyer_id, decision.action, decision.amount_cents, message))

    def send_message(self, listing: PlatformListing, thread_id: str, text: str) -> None:
        task = tasks.BrowserTask(
            self.name, "send_message", "Send this exact message in the conversation with this buyer about this listing.",
            {"listing_url": listing.url, "thread": thread_id, "message": text}, '{"sent": bool}',
            listing.url, tasks.PLATFORMS[self.name]["domains"],
        )
        self._run(task)
