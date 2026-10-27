"""Direct site connectors: request shape, parsing, sold handling, gating, and stopping when refused."""

from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from offload.find.sources.base import SearchPlan
from offload.find.sources.sites import base as site_base
from offload.find.sources.sites.base import Blocked
from offload.find.sources.sites.grailed import Grailed
from offload.find.sources.sites.poshmark import Poshmark
from offload.find.sources.sites.registry import enabled_connectors
from tests.test_find import cesca


def run(conn, handler, plan=None):
    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
            return await conn.search(plan or SearchPlan(cesca(), ["madewell perfect vintage jean 27"], []), c)
    return asyncio.run(go())


@pytest.fixture(autouse=True)
def fresh_breaker(monkeypatch):
    monkeypatch.setattr(site_base, "BREAKER", site_base.Breaker())


def test_poshmark_request_and_parse():
    seen = []

    def handler(req: httpx.Request):
        seen.append(req)
        body = json.loads(req.url.params["request"])
        assert body == {"query": "madewell perfect vintage jean 27", "count": 30, "experience": "all"}
        return httpx.Response(200, json={"data": [{
            "id": "64a1", "title": "Madewell Perfect Vintage Jean 27", "price_amount": {"val": "38.00", "currency_code": "USD"},
            "brand": "Madewell", "size_obj": {"display_with_size_system": "US 27"}, "nwt": False,
            "cover_shot": {"url": "https://di2ponv0v5otw.cloudfront.net/a.jpg"}, "inventory": {"status": "available"},
            "first_published_at": "2026-10-01T10:00:00-07:00", "aggregates": {"likes": 7}}]})

    (x,) = run(Poshmark(), handler)
    assert x.url == "https://poshmark.com/listing/64a1" and x.price_cents == 3800 and x.likes == 7
    assert x.attributes["size"] == "US 27" and x.status == "active" and x.days_listed and x.days_listed > 20
    assert seen[0].headers["User-Agent"].startswith("OffloadBot")


def test_grailed_sold_index_and_key_discovery():
    calls = []

    def handler(req: httpx.Request):
        calls.append(req)
        if req.url.host == "www.grailed.com":
            return httpx.Response(200, text='<script>window.PUBLIC_CONFIG={"publicSearchKey":"pk123"}</script>')
        body = json.loads(req.content)
        index = body["requests"][0]["indexName"]
        assert req.headers["x-algolia-api-key"] == "pk123"
        hit = {"id": 9, "title": "Our Legacy Third Cut 30", "price": 180, "designers": [{"name": "Our Legacy"}],
               "condition": "is_gently_used", "size": "30"}
        if "sold" in index:
            hit.update(sold=True, sold_price=150, sold_at="2026-10-02T00:00:00Z")
        return httpx.Response(200, json={"results": [{"hits": [hit]}]})

    out = run(Grailed(), handler, SearchPlan(cesca(), ["our legacy third cut"], []))
    sold = [x for x in out if x.status == "sold"]
    active = [x for x in out if x.status == "active"]
    assert sold and sold[0].price_cents == 15000 and sold[0].sold_on == "2026-10-02"
    assert active and active[0].price_cents == 18000 and active[0].brand == "Our Legacy"
    assert sum(1 for c in calls if c.url.host == "www.grailed.com") == 1  # key fetched once


def test_refusal_benches_the_site_and_does_not_retry():
    hits = []

    def handler(req):
        hits.append(req)
        return httpx.Response(403, text="<html>px-captcha</html>")

    with pytest.raises(Blocked):
        run(Poshmark(), handler)
    n = len(hits)
    with pytest.raises(Blocked, match="cooling down"):
        run(Poshmark(), handler)
    assert len(hits) == n  # no second attempt while benched


def test_connectors_are_off_unless_enabled(monkeypatch):
    monkeypatch.delenv("OFFLOAD_ENABLED_SITES", raising=False)
    assert enabled_connectors("fashion") == []
    monkeypatch.setenv("OFFLOAD_ENABLED_SITES", "poshmark, grailed")
    assert {c.name for c in enabled_connectors("menswear")} == {"poshmark", "grailed"}
    assert enabled_connectors("furniture") == []
