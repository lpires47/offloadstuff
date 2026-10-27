"""Pricing engine v1: each piece of market evidence moves the answer the way the research says it should."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from offload.pricing.engine import (
    Engagement,
    ItemFacts,
    MarketState,
    Observation,
    Offer,
    daily_hazard,
    next_step,
    nice,
    value,
)

TODAY = date(2026, 10, 26)


def jacket(**kw) -> ItemFacts:
    base = dict(segment="fashion", condition="very_good", retail_cents=59800, season_family="outerwear")
    base.update(kw)
    return ItemFacts(**base)


def sold(price, days_ago=10, platform="mercari", sim=1.0, condition="very_good", **kw):
    return Observation(price, "sold", platform, sim, condition, observed_on=TODAY - timedelta(days=days_ago), **kw)


def comps(center=20000, n=8):
    return [sold(center + (i - n // 2) * 800, days_ago=5 * i) for i in range(n)]


def test_value_tracks_exact_sales_and_is_tier_a():
    v = value(jacket(), comps(), today=TODAY)
    assert v.tier == "A" and v.confidence in ("high", "medium")
    assert 18500 <= v.value_cents <= 21500
    lo, hi = v.range_cents
    assert lo < v.value_cents < hi
    b = v.best
    assert b.floor_cents <= b.auto_accept_cents <= b.list_cents


def test_long_unsold_asks_pull_value_down():
    base = value(jacket(retail_cents=None), comps(n=3), today=TODAY)
    stale = [Observation(26000, "expired", "mercari", 1.0, "very_good", days_listed=90) for _ in range(6)]
    v = value(jacket(retail_cents=None), comps(n=3) + stale, today=TODAY)
    assert v.value_cents < base.value_cents
    fresh = [Observation(26000, "active", "mercari", 1.0, "very_good", days_listed=1) for _ in range(6)]
    v_fresh = value(jacket(retail_cents=None), comps(n=3) + fresh, today=TODAY)
    assert v.value_cents < v_fresh.value_cents  # a 1-day-old ask says almost nothing


def test_offers_are_lower_bounds():
    without = value(jacket(), comps(n=2), today=TODAY)
    with_offer = value(jacket(), comps(n=2), offers=[Offer(26000, "poshmark")], today=TODAY)
    assert with_offer.value_cents > without.value_cents


def test_condition_and_poshmark_list_price_normalization():
    good = value(jacket(condition="good"), comps(), today=TODAY)
    vg = value(jacket(), comps(), today=TODAY)
    assert good.value_cents < vg.value_cents
    posh = [sold(20000 + i * 100, platform="poshmark", sold_price_is_list=True) for i in range(8)]
    assert value(jacket(retail_cents=None), posh, today=TODAY).value_cents < 19000  # list, not paid


def test_supply_and_demand_change_speed():
    tight = value(jacket(), comps(), market=MarketState(active_count=5, sold_last_90d=30), today=TODAY)
    glut = value(jacket(), comps(), market=MarketState(active_count=120, sold_last_90d=10), today=TODAY)
    assert tight.p_sold[30] > glut.p_sold[30]
    assert any("months of supply" in d for d in glut.drivers)
    hot = value(jacket(), comps(), market=MarketState(search_trend=1.5), today=TODAY)
    assert hot.p_sold[30] > value(jacket(), comps(), today=TODAY).p_sold[30]


def test_seasonality():
    winter = value(jacket(), comps(), market=MarketState(month=11), today=TODAY)
    summer = value(jacket(), comps(), market=MarketState(month=6), today=TODAY)
    assert winter.p_sold[30] > summer.p_sold[30]


def test_speed_trades_price_for_time():
    fast = value(jacket(), comps(), speed="fast", today=TODAY)
    most = value(jacket(), comps(), speed="most", today=TODAY)
    f = next(p for p in fast.plans if p.platform == "mercari")
    m = next(p for p in most.plans if p.platform == "mercari")
    assert f.list_cents < m.list_cents and f.floor_cents < m.floor_cents


def test_platform_fees_and_fit():
    v = value(ItemFacts(segment="furniture", condition="good", retail_cents=150000,
                        platforms=["fbm_local", "chairish", "poshmark", "ebay"]), [], today=TODAY)
    names = [p.platform for p in v.plans]
    assert "poshmark" not in names  # furniture buyers aren't there
    assert v.tier == "C" and v.confidence == "low"


def test_overpricing_costs_time():
    at = daily_hazard(0.0, 0.0, 0.01, 5.0)
    over = daily_hazard(0.2, 0.0, 0.01, 5.0)
    under = daily_hazard(-0.2, 0.0, 0.01, 5.0)
    assert under > at > over and at == pytest.approx(0.01)


def test_round_numbers_only_when_impatient():
    assert nice(20000, patient=True) == 19500 or nice(20000, patient=True) % 1000 != 0
    assert nice(4000, patient=True) == 3900
    assert nice(4000, patient=False) == 4000


def test_no_evidence_is_an_error_not_a_guess():
    with pytest.raises(ValueError):
        value(jacket(retail_cents=None), [], today=TODAY)


def test_next_step_order():
    facts = jacket()
    low_views = Engagement(days_listed=7, views=5, current_ask_cents=30000)
    assert next_step(facts, comps(), low_views, "mercari", today=TODAY).action == "fix_listing"
    liked = Engagement(days_listed=10, views=200, likes=6, current_ask_cents=30000)
    step = next_step(facts, comps(), liked, "mercari", today=TODAY)
    assert step.action == "private_offer" and step.price_cents < 30000
    nobody = Engagement(days_listed=14, views=200, likes=0, current_ask_cents=30000)
    assert next_step(facts, comps(), nobody, "mercari", today=TODAY).action == "price_drop"
    fair = Engagement(days_listed=3, views=40, current_ask_cents=20500)
    assert next_step(facts, comps(), fair, "mercari", today=TODAY).action == "hold"
