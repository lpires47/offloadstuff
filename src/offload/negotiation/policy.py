"""Decide what to do with one offer. Deterministic: the model never decides a price.

Zones, by offer amount (item price on that platform), checked from the top:

    accept       >= accept_at (never below the floor)  -> accept
    negotiate    [floor, accept_at)                     -> counter, conceding toward the offer;
                                                           accept when rounds are used up
    ask_seller   [floor × (1 - band), floor)            -> escalate: the seller decides (big drop)
    lowball      < list × lowball_ratio                 -> decline (quietly)
    below        everything else under the floor        -> counter once from our ask, else decline

Counters never go below the floor, never land exactly on it, never go up after we've come down,
and always ask more than the buyer offered.
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


def ceil_price(cents: float) -> int:
    """Round UP to the same price steps, so rounding can never take us under a bound."""
    step = 500 if cents >= 20000 else 100
    return int(-(-int(cents) // step) * step)


def effective_floor(terms: Terms, platform: str) -> int:
    """The hidden minimum as an item price on `platform`."""
    if terms.floor_basis == "gross":
        return terms.floor_cents
    target_net = net_payout(terms.reference_platform, terms.floor_cents)
    return gross_for_net(platform, target_net)


def platform_list_price(terms: Terms, platform: str) -> int:
    """List price on `platform`: never below that platform's floor. With a net floor, the list price is
    raised by the same logic so the seller takes home the same amount everywhere."""
    if terms.floor_basis == "gross":
        return terms.list_cents
    target_net = net_payout(terms.reference_platform, terms.list_cents)
    return max(ceil_price(gross_for_net(platform, target_net)), ceil_price(effective_floor(terms, platform)))


def decide(offer: Offer, terms: Terms, thread: Thread, *, current_ask_cents: int | None = None) -> Decision:
    floor = effective_floor(terms, offer.platform)
    ask = current_ask_cents if current_ask_cents is not None else platform_list_price(terms, offer.platform)
    ask = max(ask, floor)  # an ask under the floor would itself sell below the minimum
    amount = offer.amount_cents

    guard = check_buyer_message(offer.message)
    if guard.block:
        return Decision("decline", offer.id, None, "message asks to move payment or contact off-platform", guard.flags)

    if thread.closed:
        return Decision("ignore", offer.id, None, "thread closed")

    accept_at = max(floor, min(round(terms.accept_at * ask / max(terms.list_cents, 1)), ask))
    if amount >= accept_at:
        return Decision("accept", offer.id, amount, "at or above the auto-accept price", guard.flags)

    if amount >= floor:
        # Negotiation zone: floor <= amount < accept_at.
        if thread.rounds >= terms.max_counter_rounds:
            return Decision("accept", offer.id, amount, "counter rounds used up and offer is above the floor", guard.flags)
        counter = _counter(ask, amount, floor, terms, thread)
        if counter <= amount:
            return Decision("accept", offer.id, amount, "our counter would not beat their offer", guard.flags)
        return Decision("counter", offer.id, counter, f"counter round {thread.rounds + 1}", guard.flags)

    if amount >= round(floor * (1 - terms.ask_seller_band)):
        return Decision("escalate", offer.id, amount, "just under your minimum: your call", guard.flags, needs_seller=True)

    if amount < round(terms.list_cents * terms.lowball_ratio):
        return Decision("decline", offer.id, None, "lowball: under the minimum share of list", guard.flags)

    if thread.rounds == 0:
        counter = _counter(ask, amount, floor, terms, thread)
        return Decision("counter", offer.id, counter, "well under the floor: one counter from our ask", guard.flags)
    return Decision("decline", offer.id, None, "still well under the floor after a counter", guard.flags)


def _counter(ask: int, amount: int, floor: int, terms: Terms, thread: Thread) -> int:
    """A counter in [lower, upper], on a round price.

    lower: above their offer, and a little above the floor so a counter never lands exactly on
           (and so reveals) the hidden minimum.
    upper: our current ask, and never above our previous counter (we don't go back up).
    """
    shares = CONCESSION[terms.speed]
    share = shares[min(thread.rounds, len(shares) - 1)]
    start = thread.our_last_counter if thread.our_last_counter is not None else ask
    candidate = round_price(start - (start - amount) * share)
    floor_up = min(ceil_price(floor), max(ask, floor))  # round up, but never past our own ask
    upper = max(ask, floor_up)
    if thread.our_last_counter is not None:
        upper = max(min(upper, thread.our_last_counter), floor_up)
    lower = max(ceil_price(amount + 100), floor_up, min(ceil_price(floor * 1.03 + 100), upper))
    return min(max(candidate, lower), upper)


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
