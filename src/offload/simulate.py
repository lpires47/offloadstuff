"""A scripted multi-platform sale, end to end, with no network: shows the engine's decisions."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .listing.compose import ListingDraft
from .listing.shipping import package_for
from .negotiation.models import Terms
from .orchestrator import SellJob
from .posting.fake import FakePlatform, ScriptedBuyer


def demo_job(log=print) -> tuple[SellJob, dict[str, FakePlatform]]:
    draft = ListingDraft(
        title="Arc'teryx Atom LT Hoody Men's Size M Black",
        description="Arc'teryx Atom LT Hoody, very good condition.\nFlaws, shown in photos: pilling at both cuffs (minor).",
        category="apparel", subcategory="insulated jacket",
        attributes={"brand": "Arc'teryx", "model": "Atom LT Hoody", "size": "M", "gender": "Men's", "color": "black"},
        condition="very_good", package=package_for("apparel", 1.0),
        list_cents=14900, floor_cents=11500, expected_cents=13400,
    )
    platforms = {name: FakePlatform(name) for name in ("offload", "ebay", "depop", "poshmark", "fbm_shipped")}
    job = SellJob(draft, Terms(list_cents=14900, floor_cents=11500, speed="balanced"), platforms, photos=["hoody-1.jpg"], log=log)
    return job, platforms


def run_demo() -> None:
    t = datetime(2026, 10, 23, 9, 0, tzinfo=timezone.utc)
    job, p = demo_job()
    job.post(t)

    L = job.listings
    p["poshmark"].buyer_offers(L["poshmark"], ScriptedBuyer("closet_q", 6000, 6000), t)
    p["fbm_shipped"].buyer_offers(L["fbm_shipped"], ScriptedBuyer("mike_r", 14000, 14000, message="I'll pay with Zelle, send me your number"), t)
    p["ebay"].buyer_offers(L["ebay"], ScriptedBuyer("trailhead88", 9500, 13200, step_cents=1500), t)
    p["depop"].buyer_offers(L["depop"], ScriptedBuyer("vintagefinds", 11200, 11800, step_cents=300), t)

    for hour in range(0, 6):
        now = t + timedelta(hours=hour)
        for prompt in job.tick(now):
            print(f"  >> ASK/TELL SELLER [{prompt.kind}]: {prompt.text}")
            if prompt.kind == "confirm_sale" and prompt.offer:
                print("  << seller taps 'Sell it'")
                for after in job.confirm_sale(prompt.offer, now):
                    print(f"  >> TELL SELLER [{after.kind}]: {after.text}")
            if prompt.kind == "offer_below_minimum" and prompt.offer:
                print("  << seller taps 'Hold out'")
                job.answer_below_minimum(prompt.offer, accept=False, now=now)
        if job.sold:
            break
