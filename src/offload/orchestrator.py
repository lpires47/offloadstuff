"""Runs one item's sale across platforms: post, negotiate, pick the winner, close out.

The seller signs off twice: the listing (list price + hidden minimum, before `post`) and the final
sale. Counters are sent within the approved minimum without asking, so if a buyer takes a counter
the platform may complete the sale immediately; the seller is told, not asked, in that case.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Literal

from .listing.compose import ListingDraft
from .llm import LLM
from .negotiation.arbiter import pick
from .negotiation.guard import check_buyer_message
from .negotiation.messages import draft_reply, template
from .negotiation.models import Decision, Offer, Terms, Thread
from .negotiation.policy import decide, effective_floor, platform_list_price, record
from .negotiation.schedule import next_drop
from .posting.base import MessageEvent, OfferEvent, PlatformAdapter, PlatformListing, SaleEvent


@dataclass
class UserPrompt:
    kind: Literal["confirm_sale", "offer_below_minimum", "buyer_question", "sold", "blocked_scam", "double_sale", "already_sold"]
    text: str
    offer: Offer | None = None
    platform: str | None = None


@dataclass
class SellJob:
    draft: ListingDraft
    terms: Terms
    adapters: dict[str, PlatformAdapter]
    photos: list[str]
    llm: LLM | None = None  # for phrasing replies; None = templates only
    confirm_final_sale: bool = True
    log: Callable[[str], None] = print

    listings: dict[str, PlatformListing] = field(default_factory=dict)
    threads: dict[tuple[str, str], Thread] = field(default_factory=dict)
    acceptable: dict[str, Offer] = field(default_factory=dict)  # offer id -> offer we'd accept
    open_counters: dict[str, int] = field(default_factory=dict)  # thread key -> our open counter
    counter_platforms: dict[str, str] = field(default_factory=dict)
    first_acceptable_at: datetime | None = None
    pending_confirmation: Offer | None = None
    sold: SaleEvent | None = None
    last_price_change: datetime | None = None
    last_offer_at: datetime | None = None
    posted_at: datetime | None = None
    offer_ttl: timedelta = timedelta(hours=48)  # eBay Best Offers lapse after 48h; others similar or shorter
    after_sale_watch: timedelta = timedelta(hours=24)  # keep watching delisted listings for a racing second sale

    # ---- posting ----
    def post(self, now: datetime) -> None:
        base = self.draft.public_view()
        base["package"] = vars(self.draft.package)
        base["search_query"] = self.draft.search_query
        for name, adapter in self.adapters.items():
            listing = dict(base)
            listing["price_cents"] = platform_list_price(self.terms, name)
            # Let the platform handle the clear cases natively where it can (eBay Best Offer thresholds).
            listing["best_offer"] = {
                "auto_accept_cents": max(effective_floor(self.terms, name), round(self.terms.accept_at * listing["price_cents"] / self.terms.list_cents)),
                "auto_decline_cents": round(self.terms.list_cents * self.terms.lowball_ratio),
            }
            self.listings[name] = adapter.create_listing(listing, photos=self.photos)
            self.log(f"[{name}] live at ${listing['price_cents'] / 100:.0f}")
        self.last_price_change = now
        self.posted_at = now

    # ---- the loop ----
    def tick(self, now: datetime) -> list[UserPrompt]:
        prompts: list[UserPrompt] = []
        events = []
        for name, listing in list(self.listings.items()):
            watching = listing.status == "live" or (
                self.sold is not None and listing.status == "delisted" and now - self.sold.at < self.after_sale_watch
            )
            if watching:
                events += [(listing, e) for e in self.adapters[name].poll(listing, self.posted_at)]
        # Sales first: a sale anywhere changes what every other event means.
        for listing, event in [x for x in events if isinstance(x[1], SaleEvent)]:
            prompts += self._close_out(event)
        if self.sold:
            return prompts
        for listing, event in events:
            if isinstance(event, OfferEvent):
                prompts += self._on_offer(listing, event.offer, now)
            elif isinstance(event, MessageEvent):
                prompts += self._on_message(listing, event)

        for oid, o in list(self.acceptable.items()):
            if now - o.received_at > self.offer_ttl:
                del self.acceptable[oid]
        if not self.acceptable:
            self.first_acceptable_at = None

        if not self.pending_confirmation:
            choice = pick(
                list(self.acceptable.values()),
                open_counters=self.open_counters,
                counter_platforms=self.counter_platforms,
                speed=self.terms.speed,
                now=now,
                first_acceptable_at=self.first_acceptable_at,
            )
            if choice.winner:
                offer = choice.winner.offer
                if self.confirm_final_sale:
                    self.pending_confirmation = offer
                    prompts.append(UserPrompt(
                        "confirm_sale",
                        f"Sell for ${offer.amount_cents / 100:.0f} on {offer.platform}? You'd get ${choice.winner.net_cents / 100:.2f}.",
                        offer, offer.platform,
                    ))
                else:
                    prompts += self.confirm_sale(offer, now)
            elif choice.hold_until:
                self.log(f"holding until {choice.hold_until:%H:%M}: {choice.reason}")

        if not self.acceptable and not self.open_counters:
            prompts += self._maybe_drop(now)
        return prompts

    def _thread(self, offer: Offer) -> Thread:
        key = (offer.platform, offer.buyer_id)
        if key not in self.threads:
            self.threads[key] = Thread(offer.platform, offer.buyer_id)
        return self.threads[key]

    def _on_offer(self, listing: PlatformListing, offer: Offer, now: datetime) -> list[UserPrompt]:
        self.last_offer_at = now
        thread = self._thread(offer)
        decision = decide(offer, self.terms, thread, current_ask_cents=listing.price_cents)
        tkey = f"{offer.platform}:{offer.buyer_id}"
        self.log(f"[{offer.platform}] {offer.buyer_id} offers ${offer.amount_cents / 100:.0f} -> {decision.action}"
                 + (f" ${decision.amount_cents / 100:.0f}" if decision.amount_cents and decision.action == 'counter' else "")
                 + f" ({decision.reason})")
        if decision.action == "accept":
            # Don't accept on the platform yet: the arbiter compares across platforms first.
            self.acceptable[offer.id] = offer
            self.open_counters.pop(tkey, None)
            self.first_acceptable_at = self.first_acceptable_at or now
            return []
        if decision.action == "escalate":
            return [UserPrompt("offer_below_minimum",
                               f"{offer.platform} buyer offers ${offer.amount_cents / 100:.0f}, under your ${self.terms.floor_cents / 100:.0f} minimum.",
                               offer, offer.platform)]
        if decision.action == "ignore":
            return []
        self._send(listing, offer, decision, thread)
        if decision.action == "counter":
            self.open_counters[tkey] = decision.amount_cents
            self.counter_platforms[tkey] = offer.platform
        else:
            self.open_counters.pop(tkey, None)
        if "off-platform" in decision.reason:
            return [UserPrompt("blocked_scam", f"Blocked a scam attempt on {offer.platform}: {', '.join(decision.flags)}.", offer, offer.platform)]
        return []

    def _send(self, listing: PlatformListing, offer: Offer, decision: Decision, thread: Thread) -> None:
        facts = {"title": self.draft.title, "condition": self.draft.condition, **self.draft.attributes}
        text, problems = draft_reply(decision, offer.message, facts, self.llm)
        if problems:
            self.log(f"  reply fell back to template: {problems}")
        self.adapters[listing.platform].respond_to_offer(listing, offer, decision, text)
        record(thread, offer, decision)

    def _on_message(self, listing: PlatformListing, event: MessageEvent) -> list[UserPrompt]:
        guard = check_buyer_message(event.text)
        if guard.block:
            self.adapters[listing.platform].send_message(listing, event.thread_id, "Thanks! I only take payment and messages through the app.")
            return [UserPrompt("blocked_scam", f"Blocked a scam attempt on {listing.platform}: {', '.join(guard.flags)}.", platform=listing.platform)]
        return [UserPrompt("buyer_question", f"{event.buyer_id} on {listing.platform}: {event.text}", platform=listing.platform)]

    # ---- the seller's answers ----
    def confirm_sale(self, offer: Offer, now: datetime) -> list[UserPrompt]:
        listing = self.listings[offer.platform]
        if self.sold is not None or listing.status != "live":
            self.pending_confirmation = None
            return [UserPrompt("already_sold", "This item already sold, so that offer can't be accepted.", offer, offer.platform)]
        # Take it down everywhere else BEFORE accepting, so an open counter can't be taken meanwhile.
        for name, other in self.listings.items():
            if name != offer.platform and other.status == "live":
                self.adapters[name].delist(other)
                other.status = "delisted"
        decision = Decision("accept", offer.id, offer.amount_cents, "seller confirmed")
        self._send(listing, offer, decision, self._thread(offer))
        return self._close_out(SaleEvent(listing.listing_id, offer.platform, offer.buyer_id, offer.amount_cents, now))

    def hold_out(self, offer: Offer) -> None:
        self.acceptable.pop(offer.id, None)
        self.pending_confirmation = None
        if not self.acceptable:
            self.first_acceptable_at = None
        if self.sold is not None or self.listings[offer.platform].status != "live":
            return
        listing = self.listings[offer.platform]
        decision = Decision("decline", offer.id, None, "seller wants to hold out")
        self.adapters[offer.platform].respond_to_offer(listing, offer, decision, template(decision))

    def answer_below_minimum(self, offer: Offer, accept: bool, now: datetime) -> list[UserPrompt]:
        if accept:
            return self.confirm_sale(offer, now)
        self.hold_out(offer)
        return []

    # ---- endings ----
    def _close_out(self, sale: SaleEvent) -> list[UserPrompt]:
        if self.sold is not None:
            if (sale.platform, sale.listing_id) == (self.sold.platform, self.sold.listing_id):
                return []
            self.log(f"DOUBLE SALE: {sale.platform} also sold for ${sale.price_cents / 100:.0f}")
            adapter = self.adapters[sale.platform]
            cancel = getattr(adapter, "cancel_order", None)
            done = False
            if cancel is not None:
                try:
                    cancel(self.listings[sale.platform], sale.order_id)
                    done = True
                except Exception as exc:
                    self.log(f"  cancel failed: {exc}")
            text = (f"It also sold on {sale.platform}. " + ("We cancelled that order as out of stock; the buyer is refunded."
                    if done else "Please cancel that order as out of stock.") + " Don't ship it.")
            return [UserPrompt("double_sale", text, platform=sale.platform)]
        self.sold = sale
        for name, listing in self.listings.items():
            if name == sale.platform:
                listing.status = "sold"
            elif listing.status == "live":
                self.adapters[name].delist(listing)
                listing.status = "delisted"
        self.acceptable.clear()
        self.open_counters.clear()
        self.pending_confirmation = None
        self.log(f"SOLD on {sale.platform} for ${sale.price_cents / 100:.0f}; delisted everywhere else")
        return [UserPrompt("sold", f"Sold on {sale.platform} for ${sale.price_cents / 100:.0f}. Pack it and print the label.", platform=sale.platform)]

    def _maybe_drop(self, now: datetime) -> list[UserPrompt]:
        if self.last_price_change is None:
            return []
        days = (now - self.last_price_change).total_seconds() / 86400
        recent = self.last_offer_at is not None and (now - self.last_offer_at).total_seconds() < 86400 * 2
        for name, listing in self.listings.items():
            if listing.status != "live":
                continue
            drop = next_drop(listing.price_cents, effective_floor(self.terms, name), speed=self.terms.speed,
                             days_since_last_change=days, had_offers_recently=recent, platform=name)
            if drop:
                self.adapters[name].update_price(listing, drop.new_price_cents)
                self.log(f"[{name}] price drop to ${drop.new_price_cents / 100:.0f} ({drop.reason})")
                self.last_price_change = now
        return []
