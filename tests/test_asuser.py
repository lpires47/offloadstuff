"""Searching as the user: a real browser opens the site's own search page in the user's session;
we read the JSON the page loads, embedded data, or result cards. Sites are faked with routes."""

from __future__ import annotations

import asyncio
import json

import pytest

from offload.find.sources.asuser.providers import Consents, LocalProvider
from offload.find.sources.asuser.reader import AsUserSource, NeedsUser, PacePolicy, walk_listings
from offload.find.sources.asuser.recipes import RECIPES, for_segment
from offload.find.sources.base import SearchPlan
from tests.test_find import cesca

FB_JSON = {"data": {"marketplace_search": {"feed_units": {"edges": [{"node": {"listing": {
    "id": "1234567890", "marketplace_listing_title": "Knoll Cesca chairs (set of 4)",
    "listing_price": {"amount": "320.00", "formatted_amount": "$320"},
    "primary_listing_photo": {"image": {"uri": "https://scontent.example/x.jpg"}},
    "location": {"reverse_geocode": {"city": "Oakland", "state": "CA"}}}}}]}}}}

FB_PAGE = """<html><body><div id=root>loading</div><script>
fetch('/api/graphql/', {method: 'POST'}).then(r => r.json()).then(() => document.getElementById('root').textContent = 'done');
</script></body></html>"""

CARDS_PAGE = """<html><body>
<div class=card><a href="/listing/madewell-jean-64a1"><img alt="Madewell Perfect Vintage Jean"></a><span>$38</span></div>
<div class=card><a href="/listing/madewell-jean-64a2"><img alt="Madewell Jean 27"></a><span>$45.00</span></div>
<a href="/closet/someone">not a listing</a></body></html>"""


async def fake_site(context, pages: dict[str, tuple[str, str]]):
    async def handle(route):
        url = route.request.url
        for key, (ctype, body) in pages.items():
            if key in url:
                return await route.fulfill(status=200, content_type=ctype, body=body)
        await route.fulfill(status=404, body="")
    await context.route("**/*", handle)


def run_source(recipe_name, pages, tmp_path, plan=None):
    async def go():
        provider = LocalProvider(root=tmp_path)
        try:
            ctx = await provider.context("liselle", recipe_name)
            await fake_site(ctx, pages)
            src = AsUserSource(RECIPES[recipe_name], "liselle", provider, PacePolicy(min_interval_s=0))
            return await src.search(plan or SearchPlan(cesca(), ["knoll cesca chair"], []))
        finally:
            await provider.close()
    return asyncio.run(go())


def test_facebook_results_from_the_pages_own_graphql(tmp_path):
    out = run_source("facebook", {
        "/marketplace/sanfrancisco/search": ("text/html", FB_PAGE),
        "/api/graphql": ("application/json", json.dumps(FB_JSON)),
    }, tmp_path)
    (x,) = out
    assert x.source == "facebook" and x.price_cents == 32000 and x.location == "Oakland, CA"
    assert x.url == "https://www.facebook.com/marketplace/item/1234567890/"
    assert (tmp_path / "liselle" / "facebook.json").exists()  # session saved back for next time


def test_result_cards_when_no_json(tmp_path):
    out = run_source("poshmark", {"poshmark.com/search": ("text/html", CARDS_PAGE)}, tmp_path,
                     SearchPlan(cesca(), [], ["madewell jean"]))
    assert {x.price_cents for x in out} == {3800, 4500}
    assert all("/listing/" in x.url for x in out) and out[0].title.startswith("Madewell")


def test_human_check_stops_and_asks_the_user(tmp_path):
    page = "<html><title>Just a moment</title><body>Verify you are human</body></html>"
    with pytest.raises(NeedsUser, match="human check"):
        run_source("mercari", {"mercari.com/search": ("text/html", page)}, tmp_path)


def test_login_wall_asks_to_connect(tmp_path):
    page = "<html><body>Log in to continue <a href='/login'>Log in</a></body></html>"
    with pytest.raises(NeedsUser, match="connect your facebook"):
        run_source("facebook", {"/marketplace/": ("text/html", page)}, tmp_path)


def test_consent_is_per_site_and_scope(tmp_path):
    c = Consents(root=tmp_path)
    c.grant("liselle", "facebook", ["search", "buy"])
    c.grant("liselle", "poshmark", ["search"])
    assert c.sites_for("liselle") == {"facebook", "poshmark"} and c.sites_for("liselle", "buy") == {"facebook"}
    c.revoke("liselle", "poshmark")
    assert c.sites_for("liselle") == {"facebook"}
    assert {r.name for r in for_segment("furniture", {"facebook", "poshmark"})} == {"facebook"}
    assert "ebay" not in RECIPES  # eBay only through its API
    with pytest.raises(ValueError):
        c.grant("liselle", "facebook", ["scrape_everything"])


def test_walker_finds_listings_in_unknown_shapes():
    out = []
    walk_listings({"results": [{"hits": [{"objectID": "9", "title": "Our Legacy Third Cut", "price_i": 180,
                                          "sold": True}]}]}, RECIPES["grailed"], out)
    (x,) = out
    assert x.url == "https://www.grailed.com/listings/9" and x.price_cents == 18000 and x.status == "sold"


def test_facebook_card_labels_as_seen_live():
    """Labels copied from a real Marketplace search, 2026-10-27."""
    from offload.find.sources.asuser.reader import card_listing

    fb = RECIPES["facebook"]
    a = card_listing(fb, {"url": "https://www.facebook.com/marketplace/item/1606259317092238/", "price": "$150",
                          "title": "Two Cesca Style Chairs, $150, reduced from $195, San Francisco, CA, listing 1606259317092238"})
    assert (a.title, a.price_cents, a.location, a.attributes["was_price"]) == ("Two Cesca Style Chairs", 15000, "San Francisco, CA", "$195")
    b = card_listing(fb, {"url": "u", "price": "$480",
                          "title": "Cesca side chair by Marcel Breuer for Knoll (Price Per chair), $480, , listing 1591391152424595"})
    assert b.title == "Cesca side chair by Marcel Breuer for Knoll (Price Per chair)" and b.price_cents == 48000 and b.location is None
    c = card_listing(fb, {"url": "u", "price": "$320.61",
                          "title": "Zesthouse Natural Rattan Dining Chairs Set Of 2, Modern Cesca Kitchen Chair, $320.61, Citrus Heights, CA, listing 29044495775136847"})
    assert c.title.startswith("Zesthouse") and c.price_cents == 32061 and c.location == "Citrus Heights, CA"
