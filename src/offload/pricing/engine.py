"""Pricing engine v1: what an item will sell for, how fast, and where, from the market as it is today.

This implements the design in the Pricing tab (docs/research/pricing.md):

  identity tier -> market observations (sold, unsold, active; normalized) -> a posterior over the
  item's market value -> supply/demand -> a daily chance-of-sale curve per platform -> the list price,
  hidden minimum, auto-accept, expected price, range and days to sell that maximize what the seller
  takes home at their pace -> updates as views, likes, offers and unsold days come in.

The value model is a small Bayesian grid over log(value), so every kind of evidence counts in the
same currency:
  * a sold comp is a noisy measurement of value (noisier the less similar it is);
  * an unsold listing that sat d days at ask A is evidence the ask was above value, more so the
    longer it sat (right-censored, through the same sale-hazard curve we use to plan);
  * an offer of O means at least one buyer values it at O or more (a lower bound);
  * the prior is the hierarchy: retail x condition x category when we know retail, else similar items.

Constants marked [estimate] are priors from the research, to be refit from our own telemetry
(every listing we operate logs price shown, price changes, views, likes, offers and the outcome).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date
from typing import Literal

from ..negotiation.fees import FEES, gross_for_net, net_payout

Status = Literal["sold", "active", "expired"]
Speed = Literal["fast", "balanced", "most"]
Tier = Literal["A", "B", "C", "D"]

# ---------- priors [estimate] ----------

# Value relative to "very good", by condition, per category family. Mercari Japan measured -11% and
# -24% for two levels of scratches; luxury and sneakers hold "new" premiums more steeply.
CONDITION = {
    "default": {"new_with_tags": 1.30, "new_without_tags": 1.18, "like_new": 1.10, "very_good": 1.00,
                "good": 0.87, "fair": 0.68, "poor": 0.42, "unknown": 0.92},
    "sneakers": {"new_with_tags": 1.55, "new_without_tags": 1.40, "like_new": 1.15, "very_good": 1.00,
                 "good": 0.82, "fair": 0.62, "poor": 0.38, "unknown": 0.90},
    "furniture": {"new_with_tags": 1.25, "new_without_tags": 1.20, "like_new": 1.12, "very_good": 1.00,
                  "good": 0.88, "fair": 0.72, "poor": 0.45, "unknown": 0.92},
}
# Share of current retail a "very good" item fetches, by segment (Vinted and resale-guide ranges).
RETAIL_SHARE = {"fashion": 0.38, "menswear": 0.40, "luxury": 0.55, "sneakers": 0.60,
                "furniture": 0.42, "decor": 0.35, "general": 0.35}
# Share of listings at market value that sell within 90 days, when we can't measure it.
BASE_SELL_THROUGH_90 = {"fashion": 0.35, "menswear": 0.40, "luxury": 0.40, "sneakers": 0.55,
                        "furniture": 0.30, "decor": 0.30, "general": 0.30}
# How sharply the daily chance of sale falls as the ask rises above value (log units).
ELASTICITY = {"default": 8.0, "sneakers": 10.0, "luxury": 6.0, "furniture": 5.0}
# Remaining item-level noise after comps, by identity tier (log units; Xianyu's best is ~0.35 overall).
ITEM_SIGMA = {"A": 0.12, "B": 0.20, "C": 0.30, "D": 0.42}

# Per-platform behavior [estimate]: typical sale/list ratio given offer culture, and how well the
# platform's buyers fit each segment (multiplies the chance of sale).
OFFER_RATIO = {"poshmark": 0.82, "mercari": 0.90, "depop": 0.90, "ebay": 0.92, "grailed": 0.88,
               "vinted": 0.88, "fbm_local": 0.85, "fbm_shipped": 0.88, "offload": 0.92,
               "chairish": 0.86, "1stdibs": 0.85, "kaiyo": 0.90, "aptdeco": 0.88}
AUDIENCE = {
    "fashion": {"poshmark": 1.0, "depop": 0.9, "mercari": 0.8, "ebay": 0.9, "vinted": 0.7, "grailed": 0.3,
                "fbm_shipped": 0.3, "fbm_local": 0.4, "offload": 0.5},
    "menswear": {"grailed": 1.0, "ebay": 0.9, "poshmark": 0.6, "depop": 0.7, "mercari": 0.6, "offload": 0.5},
    "luxury": {"ebay": 0.8, "poshmark": 0.8, "grailed": 0.5, "mercari": 0.4, "offload": 0.5},
    "sneakers": {"ebay": 1.0, "grailed": 0.8, "mercari": 0.7, "poshmark": 0.5, "depop": 0.6, "offload": 0.5},
    "furniture": {"fbm_local": 1.0, "chairish": 0.9, "1stdibs": 0.6, "kaiyo": 0.7, "aptdeco": 0.7,
                  "ebay": 0.4, "offload": 0.5},
    "decor": {"chairish": 0.9, "ebay": 0.8, "etsy": 0.8, "fbm_local": 0.7, "mercari": 0.6, "offload": 0.5},
    "general": {"ebay": 1.0, "mercari": 0.8, "fbm_local": 0.8, "poshmark": 0.5, "offload": 0.5},
}
# Daily patience discount by seller pace: "fast" values a sale today far above one next month.
PATIENCE = {"fast": 0.008, "balanced": 0.0025, "most": 0.0007}  # ~21%, ~7%, ~2% a month
HORIZON_DAYS = 90

# Seasonality multipliers on the chance of sale, by month (1-12). Coats in autumn, swim in spring.
SEASON = {
    "outerwear": [1.2, 1.0, 0.8, 0.7, 0.6, 0.6, 0.6, 0.8, 1.1, 1.3, 1.4, 1.3],
    "swim": [0.6, 0.7, 0.9, 1.1, 1.4, 1.5, 1.4, 1.1, 0.8, 0.6, 0.5, 0.6],
    "default": [1.0] * 12,
}


# ---------- inputs ----------


@dataclass
class Observation:
    """One listing in the market for this item or something like it."""

    price_cents: int
    status: Status  # sold (price is a sale), active (still listed), expired (delisted unsold)
    platform: str
    similarity: float  # 1.0 exact item, ~0.7 same model other variant, ~0.4 similar piece
    condition: str = "unknown"
    days_listed: float | None = None  # for active/expired: how long it sat; for sold: time to sell
    observed_on: date | None = None  # sale date, or the day we saw it
    shipping_cents: int | None = None  # what the buyer paid for shipping (0 = free shipping)
    sold_price_is_list: bool = False  # Poshmark and eBay Best Offer show list, not accepted, price
    likes: int | None = None
    url: str | None = None
    title: str = ""


@dataclass
class Offer:
    amount_cents: int
    platform: str
    accepted: bool = False


@dataclass
class MarketState:
    """Supply and demand for this item's cluster. Any field may be unknown."""

    active_count: int | None = None  # live listings of the exact item (or model)
    sold_last_90d: int | None = None
    new_listings_last_30d: int | None = None
    search_trend: float | None = None  # this month's search interest / trailing-year average
    retail_on_sale: bool = False  # the new item is currently discounted, which caps resale
    month: int | None = None

    @property
    def sell_through_90(self) -> float | None:
        if self.active_count is None or self.sold_last_90d is None:
            return None
        total = self.active_count + self.sold_last_90d
        return self.sold_last_90d / total if total else None

    @property
    def months_of_supply(self) -> float | None:
        if self.active_count is None or not self.sold_last_90d:
            return None
        return self.active_count / (self.sold_last_90d / 3)


@dataclass
class ItemFacts:
    segment: str  # router segment: fashion, menswear, luxury, sneakers, furniture, decor, general
    condition: str
    tier_hint: Tier | None = None
    retail_cents: int | None = None
    season_family: str = "default"  # outerwear, swim, default
    complete: bool = True  # tags/box/dust bag present when they matter
    authenticated: bool = False
    platforms: list[str] = field(default_factory=lambda: ["ebay", "poshmark", "mercari", "depop", "offload"])


# ---------- outputs ----------


@dataclass
class PlatformPlan:
    platform: str
    list_cents: int
    floor_cents: int  # hidden minimum: accepting this now beats waiting
    auto_accept_cents: int  # offers at or above this are accepted without asking
    expected_sale_cents: int
    expected_net_cents: int
    p_sold_30: float


@dataclass
class Valuation:
    tier: Tier
    value_cents: int  # posterior median market value in this item's condition
    range_cents: tuple[int, int]  # 80% range for the sale price
    p_sold: dict[int, float]  # day -> chance sold by then, listing everywhere at the plan
    median_days: float | None
    plans: list[PlatformPlan]  # best platform first
    speed: Speed
    confidence: Literal["high", "medium", "low"]
    drivers: list[str]  # plain-language reasons, shown to the seller
    evidence: dict[str, int]  # counts of each kind of evidence used
    flags: list[str] = field(default_factory=list)

    @property
    def best(self) -> PlatformPlan:
        return self.plans[0]


# ---------- the model ----------

GRID = 241  # log-value grid points
SPAN = 1.6  # grid covers prior_mu +/- SPAN (about x0.2 .. x5)


def _family(segment: str) -> str:
    return segment if segment in ("sneakers", "furniture") else "default"


def condition_factor(segment: str, condition: str) -> float:
    table = CONDITION.get(_family(segment), CONDITION["default"])
    return table.get(condition, table["unknown"])


def daily_hazard(ask_log: float, value_log: float, base: float, elasticity: float) -> float:
    """Chance of selling on a given day at this ask. `base` is the rate when ask == value.
    Below value it rises toward 2x base; above value it falls off with `elasticity`."""
    return min(0.9, base * 2.0 / (1.0 + math.exp(elasticity * (ask_log - value_log))))


def base_rate(facts: ItemFacts, market: MarketState) -> tuple[float, list[str]]:
    """Daily chance of sale at market value, from supply and demand."""
    notes = []
    st = market.sell_through_90
    if st is not None and st > 0:
        st = min(max(st, 0.03), 0.95)
        notes.append(f"{round(st * 100)}% of listings like this sold in the last 90 days")
    else:
        st = BASE_SELL_THROUGH_90.get(facts.segment, 0.3)
    rate = 1 - (1 - st) ** (1 / 90)
    mos = market.months_of_supply
    if mos is not None:
        notes.append(f"about {mos:.1f} months of supply listed right now")
    if market.new_listings_last_30d is not None and market.sold_last_90d:
        inflow = market.new_listings_last_30d / max(market.sold_last_90d / 3, 1)
        if inflow > 1.3:
            rate *= 0.85
            notes.append("new listings are arriving faster than they sell")
        elif inflow < 0.7:
            rate *= 1.1
            notes.append("supply is thinning")
    if market.search_trend is not None:
        trend = min(max(market.search_trend, 0.6), 1.6)
        rate *= trend ** 0.5
        if abs(trend - 1) > 0.1:
            notes.append(f"search interest is {'up' if trend > 1 else 'down'} {abs(round((trend - 1) * 100))}% vs the year")
    if market.month:
        s = SEASON.get(facts.season_family, SEASON["default"])[market.month - 1]
        rate *= s
        if abs(s - 1) > 0.1:
            notes.append(f"{'in' if s > 1 else 'out of'} season")
    return rate, notes


def _normalize(o: Observation, facts: ItemFacts) -> float:
    """An observation's price, in this item's condition, as an item-only price (log)."""
    price = o.price_cents
    if o.shipping_cents == 0:
        price -= 0.8 * _typical_shipping(facts.segment)  # sellers fold ~80% of shipping into price
    if o.status == "sold" and o.sold_price_is_list:
        price *= OFFER_RATIO.get(o.platform, 0.9)  # shown price is the ask, not what was paid
    adj = condition_factor(facts.segment, facts.condition) / condition_factor(facts.segment, o.condition)
    return math.log(max(price * adj, 100))


def _typical_shipping(segment: str) -> int:
    return {"furniture": 9000, "decor": 1500, "sneakers": 1400}.get(segment, 800)


def _recency(o: Observation, today: date) -> float:
    if o.observed_on is None:
        return 1.0
    age = (today - o.observed_on).days
    return math.exp(-max(age, 0) / 180)  # half weight at ~4 months


def infer_tier(facts: ItemFacts, obs: list[Observation]) -> Tier:
    if facts.tier_hint:
        return facts.tier_hint
    exact = [o for o in obs if o.similarity >= 0.9]
    exact_sold = [o for o in exact if o.status == "sold"]
    if len(exact_sold) >= 5 or len(exact) >= 10:
        return "A"
    if len(exact) >= 3 or len([o for o in obs if o.similarity >= 0.65]) >= 5:
        return "B"
    if facts.retail_cents or obs:
        return "C"
    return "D"


def value_posterior(
    facts: ItemFacts,
    obs: list[Observation],
    offers: list[Offer],
    market: MarketState,
    *,
    today: date | None = None,
) -> tuple[list[float], list[float], dict[str, int], list[str]]:
    """Grid posterior over log(value). Returns (grid, probs, evidence counts, notes)."""
    today = today or date.today()
    notes: list[str] = []
    elasticity = ELASTICITY.get(_family(facts.segment), ELASTICITY["default"])
    rate, _ = base_rate(facts, market)

    # Prior: retail x share x condition, else the similarity-weighted middle of what we see.
    if facts.retail_cents:
        share = RETAIL_SHARE.get(facts.segment, 0.35)
        if market.retail_on_sale:
            share *= 0.85
            notes.append("the new item is on sale right now, which caps resale")
        mu0 = math.log(facts.retail_cents * share * condition_factor(facts.segment, facts.condition))
        sd0 = 0.45
    elif obs:
        w = [o.similarity for o in obs]
        mu0 = sum(wi * _normalize(o, facts) for wi, o in zip(w, obs)) / sum(w)
        sd0 = 0.6
    else:
        raise ValueError("no comps and no retail price: ask the seller, or use an auction with a reserve")

    grid = [mu0 - SPAN + 2 * SPAN * i / (GRID - 1) for i in range(GRID)]
    logp = [-0.5 * ((g - mu0) / sd0) ** 2 for g in grid]
    counts = {"sold": 0, "unsold": 0, "active": 0, "offers": 0}

    for o in obs:
        x = _normalize(o, facts)
        weight = o.similarity ** 2 * _recency(o, today)
        if weight < 0.02:
            continue
        if o.status == "sold":
            # Less similar comps are noisier measurements of this item's value.
            sd = 0.12 + 0.45 * (1 - o.similarity)
            for i, g in enumerate(grid):
                logp[i] += weight * -0.5 * ((x - g) / sd) ** 2
            counts["sold"] += 1
        else:
            # Sat d days at ask x without selling: likely if the ask was above value. Buyers pay
            # roughly ask x the platform's offer ratio, so that is the price the hazard sees.
            # Unknown age: treat as a week, a weak upper bound with no outcome yet.
            days = min(o.days_listed if o.days_listed is not None else 7, 120)
            closing = x + math.log(OFFER_RATIO.get(o.platform, 0.9))
            for i, g in enumerate(grid):
                h = daily_hazard(closing, g, rate, elasticity)
                logp[i] += weight * days * math.log1p(-h)
            counts["unsold" if o.status == "expired" else "active"] += 1

    for off in offers:
        # At least one buyer values the item at the offer or more (soft lower bound).
        x = math.log(off.amount_cents)
        for i, g in enumerate(grid):
            logp[i] += math.log(1 / (1 + math.exp(-(g - x) / 0.08)) + 1e-9)
        counts["offers"] += 1

    top = max(logp)
    probs = [math.exp(v - top) for v in logp]
    z = sum(probs)
    return grid, [p / z for p in probs], counts, notes


def _quantile(grid: list[float], probs: list[float], q: float) -> float:
    acc = 0.0
    for g, p in zip(grid, probs):
        acc += p
        if acc >= q:
            return g
    return grid[-1]


def nice(cents: float, patient: bool) -> int:
    """Whole dollars, $5 steps over $200. Patient sellers avoid round numbers: those sell faster but
    for 5-8% less, because buyers read them as impatience (NBER, 2015)."""
    dollars = cents / 100
    if dollars >= 200:
        v = round(dollars / 5) * 5
        return int((v - 1 if patient and v % 10 == 0 else v) * 100)
    v = max(1, round(dollars))
    return int((v - 1 if patient and v % 10 == 0 and v > 10 else v) * 100)


def _plan_platform(
    platform: str,
    facts: ItemFacts,
    grid: list[float],
    probs: list[float],
    base: float,
    speed: Speed,
) -> tuple[tuple, list[float]] | None:
    fit = AUDIENCE.get(facts.segment, AUDIENCE["general"]).get(platform)
    if not fit or platform not in FEES:
        return None
    elasticity = ELASTICITY.get(_family(facts.segment), ELASTICITY["default"])
    ratio = OFFER_RATIO.get(platform, 0.9)
    rho = PATIENCE[speed]
    median = _quantile(grid, probs, 0.5)
    # Thin the posterior for speed: 25 points carry the shape well enough.
    step = max(1, len(grid) // 25)
    pts = [(grid[i], sum(probs[i : i + step])) for i in range(0, len(grid), step)]

    def score(ask_log: float) -> tuple[float, float, list[float]]:
        """Expected discounted net at this ask, averaged over our uncertainty about value."""
        sale = math.exp(ask_log) * ratio  # what it typically closes at after offers
        net = net_payout(platform, int(sale))
        ev, hs = 0.0, []
        for g, w in pts:
            h = daily_hazard(ask_log + math.log(ratio), g, base * fit, elasticity)
            q = (1 - h) * (1 - rho)
            # sum over all future days of P(first sale on day t) * discount^t (closed form). No fixed
            # horizon: an item unsold at day 90 isn't worthless, it keeps selling at a discount.
            ev += w * net * h * (1 - rho) / (1 - q)
            hs.append(h)
        return ev, net, hs

    best = max(((score(median + k * 0.01), median + k * 0.01) for k in range(-30, 61)), key=lambda x: x[0][0])
    (ev, net, hs), ask_log = best
    sale = math.exp(ask_log) * ratio
    curve = [sum(w * (1 - (1 - h) ** t) for (g, w), h in zip(pts, hs)) for t in range(HORIZON_DAYS + 1)]
    p30 = curve[30]
    return (ask_log, sale, net, p30, [w for _, w in pts], hs), curve


def _finish_plan(platform: str, ask_log: float, sale: float, net: int, p30: float, wait_net: float, speed: Speed) -> PlatformPlan:
    """Hidden minimum = what waiting is worth across every channel the item is listed on.
    Accepting less than that now loses money in expectation; accepting more beats waiting."""
    floor = gross_for_net(platform, max(int(wait_net), 100))
    patient = speed != "fast"
    list_c = nice(math.exp(ask_log), patient)
    floor_c = min(nice(floor, False), list_c)
    auto_c = max(floor_c, min(list_c, nice(sale, False)))
    return PlatformPlan(platform, list_c, floor_c, auto_c, int(sale), net, round(p30, 3))


def value(
    facts: ItemFacts,
    obs: list[Observation],
    *,
    market: MarketState | None = None,
    offers: list[Offer] | None = None,
    speed: Speed = "balanced",
    today: date | None = None,
) -> Valuation:
    market = market or MarketState()
    offers = offers or []
    today = today or date.today()
    if market.month is None:
        market.month = today.month
    tier = infer_tier(facts, obs)
    grid, probs, counts, notes = value_posterior(facts, obs, offers, market, today=today)

    # Predictive spread = uncertainty about value + item-level noise for this tier.
    q10, q50, q90 = (_quantile(grid, probs, q) for q in (0.1, 0.5, 0.9))
    post_sd = (q90 - q10) / 2.563
    sd = math.sqrt(post_sd**2 + ITEM_SIGMA[tier] ** 2)
    lo, hi = math.exp(q50 - 1.2816 * sd), math.exp(q50 + 1.2816 * sd)

    base, market_notes = base_rate(facts, market)
    raw, curves = {}, {}
    for p in facts.platforms:
        out = _plan_platform(p, facts, grid, probs, base, speed)
        if out:
            raw[p], curves[p] = out
    if not raw:
        raise ValueError(f"none of {facts.platforms} suit {facts.segment}")
    # Value of waiting, listed everywhere at the planned asks: each day, any platform may sell it.
    rho = PATIENCE[speed]
    weights = next(iter(raw.values()))[4]
    wait = 0.0
    for j, w in enumerate(weights):
        hs = {p: r[5][j] for p, r in raw.items()}
        h_any = 1 - math.prod(1 - h for h in hs.values())
        avg_net = sum(hs[p] * raw[p][2] for p in hs) / max(sum(hs.values()), 1e-9)
        q = (1 - h_any) * (1 - rho)
        wait += w * avg_net * h_any * (1 - rho) / (1 - q)
    plans = [_finish_plan(p, r[0], r[1], r[2], r[3], wait, speed) for p, r in raw.items()]
    plans.sort(key=lambda pl: -pl.expected_net_cents * (0.5 + pl.p_sold_30))

    # Listed everywhere at once: sold by day t unless it survives on every platform.
    p_sold = {}
    for day in (7, 30, 60, 90):
        survive = 1.0
        for p in curves:
            survive *= 1 - curves[p][day]
        p_sold[day] = round(1 - survive, 3)
    median_days = None
    survive_all = [1.0] * (HORIZON_DAYS + 1)
    for p in curves:
        for t in range(HORIZON_DAYS + 1):
            survive_all[t] *= 1 - curves[p][t]
    for t, s in enumerate(survive_all):
        if s <= 0.5:
            median_days = float(t)
            break

    width = (hi - lo) / math.exp(q50)
    confidence = "high" if tier == "A" and width < 0.5 else "medium" if tier in "AB" and width < 0.9 else "low"
    drivers = []
    if counts["sold"]:
        drivers.append(f"{counts['sold']} recent sales of this item or close matches")
    if counts["unsold"] + counts["active"]:
        drivers.append(f"{counts['unsold'] + counts['active']} listings that haven't sold at their asks")
    if counts["offers"]:
        drivers.append(f"{counts['offers']} offers received")
    if facts.retail_cents:
        drivers.append(f"retail ${facts.retail_cents / 100:,.0f}, adjusted for condition ({facts.condition.replace('_', ' ')})")
    drivers += notes + market_notes
    flags = []
    if not facts.complete and facts.segment in ("luxury", "sneakers"):
        flags.append("Missing box, tags or dust bag usually costs 10-20% here")
    if tier == "D":
        flags.append("No close comps: consider an auction with a reserve at the hidden minimum")
    return Valuation(
        tier=tier,
        value_cents=int(math.exp(q50)),
        range_cents=(int(lo), int(hi)),
        p_sold=p_sold,
        median_days=median_days,
        plans=plans,
        speed=speed,
        confidence=confidence,
        drivers=drivers,
        evidence=counts,
        flags=flags,
    )


# ---------- after listing: what to do next ----------


@dataclass
class Engagement:
    days_listed: float
    views: int | None = None
    likes: int | None = None
    offers: list[Offer] = field(default_factory=list)
    current_ask_cents: int | None = None


EXPECTED_VIEWS_PER_DAY = {"fashion": 6, "menswear": 6, "luxury": 10, "sneakers": 12, "furniture": 8, "decor": 4,
                          "general": 5}  # [estimate] until our telemetry sets it per platform


@dataclass
class NextStep:
    action: Literal["hold", "private_offer", "fix_listing", "price_drop", "change_channel"]
    price_cents: int | None
    reason: str


def next_step(
    facts: ItemFacts,
    obs: list[Observation],
    engagement: Engagement,
    platform: str,
    *,
    market: MarketState | None = None,
    speed: Speed = "balanced",
    today: date | None = None,
) -> NextStep:
    """Re-value with what this listing has seen, then pick the gentlest action that helps.
    Order: private offers to likers, fix the listing, a public drop, then another channel."""
    own = Observation(
        price_cents=engagement.current_ask_cents or 0,
        status="active",
        platform=platform,
        similarity=1.0,
        condition=facts.condition,
        days_listed=engagement.days_listed,
    )
    evidence = obs + ([own] if engagement.current_ask_cents else [])
    v = value(facts, evidence, market=market, offers=engagement.offers, speed=speed, today=today)
    plan = next((p for p in v.plans if p.platform == platform), v.best)
    ask = engagement.current_ask_cents or plan.list_cents
    expected_views = EXPECTED_VIEWS_PER_DAY.get(facts.segment, 5) * engagement.days_listed
    if engagement.views is not None and engagement.days_listed >= 3 and engagement.views < 0.35 * expected_views:
        return NextStep("fix_listing", None, "Few people are seeing it: better photos and title before touching price")
    if ask <= plan.list_cents * 1.05:
        return NextStep("hold", None, "Still priced right for the market")
    if engagement.likes:
        return NextStep("private_offer", plan.auto_accept_cents,
                        f"{engagement.likes} people liked it: offer them a lower price privately first")
    if engagement.days_listed > 45 and plan.p_sold_30 < 0.25:
        return NextStep("change_channel", plan.list_cents, "Slow here: list where this kind of item sells faster")
    return NextStep("price_drop", plan.list_cents, "The market says the ask is above what buyers pay")
