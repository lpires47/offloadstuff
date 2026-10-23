"""Decide what to do with one offer. Deterministic: the model never decides a price.

Zones, by offer amount (gross, per platform):

    lowball      < list × lowball_ratio                -> decline (quietly)
    below        < floor × (1 - ask_seller_band)        -> counter once from our ask, else decline
    ask_seller   [floor × (1 - band), floor)            -> escalate: the seller decides (big drop)
    negotiate    [floor, accept_at)                     -> counter, conceding toward the offer;
                                                           accept when rounds are used up
    accept       >= accept_at                           -> accept

Counters never go below the floor, never go up after we've come down, and never ask less than the
buyer already offered.
"""

from __future__ import annotations

from .fees import gross_for_net, net_payout
from .guard import check_buyer_message
from .models import Decision, Offer, Terms, Thread

# Share of the gap (our ask - their offer) we give up per counter round.
CONCESSION = {
    "most": (0.25, 0.40),
    "balanced": (0.35, 0.50),
    "fast": (0.50, 0.65),
}


def round_price(cents: float) -> int:
    dollars = cents / 100
    step = 5 if dollars >= 200 else 1
    return int(round(dollars / step) * step * 100)


def effective_floor(terms: Terms, platform: str) -> int:
    """The floor as an item price on `platform`."""
    if terms.floor_basis == "gross":
        return terms.floor_cents
    target_net = net_payout(terms.reference_platform, terms.floor_cents)
    return gross_for_net(platform, target_net)


def decide(offer: Offer, terms: Terms, thread: Thread, *, current_ask_cents: int | None = None) -> Decision:
    ask = current_ask_cents if current_ask_cents is not None else terms.list_cents
    floor = effective_floor(terms, offer.platform)
    amount = offer.amount_cents

    guard = check_buyer_message(offer.message)
    if guard.block:
        return Decision("decline", offer.id, None, "message asks to move payment or contact off-platform", guard.flags)

    if thread.closed:
        return Decision("ignore", offer.id, None, "thread closed")

    if amount >= max(floor, min(terms.accept_at, ask)):
        return Decision("accept", offer.id, amount, "at or above the auto-accept price", guard.flags)

    if amount < round(terms.list_cents * terms.lowball_ratio):
        return Decision("decline", offer.id, None, "lowball: under the minimum share of list", guard.flags)

    if amount < round(floor * (1 - terms.ask_seller_band)):
        if thread.rounds == 0:
            counter = _counter(ask, amount, floor, terms, thread)
            return Decision("counter", offer.id, counter, "well under the floor: one counter from our ask", guard.flags)
        return Decision("decline", offer.id, None, "still well under the floor after a counter", guard.flags)

    if amount < floor:
        return Decision(
            "escalate", offer.id, amount, "just under your minimum: your call", guard.flags, needs_seller=True
        )

    # Negotiation zone: floor <= amount < accept_at.
    if thread.rounds >= terms.max_counter_rounds:
        return Decision("accept", offer.id, amount, "counter rounds used up and offer is above the floor", guard.flags)
    counter = _counter(ask, amount, floor, terms, thread)
    if counter <= amount:
        return Decision("accept", offer.id, amount, "our counter would not beat their offer", guard.flags)
    return Decision("counter", offer.id, counter, f"counter round {thread.rounds + 1}", guard.flags)


def _counter(ask: int, amount: int, floor: int, terms: Terms, thread: Thread) -> int:
    shares = CONCESSION[terms.speed]
    share = shares[min(thread.rounds, len(shares) - 1)]
    start = thread.our_last_counter if thread.our_last_counter is not None else ask
    counter = round_price(start - (start - amount) * share)
    counter = max(counter, floor, amount + 100)  # never below floor, always above their offer
    if thread.our_last_counter is not None:
        counter = min(counter, thread.our_last_counter)  # never go back up
    return min(counter, ask)


def record(thread: Thread, offer: Offer, decision: Decision) -> Thread:
    """Update thread state after acting on a decision."""
    thread.their_last_offer = offer.amount_cents
    thread.history.append(("buyer", offer.amount_cents))
    if decision.action == "counter" and decision.amount_cents is not None:
        thread.our_last_counter = decision.amount_cents
        thread.rounds += 1
        thread.history.append(("us", decision.amount_cents))
    if decision.action == "accept":
        thread.closed = True  # a decline leaves the door open: the buyer can come back higher
    return thread
