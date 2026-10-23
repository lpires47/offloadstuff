"""Regression tests for the issues found in the first independent code review (2026-10-23)."""

from datetime import datetime, timedelta, timezone

import httpx
import pytest

from offload.images import Box
from offload.listing import compose_listing
from offload.llm import ScriptedLLM
from offload.negotiation.fees import net_payout
from offload.negotiation.messages import template, usd
from offload.negotiation.models import Decision, Offer, Terms, Thread
from offload.negotiation.policy import decide, effective_floor, platform_list_price
from offload.orchestrator import SellJob
from offload.posting.browser.adapter import BrowserAdapter, OfferMismatch
from offload.posting.browser.computer_use import NOT_EXECUTED, TaskResult, _host_allowed, _trim_screenshots
from offload.posting.ebay import EbayAdapter
from offload.posting.fake import ScriptedBuyer
from offload.posting.base import PlatformListing
from offload.pricing import estimate_price
from offload.simulate import demo_job
from offload.vision.pipeline import analyze_photo, assess
from offload.vision.schema import Dimensions

from .conftest import attr, detected, detection, make_ident

T0 = datetime(2026, 10, 23, 9, tzinfo=timezone.utc)


def off(cents, platform="ebay", buyer="b", message=""):
    return Offer(f"{platform}-{buyer}-{cents}", platform, buyer, cents, T0, message)


# 1, 2: net floors
def test_net_floor_counter_never_below_platform_floor_or_offer():
    terms = Terms(10000, 9500, floor_basis="net")
    floor = effective_floor(terms, "ebay")
    d = decide(off(10500), terms, Thread("ebay", "b"))
    assert d.action in ("counter", "escalate", "accept")
    if d.action == "counter":
        assert d.amount_cents >= floor and d.amount_cents > 10500
    assert d.action != "accept" or d.amount_cents >= floor


def test_net_floor_list_price_and_drops_respect_platform_floor():
    terms = Terms(10000, 9500, floor_basis="net")
    assert platform_list_price(terms, "ebay") >= effective_floor(terms, "ebay")
    assert net_payout("ebay", platform_list_price(terms, "ebay")) >= net_payout("offload", 10000)
    job, _ = demo_job(log=lambda s: None)
    job.terms = terms
    job.post(T0)
    job.tick(T0 + timedelta(days=30))
    for name, l in job.listings.items():
        assert l.price_cents >= effective_floor(terms, name)


# 3, 4: double sales
def test_confirm_after_sale_elsewhere_is_refused():
    job, p = demo_job(log=lambda s: None)
    job.post(T0)
    L = job.listings
    p["offload"].buyer_offers(L["offload"], ScriptedBuyer("o", 14500, 14500), T0)
    prompt = [x for x in job.tick(T0) if x.kind == "confirm_sale"][0]
    p["ebay"].buy_now(L["ebay"], "fast_buyer", T0)
    job.tick(T0 + timedelta(minutes=1))
    assert job.sold.platform == "ebay"
    again = job.confirm_sale(prompt.offer, T0 + timedelta(minutes=2))
    assert again[0].kind == "already_sold" and job.sold.platform == "ebay"


def test_second_simultaneous_sale_is_caught_and_cancelled():
    job, p = demo_job(log=lambda s: None)
    job.post(T0)
    L = job.listings
    p["ebay"].buy_now(L["ebay"], "a", T0)
    p["depop"].buy_now(L["depop"], "b", T0)
    kinds = [x.kind for x in job.tick(T0)]
    assert kinds.count("sold") == 1 and "double_sale" in kinds
    assert any("cancelled order" in line for line in p["depop"].log + p["ebay"].log)


def test_confirm_sale_delists_others_before_accepting():
    job, p = demo_job(log=lambda s: None)
    job.post(T0)
    L = job.listings
    p["offload"].buyer_offers(L["offload"], ScriptedBuyer("o", 14500, 14500), T0)
    prompt = [x for x in job.tick(T0) if x.kind == "confirm_sale"][0]
    job.confirm_sale(prompt.offer, T0)
    assert all(l.status == "delisted" for n, l in L.items() if n != "offload")


# 5, 6: computer-use enforcement (no browser needed: fake page + executor)
class FakePage:
    url = "https://www.depop.com/x"
    context = None

    def on(self, *a):
        pass

    def goto(self, url):
        self.url = url


class FakeExecutor:
    def __init__(self):
        self.ran = []

    def screenshot_png(self):
        return b"\x89PNG"

    def _image_block(self, png):
        return {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": ""}}

    def run(self, name, args):
        if args.get("fail"):
            raise RuntimeError("boom")
        self.ran.append(name)
        return [{"type": "text", "text": "OK"}]


def _runner(llm, approve=lambda s: False):
    from offload.posting.browser.computer_use import ComputerUseRunner

    r = ComputerUseRunner(llm, FakePage(), approve=approve, executor=FakeExecutor())
    r._install_guards = lambda task, blocked: None
    return r


def _task(**kw):
    from offload.posting.browser.tasks import BrowserTask

    return BrowserTask("depop", "x", "g", {}, "{}", None, ("depop.com",), **kw)


def test_declined_approval_stops_the_rest_of_the_batch():
    from .conftest import computer, response, tool

    llm = ScriptedLLM(create_responses=[
        response(tool("a", "ask_user", action_summary="Accept $40"), computer("b", "left_click", coordinate=[1, 1])),
        response(tool("c", "report_blocked", reason="declined", needs_user=False)),
    ])
    r = _runner(llm)
    r.run(_task())
    assert r.executor.ran == []
    assert llm.calls[1]["messages"][-1]["content"][1]["content"] == NOT_EXECUTED


def test_report_done_after_failed_action_is_not_success():
    from .conftest import computer, response, tool

    llm = ScriptedLLM(create_responses=[
        response(computer("a", "left_click", coordinate=[1, 1], fail=True), tool("b", "report_done", summary="published", result={})),
        response(tool("c", "report_blocked", reason="gave up", needs_user=False)),
    ])
    assert _runner(llm).run(_task()).status == "blocked"


def test_approval_steps_enforced_in_code():
    from .conftest import response, tool

    llm = ScriptedLLM(create_responses=[
        response(tool("a", "report_done", summary="paid", result={})),
        response(tool("b", "ask_user", action_summary="Pay $50")),
        response(tool("c", "report_done", summary="paid", result={})),
    ])
    result = _runner(llm, approve=lambda s: True).run(_task(approval_steps=("paying",)))
    assert result.status == "done" and len(llm.calls) == 3  # the first report_done was refused


# 7: untrusted page reads
def test_browser_adapter_rejects_mismatched_offer_amounts(monkeypatch):
    ad = BrowserAdapter("depop", "u", ScriptedLLM())
    pl = PlatformListing("depop", "1", "https://www.depop.com/products/1", 14900)
    monkeypatch.setattr(ad, "_run", lambda task: TaskResult("done", "", {"offer_shown_usd": "40.00", "final_amount_usd": "120.00"}))
    with pytest.raises(OfferMismatch):
        ad.respond_to_offer(pl, off(12000, "depop"), Decision("accept", "o", 12000, "x"), "ok")


def test_unverified_sold_flag_creates_no_sale(monkeypatch):
    ad = BrowserAdapter("depop", "u", ScriptedLLM())
    pl = PlatformListing("depop", "1", "https://www.depop.com/products/1", 14900)
    results = iter([TaskResult("done", "", {"offers": [], "messages": [], "sold": True}), TaskResult("done", "", {"sold": False})])
    monkeypatch.setattr(ad, "_run", lambda task: next(results))
    assert ad.poll(pl, None) == []


# 8, 9, 10: zones, floor disclosure, money text
def test_offer_at_floor_is_never_called_a_lowball():
    d = decide(off(5500, "offload"), Terms(10000, 5000), Thread("offload", "b"))
    assert d.action in ("counter", "accept")


def test_counter_does_not_reveal_the_exact_floor():
    d = decide(off(6000, "offload"), Terms(10000, 8000, speed="fast"), Thread("offload", "b"))
    assert d.action == "counter" and d.amount_cents > 8000 and d.amount_cents % 100 == 0


def test_money_text_keeps_cents():
    assert usd(9650) == "$96.50" and usd(13000) == "$130"
    assert "$96.50" in template(Decision("accept", "o", 9650, "x"))


# 11: boxes
def test_edge_and_pixel_boxes_dont_crash(photo):
    assert Box.clamp(1000, 0, 1000, 500).x0 == 999
    det = detection("multiple_items", [detected("i1", 0, 0, 400, 300), detected("i2", 500, 100, 700, 590)])
    det.items[1].x0, det.items[1].x1 = 500, 790  # pixel-space answer on an 800x600 photo
    llm = ScriptedLLM([det, make_ident(), make_ident()])
    assert len(analyze_photo(photo, llm).items) == 2


# 12: honesty gates
def test_listing_only_states_confident_facts(photo):
    ident = make_ident(material=attr("cashmere", 0.2), condition="like_new", condition_confidence=0.5, flaws=[],
                       dimensions=Dimensions(width_in=20, height_in=28, depth_in=None, method="category_typical", note=""))
    llm = ScriptedLLM([detection("single_item", [detected("i1", 0, 0, 1000, 1000)]), ident])
    item = analyze_photo(photo, llm).items[0]
    draft = compose_listing(item, estimate_price([], "like_new", retail_cents=20000))
    assert "material" not in draft.attributes and "cashmere" not in draft.description
    assert "No visible flaws" not in draft.description
    assert "measurements" not in draft.description.lower()
    assert "material" in item.low_confidence


def test_high_authenticity_risk_never_auto_lists(photo):
    llm = ScriptedLLM([detection("single_item", [detected("i1", 0, 0, 1000, 1000)]), make_ident(authenticity_risk="high")])
    assert not analyze_photo(photo, llm).items[0].ready_to_list


def test_every_missing_required_field_gets_its_shot():
    ident = make_ident(brand=attr(None, 0), size=attr(None, 0), condition="unknown", condition_confidence=0.0)
    missing, _, requests = assess(ident)
    assert {"brand", "size", "condition"} <= set(missing)
    assert {"brand_tag", "size_tag", "flaw_closeup"} <= {r.shot for r in requests}


# 13, 14: eBay
def _ebay(handler):
    return EbayAdapter("i", "s", "r", "F", "P", "R", "L", env="sandbox", http=httpx.Client(transport=httpx.MockTransport(handler)))


def test_ebay_department_and_rejected_price_update():
    bodies = []

    def handler(req):
        bodies.append(req.content)
        if req.url.path.endswith("/oauth2/token"):
            return httpx.Response(200, json={"access_token": "t", "expires_in": 7200})
        if req.url.path.endswith("/offer"):
            return httpx.Response(201, json={"offerId": "OF"})
        if req.url.path.endswith("/publish"):
            return httpx.Response(200, json={"listingId": "9"})
        if req.url.path.endswith("bulk_update_price_quantity"):
            return httpx.Response(200, json={"responses": [{"statusCode": 400, "errors": [{"message": "bad"}]}]})
        return httpx.Response(204)

    ad = _ebay(handler)
    pl = ad.create_listing({"title": "t", "description": "d", "category": "apparel", "condition": "good", "price_cents": 5000,
                            "attributes": {"gender": "Men's"}, "ebay_category_id": "1"}, photos=["https://x/1.jpg"])
    assert b'"Department":["Men"]' in bodies[1] and b"USED_EXCELLENT" in bodies[1]
    with pytest.raises(RuntimeError):
        ad.update_price(pl, 4500)
    assert pl.price_cents == 5000


# 15: guard and trimming
def test_data_urls_blocked_and_newest_screenshot_kept():
    assert not _host_allowed("data:text/html,<h1>x</h1>", ("depop.com",))
    img = lambda n: {"type": "image", "n": n}
    msgs = [{"role": "user", "content": [{"type": "tool_result", "content": [img(1), img(2)]}]}]
    _trim_screenshots(msgs, keep=1)
    parts = msgs[0]["content"][0]["content"]
    assert parts[1]["type"] == "image" and parts[0]["type"] == "text"
