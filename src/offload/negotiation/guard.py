"""Scam and off-platform detection on buyer messages, and checks on our own outgoing replies.

Rules, not a model: they must be predictable, and they run before any LLM ever sees the message.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_PATTERNS: list[tuple[str, str, re.Pattern[str]]] = [
    # (flag, severity, pattern)
    ("off_platform_payment", "block", re.compile(r"\b(zelle|venmo|cash ?app|cashapp|apple ?pay|wire transfer|western union|moneygram|bitcoin|btc|crypto|usdt|paypal (f&f|friends))\b", re.I)),
    ("verification_code", "block", re.compile(r"\b(verification|verify|security|confirmation) code\b|\bgoogle voice\b|\b6[- ]digit code\b", re.I)),
    ("move_off_platform", "block", re.compile(r"\b(whats ?app|telegram|signal|text me|call me|email me|dm me on|my number is|outside (the )?app)\b", re.I)),
    ("courier_pickup", "block", re.compile(r"\b(my (courier|shipper|agent|mover)|courier will (pick|collect)|i'?ll send (a|my) (courier|driver))\b", re.I)),
    ("overpayment", "block", re.compile(r"\b(overpa(y|id)|send (back|me) the (difference|extra)|refund the extra|cashier'?s check|certified check)\b", re.I)),
    ("fake_payment_notice", "block", re.compile(r"\b(payment (is )?(pending|on hold)|upgrade (to|your) (a )?business account|check your email for (the )?payment)\b", re.I)),
    ("link", "warn", re.compile(r"https?://|www\.|\b[a-z0-9-]+\.(com|net|org|io|ly|link|app|me)\b", re.I)),
    ("email_address", "warn", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b")),
    ("phone_number", "warn", re.compile(r"(?<!\d)(\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}(?!\d)")),
    ("ship_elsewhere", "warn", re.compile(r"\b(ship (it )?to (my|a) (friend|cousin|son|daughter|address abroad)|different address|overseas)\b", re.I)),
]


@dataclass(frozen=True)
class GuardResult:
    flags: tuple[str, ...]
    block: bool

    @property
    def clean(self) -> bool:
        return not self.flags


def check_buyer_message(text: str) -> GuardResult:
    flags, block = [], False
    for flag, severity, pattern in _PATTERNS:
        if pattern.search(text or ""):
            flags.append(flag)
            block = block or severity == "block"
    return GuardResult(tuple(flags), block)


def check_outgoing(text: str, expected_amount_cents: int | None) -> list[str]:
    """Problems with a reply we're about to send. Any problem -> fall back to the template reply."""
    problems = []
    for flag, _, pattern in _PATTERNS:
        if pattern.search(text):
            problems.append(f"contains {flag}")
    amounts = {round(float(m.replace(",", "")) * 100) for m in re.findall(r"\$\s?(\d[\d,]*(?:\.\d{2})?)", text)}
    if expected_amount_cents is None and amounts:
        problems.append("mentions a price when no price was decided")
    if expected_amount_cents is not None and amounts and amounts != {expected_amount_cents}:
        problems.append(f"mentions {sorted(amounts)} but the decided price is {expected_amount_cents}")
    return problems
