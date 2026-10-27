"""What the seller actually takes home on each platform (US, as researched 2026-10-23).

These schedules change often; each has a source and an as-of date. Several are unverified because the
platform's help pages block automated reading. Re-check before relying on them for money movement.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

# Our success fee when we sell for the user on someone else's platform (Liselle, 2026-10-23).
AGENT_FEE_OTHER_PLATFORMS = 0.05


@dataclass(frozen=True)
class FeeSchedule:
    platform: str
    seller_fee: Callable[[int], int]  # item price cents -> platform's cut, cents
    source: str
    verified: bool
    is_ours: bool = False


def _pct(rate: float, fixed: int = 0) -> Callable[[int], int]:
    return lambda price: round(price * rate) + fixed


FEES: dict[str, FeeSchedule] = {
    "offload": FeeSchedule("offload", lambda p: 0, "our policy: buyer pays the fee", True, is_ours=True),
    "ebay": FeeSchedule(
        "ebay",
        lambda p: round(p * 0.136) + (40 if p > 1000 else 30),
        "https://www.ebay.com/help/selling/fees-credits-invoices/selling-fees?id=4822",
        True,
    ),
    "depop": FeeSchedule(
        "depop",
        _pct(0.033, 45),  # 0% selling fee; seller pays processing
        "https://depophelp.zendesk.com/hc/en-gb/articles/360001791127-Seller-fees-and-charges",
        True,
    ),
    "vinted": FeeSchedule("vinted", lambda p: 0, "https://www.vinted.com/help/342", True),
    "mercari": FeeSchedule("mercari", _pct(0.10), "https://www.mercari.com/us/help_center/article/2517/", True),
    "poshmark": FeeSchedule(
        "poshmark", lambda p: 295 if p < 1500 else round(p * 0.20), "unverified: press reports", False
    ),
    "fbm_shipped": FeeSchedule(
        "fbm_shipped", lambda p: max(80, round(p * 0.10)), "unverified: third-party reports", False
    ),
    "fbm_local": FeeSchedule("fbm_local", lambda p: 0, "unverified: third-party reports", False),
    "grailed": FeeSchedule("grailed", lambda p: round(p * 0.09) + round(p * 0.0349) + 49, "unverified", False),
    # Furniture and design platforms [estimate, 2026-10-26]: commissions vary by seller plan and price.
    "chairish": FeeSchedule(
        "chairish",
        lambda p: round(p * (0.30 if p <= 250000 else 0.20)),
        "https://support.chairish.com/hc/en-us/articles/115006460407 (plans 20-40%; Standard assumed)",
        False,
    ),
    "1stdibs": FeeSchedule("1stdibs", _pct(0.20), "unverified: seller commission varies by tier", False),
    "kaiyo": FeeSchedule("kaiyo", _pct(0.40), "unverified: consignment payout varies", False),
    "aptdeco": FeeSchedule("aptdeco", _pct(0.24), "unverified", False),
    "etsy": FeeSchedule("etsy", lambda p: round(p * 0.065) + round(p * 0.03) + 45, "unverified: 6.5% + 3% + $0.25 + $0.20 listing", False),
}


def platform_fee(platform: str, price_cents: int) -> int:
    return FEES[platform].seller_fee(price_cents)


def agent_fee(platform: str, price_cents: int) -> int:
    return 0 if FEES[platform].is_ours else round(price_cents * AGENT_FEE_OTHER_PLATFORMS)


def net_payout(platform: str, price_cents: int) -> int:
    """Item price minus the platform's cut and ours. Shipping is buyer-paid everywhere we sell."""
    return price_cents - platform_fee(platform, price_cents) - agent_fee(platform, price_cents)


def gross_for_net(platform: str, net_cents: int) -> int:
    """Smallest item price on `platform` that nets at least `net_cents`."""
    lo, hi = net_cents, net_cents * 2 + 1000
    while lo < hi:
        mid = (lo + hi) // 2
        if net_payout(platform, mid) >= net_cents:
            hi = mid
        else:
            lo = mid + 1
    return lo
