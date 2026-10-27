"""Find it: parsing, routing, the ladder, the engine stream, and the sell flow, all offline."""

from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from offload.find import ladder as L
from offload.find.engine import FindSettings, Sources, find
from offload.find.models import CandidateVerdict, DefiningDetail, ItemProfile, Listing, Verdicts
from offload.find.router import RouterStats, route, segment
from offload.find.sources.base import SearchPlan
from offload.find.sources.ebay import EbayBrowse
from offload.find.sources.pagefetch import parse_listing
from offload.find.sources.shopify import ShopifyStores
from offload.find.sources.websearch import BraveSearch, WebSearchSource
from offload.listing.from_ladder import price_from_ladder
from offload.llm import ScriptedLLM
from offload.vision.attributes import ProductAttribute


def cesca(**kw) -> ItemProfile:
    base = dict(
        category="furniture",
        subcategory="side chair",
        brand="Knoll",
        brand_confidence=0.7,
        model_name="Cesca Chair",
        model_confidence=0.9,
        designer="Marcel Breuer",
        variant="cane seat, chrome, black wood",
        style_code=None,
        gtin=None,
        era="1970s",
        materials=["chrome", "cane", "beech"],
        colors=["black", "silver"],
        attributes=[
            ProductAttribute(name="seat height", value="18 in", confidence=0.6, evidence="typical spec", source="product_spec"),
            ProductAttribute(name="arms", value="armless", confidence=0.95, evidence="visible", source="visible"),
        ],
        defining_details=[
            DefiningDetail(detail="cantilevered chrome tube frame", why="the silhouette", must_match=True),
            DefiningDetail(detail="woven cane seat and back", why="signature material", must_match=True),
            DefiningDetail(detail="black stained wood frame", why="finish", must_match=False),
        ],
        exact_queries=["Knoll Cesca chair cane"],
        similar_queries=["cantilever chrome chair cane seat"],
        reproduction_risk="high",
        notes="Many Italian-made and unmarked reproductions; Knoll label under the seat.",
    )
    base.update(kw)
    return ItemProfile(**base)


def lst(title, price, url, source="chairish.com", condition="used", via="web", **kw) -> Listing:
    return Listing(source=source, url=url, title=title, price_cents=price, condition=condition,
                   image_urls=[f"{url}/img.jpg"], found_via=via, **kw)


# ---------- page parsing ----------


def test_parse_jsonld_product_with_offer_and_graph():
    html = """<html><head><script type="application/ld+json">
    {"@context":"https://schema.org","@graph":[{"@type":"BreadcrumbList"},
     {"@type":"Product","name":"Marcel Breuer Cesca Chair","image":["/a.jpg",{"url":"https://cdn.x/b.jpg"}],
      "brand":{"@type":"Brand","name":"Knoll"},"gtin13":"0123456789012","sku":"B32",
      "offers":{"@type":"Offer","price":"395.00","priceCurrency":"USD",
        "availability":"https://schema.org/InStock","itemCondition":"https://schema.org/UsedCondition"}}]}
    </script></head></html>"""
    x = parse_listing(html, "https://www.chairish.com/product/123/cesca")
    assert x is not None
    assert x.source == "chairish.com" and x.price_cents == 39500 and x.condition == "used"
    assert x.available is True and x.brand == "Knoll" and x.gtin == "0123456789012" and x.mpn == "B32"
    assert x.image_urls == ["https://www.chairish.com/a.jpg", "https://cdn.x/b.jpg"]


def test_parse_og_fallback_and_non_product():
    og = ('<meta property="og:type" content="product"><meta property="og:title" content="Cesca">'
          '<meta property="product:price:amount" content="120"><meta property="og:image" content="https://i/x.jpg">')
    x = parse_listing(og, "https://shop.example/p/1")
    assert x and x.price_cents == 12000 and x.image_urls == ["https://i/x.jpg"]
    assert parse_listing("<html><title>Blog</title></html>", "https://x.com/blog") is None


# ---------- routing ----------


def test_segment_and_learned_order(tmp_path):
    p = cesca()
    assert segment(p) == "furniture"
    assert segment(cesca(category="bags", brand="Hermès", subcategory="tote")) == "luxury"
    assert segment(cesca(category="footwear", subcategory="low-top sneaker")) == "sneakers"
    stats = RouterStats(path=tmp_path / "s.json")
    for _ in range(50):
        stats.record("furniture", "aptdeco.com", shown=1, clicked=1)
    stats.record("furniture", "chairish.com", shown=50)
    r = route(p, stats)
    assert r.resale_groups[0][0] == "aptdeco.com"
    assert all(len(g) <= 4 for g in r.resale_groups)
    assert RouterStats.load(tmp_path / "s.json").counts["furniture"]["aptdeco.com"] == [50, 50]


# ---------- the ladder ----------


def test_preliminary_is_conservative_and_final_uses_verdicts():
    p = cesca()
    items = [
        lst("Knoll Cesca Chair cane chrome", 45000, "https://a/1"),
        lst("Knoll Cesca Chair cane chrome", 45000, "https://a/1?utm=x"),  # duplicate URL
        lst("Cesca chair new from Knoll", 120000, "https://knoll.com/cesca", source="knoll.com", condition="new",
            seller_type="retail"),
        lst("Italian cantilever chrome chair with cane seat", 18000, "https://b/2"),
        lst("Plastic stacking chair", 3000, "https://c/3"),
    ]
    pre = L.preliminary(p, items)
    assert [r.listing.url for r in pre.exact_used] == ["https://a/1"]
    assert pre.exact_new and pre.exact_new[0].listing.source == "knoll.com"
    assert all("Plastic" not in r.listing.title for r in pre.all())

    cands = L.shortlist(p, items)
    idx = {c.url: i for i, c in enumerate(cands)}
    verdicts = [
        CandidateVerdict(index=idx["https://a/1"], match="exact", matched_details=["cantilevered chrome tube frame"],
                         missing_details=[], looks="used", confidence=0.9, reason="Same chair, Knoll label"),
        CandidateVerdict(index=idx["https://knoll.com/cesca"], match="exact", matched_details=[], missing_details=[],
                         looks="new", confidence=0.95, reason="Current Knoll production"),
        CandidateVerdict(index=idx["https://b/2"], match="similar",
                         matched_details=["cantilevered chrome frame", "woven cane seat and back"],
                         missing_details=[], looks="used", confidence=0.8, reason="Same shape, unbranded"),
        CandidateVerdict(index=idx["https://c/3"], match="unrelated", matched_details=[], missing_details=["cane"],
                         looks="used", confidence=0.9, reason="Different chair"),
    ]
    fin = L.final(p, cands, verdicts)
    assert [r.listing.url for r in fin.exact_used] == ["https://a/1"]
    assert [r.listing.url for r in fin.exact_new] == ["https://knoll.com/cesca"]
    assert [r.listing.url for r in fin.similar] == ["https://b/2"]
    assert fin.similar[0].score > 1.0  # both must-match details kept, despite paraphrase


def test_reissue_text_match_is_not_exact_without_vision():
    p = cesca(model_confidence=0.5)  # unsure of the exact model: never "exact" from text alone
    pre = L.preliminary(p, [lst("Knoll Cesca Chair", 40000, "https://a/1")])
    assert not pre.exact_used and pre.similar


def test_style_code_match_and_price_badges():
    p = cesca(category="footwear", subcategory="sneaker", brand="Nike", model_name="Dunk Low", style_code="DD1391-100")
    items = [lst(f"Nike Dunk Low Panda DD1391 100 size {s}", price, f"https://e/{s}", source="grailed.com")
             for s, price in [(9, 9000), (10, 10000), (11, 11000), (12, 12000), (8, 6000)]]
    pre = L.preliminary(p, items)
    assert len(pre.exact_used) == 5 and pre.typical_used_cents == 10000
    badges = {r.listing.url: r.price_badge for r in pre.exact_used}
    assert badges["https://e/8"] == "good_price" and badges["https://e/12"] == "high" and badges["https://e/10"] == "typical"


def test_ebay_results_are_separate_and_never_priced():
    """eBay API License 8.1(b)(2) no co-mingling; 9.5 no price modeling."""
    p = cesca()
    items = [lst("Knoll Cesca Chair cane chrome", 40000 + i * 1000, f"https://a/{i}") for i in range(4)]
    items += [lst("Knoll Cesca Chair cane chrome", 10000 + i, f"https://ebay.com/itm/{i}", source="ebay") for i in range(5)]
    pre = L.preliminary(p, items)
    assert all(r.listing.source != "ebay" for r in pre.exact_used + pre.exact_new + pre.similar)
    assert len(pre.ebay) == 5 and all(r.price_badge is None for r in pre.ebay)
    assert pre.typical_used_cents == 41500  # median of the four non-eBay asks only
    est = price_from_ladder(pre, "very_good")
    assert est is None or all(c.platform != "ebay" for c in est.comps_used)


# ---------- sources over a mocked network ----------


def mock_client(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def test_ebay_maps_conditions_and_splits_new_used():
    seen = []

    def handler(req: httpx.Request):
        seen.append(req)
        if req.url.path.endswith("/oauth2/token"):
            return httpx.Response(200, json={"access_token": "T", "expires_in": 7200})
        cond = "1000" if "1000" in str(req.url) else "3000"
        return httpx.Response(200, json={"itemSummaries": [{
            "title": "Knoll Cesca", "price": {"value": "450.00", "currency": "USD"}, "conditionId": cond,
            "itemWebUrl": f"https://ebay.com/itm/{cond}", "image": {"imageUrl": "https://i/1.jpg"},
            "itemLocation": {"city": "Oakland", "stateOrProvince": "CA", "country": "US"},
            "shippingOptions": [{"shippingCost": {"value": "35.00"}}]}]})

    async def go():
        async with mock_client(handler) as c:
            src = EbayBrowse("app", "cert")
            plan = SearchPlan(cesca(), ["Knoll Cesca chair cane"], ["cantilever chrome chair"])
            return await src.search(plan, c)

    out = asyncio.run(go())
    assert {x.condition for x in out} == {"new", "used"}
    assert out[0].price_cents == 45000 and out[0].shipping_cents == 3500 and out[0].location == "Oakland, CA, US"
    assert sum(1 for r in seen if r.url.path.endswith("/oauth2/token")) == 1  # token reused
    assert all(r.headers.get("X-EBAY-C-MARKETPLACE-ID") == "EBAY_US" for r in seen[1:])


def test_web_search_reads_pages_respects_robots_and_keeps_links():
    page = """<script type="application/ld+json">{"@type":"Product","name":"Cesca chair pair",
      "offers":{"price":300,"priceCurrency":"USD","itemCondition":"https://schema.org/UsedCondition"}}</script>"""

    def handler(req: httpx.Request):
        host, path = req.url.host, req.url.path
        if host == "api.search.brave.com":
            assert "site:chairish.com" in req.url.params["q"]
            return httpx.Response(200, json={"web": {"results": [
                {"url": "https://www.chairish.com/product/1/cesca", "title": "Cesca pair"},
                {"url": "https://www.1stdibs.com/furniture/seating/id-f_9/", "title": "Breuer chairs",
                 "thumbnail": {"src": "https://t/9.jpg"}},
                {"url": "https://www.chairish.com/search?q=cesca", "title": "search page"}]}})
        if path == "/robots.txt":
            body = "User-agent: *\nDisallow: /furniture/" if "1stdibs" in host else "User-agent: *\nAllow: /"
            return httpx.Response(200, text=body)
        return httpx.Response(200, text=page, headers={"content-type": "text/html"})

    async def go():
        async with mock_client(handler) as c:
            src = WebSearchSource("web:test", BraveSearch("k"), domains=["chairish.com", "1stdibs.com"])
            return await src.search(SearchPlan(cesca(), ["Knoll Cesca"], []), c)

    out = {x.source: x for x in asyncio.run(go())}
    assert out["chairish.com"].price_cents == 30000 and out["chairish.com"].condition == "used"
    assert out["1stdibs.com"].price_cents is None and out["1stdibs.com"].found_via.endswith("search:link")
    assert len(out) == 2  # the search page was skipped


def test_shopify_predictive_search():
    def handler(req):
        return httpx.Response(200, json={"resources": {"results": {"products": [
            {"title": "Vintage Cesca chair", "url": "/products/cesca?_pos=1", "price": "275.00",
             "image": "https://cdn.shopify.com/c.jpg", "available": True, "vendor": "Knoll"}]}}})

    async def go():
        async with mock_client(handler) as c:
            plan = SearchPlan(cesca(), ["Knoll Cesca"], [], shopify_stores=["modernshop.com"])
            return await ShopifyStores().search(plan, c)

    (x,) = asyncio.run(go())
    assert x.url == "https://modernshop.com/products/cesca" and x.price_cents == 27500 and x.source == "shopify:modernshop.com"


# ---------- the engine stream and the sell flow ----------


class FakeSource:
    def __init__(self, name, items, delay=0.0, fail=False):
        self.name, self.items, self.delay, self.fail = name, items, delay, fail

    async def search(self, plan, client):
        await asyncio.sleep(self.delay)
        if self.fail:
            raise RuntimeError("blocked")
        return self.items


def test_engine_streams_profile_sources_and_final_ladder(tmp_path):
    items = [lst("Knoll Cesca Chair cane chrome", 40000 + i * 1000, f"https://a/{i}") for i in range(6)]
    items.append(lst("Cantilever chrome cane chair", 15000, "https://b/1"))

    def verdicts(req):
        text = req["content"][-1]["text"]
        n = text.count("\n#")
        out = []
        for i in range(n):
            line = text.split(f"#{i}: ")[1].split("\n")[0] if f"#{i}: " in text else ""
            if "Knoll" in line:
                out.append(CandidateVerdict(index=i, match="exact", matched_details=[], missing_details=[], looks="used",
                                            confidence=0.9, reason="same"))
            else:
                out.append(CandidateVerdict(index=i, match="similar", matched_details=["woven cane seat and back"],
                                            missing_details=[], looks="used", confidence=0.7, reason="close"))
        return Verdicts(verdicts=out)

    llm = ScriptedLLM([cesca(), verdicts])
    srcs = Sources(sites=False, extra=[FakeSource("fast", items[:3]), FakeSource("slow", items[3:], delay=0.05),
                          FakeSource("broken", [], fail=True)])
    fs = FindSettings(router_stats_file=tmp_path / "none.json", shopify_stores_file=tmp_path / "none.txt",
                      verify_batch=8)

    async def go():
        async with mock_client(lambda r: httpx.Response(404)) as c:
            return [e async for e in find(llm, text="cesca chair", sources=srcs, fs=fs, client=c)]

    events = asyncio.run(go())
    kinds = [e["type"] for e in events]
    assert kinds[0] == "profile" and kinds[1] == "route" and kinds[-1] == "done"
    assert [e["source"] for e in events if e["type"] == "source"] == ["broken", "fast", "slow"] or \
        {e["source"] for e in events if e["type"] == "source"} == {"broken", "fast", "slow"}
    final = [e for e in events if e["type"] == "ladder" and e["stage"] == "final"][0]
    lad = final["ladder"]
    assert len(lad["exact_used"]) == 6 and len(lad["similar"]) == 1
    assert "broken" in lad["sources_failed"] and lad["typical_used_cents"]
    json.dumps({k: v for k, v in final.items() if not k.startswith("_")})  # serializable

    est = price_from_ladder(final["_ladder"], "very_good", segment="furniture")
    assert est is not None and est.floor_cents <= est.expected_cents <= est.list_cents
    assert any("haven't sold" in n for n in est.notes)


def test_price_from_ladder_falls_back_to_retail_or_none():
    p = cesca()
    new_only = L.preliminary(p, [lst("Knoll Cesca Chair", 120000, "https://knoll.com/c", source="knoll.com",
                                      condition="new", seller_type="retail")])
    est = price_from_ladder(new_only, "good", segment="furniture")
    assert est is not None and est.confidence == "low"
    assert any("retail $1,200" in n for n in est.notes)
    assert price_from_ladder(L.preliminary(p, []), "good") is None


def test_benchmark_runs_and_scores(tmp_path):
    from PIL import Image

    from offload.bench import draft_benchmark, run_benchmark

    for name in ("cesca-01", "pile-bed-01"):
        d = tmp_path / name
        d.mkdir()
        Image.new("RGB", (32, 32)).save(d / "1.jpg")
        (d / "note.txt").write_text("Knoll Cesca chair, cane\npaid $200")
    path = draft_benchmark(tmp_path)
    import yaml

    entries = yaml.safe_load(path.read_text())
    assert [e["kind"] for e in entries] == ["find", "pile"]
    entries[0]["truth"].update(brand="Knoll", model="Cesca")
    path.write_text(yaml.safe_dump(entries))

    items = [lst("Knoll Cesca Chair cane chrome", 40000 + i, f"https://a/{i}") for i in range(3)]

    def all_exact(req):
        n = req["content"][-1]["text"].count("\n#")
        return Verdicts(verdicts=[CandidateVerdict(index=i, match="exact", matched_details=[], missing_details=[],
                                                   looks="used", confidence=0.9, reason="same") for i in range(n)])

    fs = FindSettings(router_stats_file=tmp_path / "x.json", shopify_stores_file=tmp_path / "x.txt")
    out = run_benchmark(path, ScriptedLLM([cesca(), all_exact]), Sources(sites=False, extra=[FakeSource("fake", items)]), fs)
    summary = (out / "summary.md").read_text()
    assert "| Brand right | 100% of 1 |" in summary and "| Found the exact item used | 100% of 1 |" in summary
    judge = json.loads((out / "judge.json").read_text())
    assert judge[0]["id"] == "cesca-01" and len(judge[0]["results"]["exact_used"]) == 3


def test_marketplace_handoff_links():
    from offload.find.deeplinks import facebook_marketplace, handoff_links

    url = facebook_marketplace("knoll cesca chair", "sanfrancisco", max_price=40000)
    assert url == "https://www.facebook.com/marketplace/sanfrancisco/search/?query=knoll+cesca+chair&maxPrice=400"
    links = handoff_links(["Knoll Cesca chair"], ["cantilever cane chair"], "furniture", "oakland")
    assert len(links) == 2 and "/marketplace/oakland/" in links[0]["url"]
