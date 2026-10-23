import json
from datetime import datetime, timedelta, timezone

import httpx
import yaml

from offload.evals import norm, run_eval, similar
from offload.llm import ScriptedLLM
from offload.negotiation.models import Decision, Offer
from offload.posting.base import PlatformListing
from offload.posting.ebay import EbayAdapter
from offload.posting.fake import ScriptedBuyer
from offload.simulate import demo_job

from .conftest import attr, detected, detection, make_ident, png_bytes

T0 = datetime(2026, 10, 23, 9, tzinfo=timezone.utc)


def test_end_to_end_sale_delists_everywhere_else():
    job, p = demo_job(log=lambda s: None)
    job.post(T0)
    L = job.listings
    p["ebay"].buyer_offers(L["ebay"], ScriptedBuyer("b1", 9500, 13200, step_cents=1500), T0)
    p["fbm_shipped"].buyer_offers(L["fbm_shipped"], ScriptedBuyer("scam", 14900, 14900, message="pay by zelle?"), T0)
    kinds = [pr.kind for pr in job.tick(T0)] + [pr.kind for pr in job.tick(T0 + timedelta(hours=1))]
    assert "blocked_scam" in kinds and "sold" in kinds
    assert job.sold.platform == "ebay" and job.sold.price_cents == 13000
    assert all(l.status == "delisted" for n, l in L.items() if n != "ebay")


def test_acceptable_offers_need_seller_confirmation_and_best_net_wins():
    job, p = demo_job(log=lambda s: None)
    job.post(T0)
    L = job.listings
    p["ebay"].buyer_offers(L["ebay"], ScriptedBuyer("e", 14500, 14500), T0)
    p["offload"].buyer_offers(L["offload"], ScriptedBuyer("o", 14200, 14200), T0)
    prompts = job.tick(T0)
    confirm = [pr for pr in prompts if pr.kind == "confirm_sale"]
    assert len(confirm) == 1 and confirm[0].platform == "offload"  # $142 at 0% beats $145 minus fees
    assert job.sold is None  # nothing sold until the seller says so
    job.confirm_sale(confirm[0].offer, T0)
    assert job.sold.platform == "offload"


def test_price_drops_after_quiet_days():
    job, _ = demo_job(log=lambda s: None)
    job.post(T0)
    job.tick(T0 + timedelta(days=5))
    assert all(l.price_cents < 14900 for l in job.listings.values())
    assert all(l.price_cents >= job.terms.floor_cents for l in job.listings.values())


def test_ebay_adapter_request_shapes():
    seen = []

    def handler(req: httpx.Request) -> httpx.Response:
        seen.append((req.method, req.url.path, req.content))
        if req.url.path.endswith("/oauth2/token"):
            return httpx.Response(200, json={"access_token": "tok", "expires_in": 7200})
        if req.url.path.endswith("/get_category_suggestions"):
            return httpx.Response(200, json={"categorySuggestions": [{"category": {"categoryId": "57988"}}]})
        if req.url.path.endswith("/offer"):
            return httpx.Response(201, json={"offerId": "OF1"})
        if req.url.path.endswith("/publish"):
            return httpx.Response(200, json={"listingId": "123"})
        if req.url.path.endswith("/ws/api.dll"):
            return httpx.Response(200, text='<R xmlns="urn:ebay:apis:eBLBaseComponents"><Ack>Success</Ack></R>')
        return httpx.Response(204)

    ad = EbayAdapter("id", "secret", "refresh", "F", "P", "R", "LOC", env="sandbox", http=httpx.Client(transport=httpx.MockTransport(handler)))
    listing = {"title": "Arc'teryx Atom LT Hoody", "description": "d", "category": "apparel", "subcategory": "jacket",
               "attributes": {"brand": "Arc'teryx", "size": "M"}, "condition": "very_good", "price_cents": 14900,
               "best_offer": {"auto_accept_cents": 14200, "auto_decline_cents": 8900}}
    pl = ad.create_listing(listing, photos=["https://img.example/1.jpg"])
    assert pl.listing_id == "123" and pl.extra["offer_id"] == "OF1"
    offer_body = json.loads(next(c for m, path, c in seen if path.endswith("/sell/inventory/v1/offer")))
    assert offer_body["pricingSummary"]["price"] == {"currency": "USD", "value": "149.00"}
    assert offer_body["listingPolicies"]["bestOfferTerms"]["autoDeclinePrice"]["value"] == "89.00"
    item = json.loads(next(c for m, path, c in seen if "/inventory_item/" in path))
    assert item["condition"] == "PRE_OWNED_EXCELLENT" and item["product"]["aspects"]["Brand"] == ["Arc'teryx"]

    ad.respond_to_offer(pl, Offer("ebay-BO9", "ebay", "b", 12000, T0), Decision("counter", "ebay-BO9", 13000, "x"), "Can do $130 & ship fast")
    xml = seen[-1][2].decode()
    assert "<Action>Counter</Action>" in xml and ">130.00</CounterOfferPrice>" in xml and "&amp;" in xml


def test_ebay_rejects_local_photos_and_floor():
    ad = EbayAdapter("i", "s", "r", "F", "P", "R", "L", env="sandbox")
    import pytest

    with pytest.raises(ValueError):
        ad.create_listing({"title": "x", "floor_cents": 1}, photos=["https://a"])
    with pytest.raises(ValueError):
        ad.create_listing({"title": "x"}, photos=["/tmp/a.jpg"])


def test_eval_harness(tmp_path):
    (tmp_path / "a.png").write_bytes(png_bytes())
    (tmp_path / "labels.yaml").write_text(yaml.safe_dump([
        {"photo": "a.png", "items": [{"brand": "Arcteryx", "model_name": "Atom LT Hoodie", "size": "M", "gender": "mens",
                                      "category": "apparel", "condition": "good", "colors": ["black"]}]},
    ]))
    llm = ScriptedLLM([detection("single_item", [detected("i1", 0, 0, 1000, 1000)]), make_ident(size=attr("L", 0.95))])
    out = run_eval(tmp_path / "labels.yaml", llm, out_root=tmp_path / "runs")
    rep = (out / "report.md").read_text()
    assert "| brand | 100% |" in rep and "| model_name | 100% |" in rep  # alias + hoody/hoodie tolerated
    assert "| size | 0% |" in rep and "| condition_within_one | 100% |" in rep
    assert "wanted" in rep


def test_normalization():
    assert norm("Arc'teryx") == "arcteryx" and similar("The North Face", "north face")
    assert not similar("Atom LT", "Beta AR")
