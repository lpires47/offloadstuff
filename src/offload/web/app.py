"""The test app: Find it (buy side) and Photo -> listing (sell side) on one engine.

Run:  uvicorn offload.web.app:app --host 0.0.0.0 --port 8000
Needs ANTHROPIC_API_KEY; each of EBAY_CLIENT_ID/EBAY_CLIENT_SECRET, BRAVE_API_KEY, ETSY_API_KEY adds sources.
"""

from __future__ import annotations

import asyncio
import json
import os
import logging
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from offload.config import settings
from offload.find.engine import AsUser, FindSettings, Sources, find, ladder_dict
from offload.find.sources.asuser.providers import BrowserbaseProvider, Consents, LocalProvider
from offload.find.sources.asuser.recipes import NEVER, RECIPES
from offload.find.profile import build_profile
from offload.find.router import RouterStats
from offload.images import load_photo
from offload.listing.compose import compose_listing
from offload.find.router import segment as segment_of
from offload.listing.from_ladder import as_estimate, value_from_ladder
from offload.llm import AnthropicLLM, LLM
from offload.vision.pipeline import _finish, identify_item

log = logging.getLogger("offload.web")
STATIC = Path(__file__).parent / "static"
MAX_PHOTOS = 4
MAX_BYTES = 15 * 1024 * 1024

app = FastAPI(title="Offload test app")
ACCESS_TOKEN = os.environ.get("OFFLOAD_ACCESS_TOKEN", "")


@app.middleware("http")
async def private_link(request, call_next):
    """The test app is reachable by link, and it holds signed-in sessions: require the private key
    (?k=... once, then a cookie) whenever OFFLOAD_ACCESS_TOKEN is set."""
    from fastapi.responses import PlainTextResponse, RedirectResponse

    if not ACCESS_TOKEN or request.url.path == "/api/health":
        return await call_next(request)
    if request.query_params.get("k") == ACCESS_TOKEN:
        resp = RedirectResponse(str(request.url.remove_query_params("k")))
        resp.set_cookie("offload_k", ACCESS_TOKEN, httponly=True, secure=True, samesite="lax", max_age=30 * 86400)
        return resp
    if request.cookies.get("offload_k") != ACCESS_TOKEN:
        return PlainTextResponse("Private test app. Open it with your link.", status_code=401)
    return await call_next(request)
_state: dict = {}


def llm() -> LLM:
    if "llm" not in _state:
        _state["llm"] = AnthropicLLM()
    return _state["llm"]


USER_ID = os.environ.get("OFFLOAD_USER", "liselle")  # single-user test; real auth comes with accounts


def consents() -> Consents:
    if "consents" not in _state:
        _state["consents"] = Consents()
    return _state["consents"]


def provider():
    """The user's browser sessions: hosted (Browserbase) in production, local Chromium in development."""
    if "provider" not in _state:
        kind = os.environ.get("OFFLOAD_BROWSER", "local")
        _state["provider"] = BrowserbaseProvider() if kind == "browserbase" else LocalProvider()
    return _state["provider"]


def sources() -> Sources:
    if "sources" not in _state:
        s = Sources.from_settings(FindSettings())
        if os.environ.get("OFFLOAD_BROWSER", "local") != "off":
            s.as_user = AsUser(USER_ID, provider(), consents())
        _state["sources"] = s
    return _state["sources"]


def stats() -> RouterStats:
    if "stats" not in _state:
        path = FindSettings().router_stats_file
        path.parent.mkdir(parents=True, exist_ok=True)
        _state["stats"] = RouterStats.load(path)
    return _state["stats"]


async def _photos(files: list[UploadFile] | None):
    photos = []
    for f in (files or [])[:MAX_PHOTOS]:
        data = await f.read()
        if not data:
            continue
        if len(data) > MAX_BYTES:
            raise HTTPException(413, "photo too large")
        photos.append(await asyncio.to_thread(load_photo, data, settings().max_image_edge))
    return photos


def _log_event(run_id: str, event: dict) -> None:
    # Every run is logged: the benchmark and the router learn from these.
    path = Path("data/runs") / f"{time.strftime('%Y-%m-%d')}.ndjson"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as fh:
        fh.write(json.dumps({"run": run_id, **{k: v for k, v in event.items() if not k.startswith("_")}}) + "\n")


@app.get("/")
async def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/health")
async def health():
    s = sources()
    return {
        "anthropic": settings().has_api_key,
        "ebay": s.ebay is not None,
        "etsy": s.etsy is not None,
        "web_search": s.web is not None,
        "shopify_stores": FindSettings().shopify_stores_file.exists(),
    }


@app.post("/api/find")
async def api_find(
    photos: list[UploadFile] | None = File(None),
    text: str | None = Form(None),
    city: str = Form("sanfrancisco"),
    scope: str | None = Form(None),  # "furniture" for test 2
):
    pics = await _photos(photos)
    if not pics and not (text and text.strip()):
        raise HTTPException(400, "send a photo or a description")
    run_id = uuid.uuid4().hex[:12]

    async def stream():
        segment = None
        try:
            async for event in find(llm(), photos=pics, text=text, sources=sources(), city_slug=city,
                                    segment_override=scope):
                if event["type"] == "route":
                    segment = event["segment"]
                if event["type"] == "ladder" and event["stage"] == "final" and segment:
                    for r in event["_ladder"].all():
                        domain = r.listing.source.split(":")[-1]
                        stats().record(segment, domain, shown=1)
                _log_event(run_id, event)
                out = {k: v for k, v in event.items() if not k.startswith("_")}
                yield json.dumps({"run": run_id, "segment": segment, **out}) + "\n"
        except Exception as e:  # noqa: BLE001
            log.exception("find failed")
            yield json.dumps({"type": "error", "message": str(e)[:300]}) + "\n"

    return StreamingResponse(stream(), media_type="application/x-ndjson")


class Click(BaseModel):
    run: str
    segment: str
    source: str
    url: str
    rung: str


@app.post("/api/click")
async def api_click(c: Click):
    stats().record(c.segment, c.source.split(":")[-1], clicked=1)
    _log_event(c.run, {"type": "click", **c.model_dump()})
    return {"ok": True}


DRAFTS: dict[str, dict] = {}  # run id -> draft + photo paths, for the publish step


async def draft_for(pics, speed: str = "balanced", *, overview=None) -> dict:
    """Photos of one item -> what it is, what it's worth here and everywhere, and a listing to sign off."""
    cfg = settings()
    ident_task = asyncio.create_task(asyncio.to_thread(identify_item, pics, llm(), overview=overview, cfg=cfg))
    profile = await asyncio.to_thread(build_profile, llm(), photos=pics, cfg=cfg)
    final = None
    async for event in find(llm(), photos=pics, sources=sources(), profile=profile):
        if event["type"] == "ladder" and event["stage"] == "final":
            final = event["_ladder"]
    ident = await ident_task
    analysis = _finish(None, ident, pics)
    sub = ident.subcategory.lower()
    season = "outerwear" if any(w in sub for w in ("coat", "jacket", "parka", "puffer", "vest")) else (
        "swim" if "swim" in sub else "default")
    valuation, price_error = None, None
    if final:
        try:
            valuation = value_from_ladder(final, segment=segment_of(profile), condition=ident.condition, speed=speed,  # type: ignore[arg-type]
                                          season_family=season, identification=ident, photo_count=len(pics))
        except ValueError as e:  # e.g. high authenticity risk: route to an authenticator first
            price_error = str(e)
    price = as_estimate(valuation) if valuation else None
    body: dict = {
        "identity": {"category": ident.category, "subcategory": ident.subcategory,
                     "brand": ident.brand.value, "model": ident.model_name.value, "condition": ident.condition,
                     "attributes": [a.model_dump() for a in ident.attributes if a.value]},
        "ready_to_list": analysis.ready_to_list,
        "photo_requests": [r.model_dump() for r in analysis.photo_requests],
        "flagged_fields": sorted(set(analysis.low_confidence + analysis.missing)),
        "market": ladder_dict(final) if final else None,
    }
    if price is None:
        body["draft"] = None
        body["price_note"] = price_error or "Not enough market data for this item yet; set a price on the sign-off screen."
        return body
    draft = compose_listing(analysis, price)
    body["draft"] = {
        **draft.public_view(),
        "hidden_minimum_cents": draft.floor_cents,
        "expected_cents": draft.expected_cents,
        "range_cents": [price.p10_cents, price.p90_cents],
        "package": draft.package.__dict__ if hasattr(draft.package, "__dict__") else str(draft.package),
        "price_confidence": price.confidence,
        "price_notes": price.notes,
        "tier": valuation.tier,
        "value_cents": valuation.value_cents,
        "p_sold": valuation.p_sold,
        "median_days": valuation.median_days,
        "evidence": valuation.evidence,
        "adjustments": [{"factor": a.factor, "reason": a.reason} for a in valuation.adjustments],
        "platforms": [p.__dict__ for p in valuation.plans],
        "comps": [
            {"title": r.listing.title, "price_cents": r.listing.price_cents, "url": r.listing.url,
             "status": r.listing.status, "source": r.listing.source}
            for r in [*final.exact_used, *final.sold][:10] if r.listing.source != "ebay"
        ],
    }
    return body


def _save_photos(run_id: str, pics) -> list[str]:
    folder = Path("data/runs") / run_id
    folder.mkdir(parents=True, exist_ok=True)
    paths = []
    for i, p in enumerate(pics):
        path = folder / f"photo_{i}.jpg"
        path.write_bytes(p.jpeg_bytes())
        paths.append(str(path.resolve()))
    return paths


@app.post("/api/sell")
async def api_sell(photos: list[UploadFile] = File(...), speed: str = Form("balanced")):
    """Test 3: photo -> a listing draft for one-step sign-off, priced from the exact item's market."""
    pics = await _photos(photos)
    if not pics:
        raise HTTPException(400, "send at least one photo")
    run_id = uuid.uuid4().hex[:12]
    body = {"run": run_id, **await draft_for(pics, speed)}
    DRAFTS[run_id] = {"draft": body.get("draft"), "photos": _save_photos(run_id, pics)}
    _log_event(run_id, {"type": "sell", **{k: v for k, v in body.items() if k != "market"}})
    return body


class Publish(BaseModel):
    run: str
    platforms: list[str]
    title: str | None = None
    price_cents: int | None = None
    hidden_minimum_cents: int | None = None
    description: str | None = None
    live: bool = False  # False: fill everything in and stop right before Publish


@app.post("/api/sell/publish")
async def api_publish(req: Publish):
    """The one sign-off: list on every chosen platform, as the user, in their own session."""
    from offload.posting.browser.adapter import BrowserAdapter, BrowserTaskError

    saved = DRAFTS.get(req.run)
    if not saved or not saved["draft"]:
        raise HTTPException(404, "no draft for this run")
    allowed = consents().sites_for(USER_ID, "list")
    d = dict(saved["draft"])
    for k in ("title", "price_cents", "description"):
        if getattr(req, k) is not None:
            d[k] = getattr(req, k)
    listing = {k: d[k] for k in ("title", "description", "category", "subcategory", "attributes", "condition", "price_cents")}
    root = provider().root if isinstance(provider(), LocalProvider) else None

    def one(platform: str) -> dict:
        if platform not in allowed:
            return {"platform": platform, "status": "needs_consent",
                    "message": f"Allow listing on {platform} in Accounts first"}
        adapter = BrowserAdapter(platform, USER_ID, llm(), approve=lambda summary: req.live, sessions_root=root)
        try:
            pl = adapter.create_listing(listing, photos=saved["photos"])
            return {"platform": platform, "status": "listed", "url": pl.url}
        except BrowserTaskError as e:
            stopped = not req.live and "publish" in str(e).lower()
            return {"platform": platform, "status": "ready_to_publish" if stopped else "needs_you",
                    "message": e.result.summary[:300]}
        except Exception as e:  # noqa: BLE001
            return {"platform": platform, "status": "failed", "message": f"{type(e).__name__}: {e}"[:300]}

    results = await asyncio.gather(*(asyncio.to_thread(one, p) for p in req.platforms))
    _log_event(req.run, {"type": "publish", "live": req.live, "results": results,
                         "hidden_minimum_cents": req.hidden_minimum_cents or d.get("hidden_minimum_cents")})
    return {"results": results}


@app.post("/api/pile")
async def api_pile(photo: UploadFile = File(...), speed: str = Form("balanced")):
    """Test 4: one photo of a pile -> every item found, each with its own listing draft, streamed."""
    from offload.vision.pipeline import analyze_photo, box_of

    pics = await _photos([photo])
    if not pics:
        raise HTTPException(400, "send a photo")
    run_id = uuid.uuid4().hex[:12]
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue()

    def detect_and_identify():
        analysis = analyze_photo(pics[0], llm(), on_item=lambda it: loop.call_soon_threadsafe(queue.put_nowait, ("item", it)))
        loop.call_soon_threadsafe(queue.put_nowait, ("done", analysis))

    async def stream():
        t0 = time.perf_counter()
        ms = lambda: int((time.perf_counter() - t0) * 1000)  # noqa: E731
        worker = asyncio.create_task(asyncio.to_thread(detect_and_identify))
        pricing: set[asyncio.Task] = set()
        sem = asyncio.Semaphore(3)
        n = 0

        async def price_item(idx: int, item):
            async with sem:
                body = await draft_for(item.photos, speed)
            rid = f"{run_id}-{idx}"
            DRAFTS[rid] = {"draft": body.get("draft"), "photos": _save_photos(rid, item.photos)}
            return {"type": "draft", "ms": ms(), "index": idx, "run": rid, **body}

        try:
            while True:
                kind, payload = await queue.get()
                if kind == "item":
                    box = box_of(payload.detected, pics[0]) if payload.detected else None
                    i = payload.identification
                    yield json.dumps({"type": "item", "ms": ms(), "index": n, "label": payload.detected.label if payload.detected else "",
                                      "box": [box.x0, box.y0, box.x1, box.y1] if box else None,
                                      "what": " ".join(x for x in (i.brand.value, i.model_name.value) if x) or i.subcategory,
                                      "photo_requests": [r.model_dump() for r in payload.photo_requests]}) + "\n"
                    pricing.add(asyncio.create_task(price_item(n, payload)))
                    n += 1
                else:
                    skipped = [s.label for s in payload.skipped]
                    yield json.dumps({"type": "found", "ms": ms(), "count": n, "skipped": skipped}) + "\n"
                    break
            for task in asyncio.as_completed(pricing):
                try:
                    yield json.dumps(await task, default=str) + "\n"
                except Exception as e:  # noqa: BLE001
                    yield json.dumps({"type": "error", "message": str(e)[:300]}) + "\n"
            await worker
            yield json.dumps({"type": "done", "ms": ms()}) + "\n"
        except Exception as e:  # noqa: BLE001
            log.exception("pile failed")
            yield json.dumps({"type": "error", "message": str(e)[:300]}) + "\n"

    return StreamingResponse(stream(), media_type="application/x-ndjson")


# ---------- connected accounts: the user's own sites, with consent ----------


class Consent(BaseModel):
    scopes: list[str] = ["search"]


@app.get("/api/accounts")
async def accounts():
    granted = consents().get(USER_ID)
    rows = []
    for r in RECIPES.values():
        rows.append({"site": r.name, "domain": r.domain, "connected": r.name in granted,
                     "scopes": granted.get(r.name, {}).get("scopes", []), "needs_login": r.login, "notes": r.notes})
    return {"user": USER_ID, "sites": rows, "never": NEVER}


@app.post("/api/accounts/{site}/consent")
async def grant(site: str, c: Consent):
    if site not in RECIPES:
        raise HTTPException(404, f"unknown site {site}")
    consents().grant(USER_ID, site, c.scopes)
    _log_event("consent", {"type": "consent", "site": site, "scopes": c.scopes})
    return {"ok": True}


@app.delete("/api/accounts/{site}/consent")
async def revoke(site: str):
    consents().revoke(USER_ID, site)
    _log_event("consent", {"type": "revoke", "site": site})
    return {"ok": True}


@app.post("/api/accounts/{site}/connect")
async def connect(site: str):
    """Sign in to a site as yourself. Hosted: a live view of your browser. Local: run `offload connect`."""
    p = provider()
    if isinstance(p, BrowserbaseProvider):
        s = await p.session(USER_ID)
        return {"live_view": await p.live_view_url(s["id"]), "open": f"https://www.{RECIPES[site].domain}/"}
    return {"connect_url": f"/connect/{site}"}


# ---------- sign in to your own accounts, in our browser, through a live view ----------

SIGN_IN = {
    "facebook": "https://www.facebook.com/login/?next=https%3A%2F%2Fwww.facebook.com%2Fmarketplace%2F",
    "poshmark": "https://poshmark.com/login",
    "mercari": "https://www.mercari.com/login/",
    "depop": "https://www.depop.com/login/",
    "grailed": "https://www.grailed.com/users/sign_up",
    "vinted": "https://www.vinted.com/member/signup/select_type",
    "liveauctioneers": "https://www.liveauctioneers.com/login/",
    "invaluable": "https://www.invaluable.com/login",
}


@app.get("/connect/{site}")
async def connect_page(site: str):
    if site not in RECIPES:
        raise HTTPException(404, f"unknown site {site}")
    return FileResponse(STATIC / "connect.html")


@app.websocket("/ws/connect/{site}")
async def connect_ws(ws: WebSocket, site: str):
    """Stream the agent's browser to the user so they sign in themselves; their session is kept
    (never their password). Clicks and typing come from the user's own taps."""
    if ACCESS_TOKEN and ws.cookies.get("offload_k") != ACCESS_TOKEN:
        await ws.close(code=4401)
        return
    await ws.accept()
    if site not in RECIPES:
        await ws.close(code=4404)
        return
    prov = provider()
    if not isinstance(prov, LocalProvider):
        await ws.send_json({"error": "live sign-in runs on the local browser provider"})
        await ws.close()
        return
    ctx = await prov.context(USER_ID, site)
    page = await ctx.new_page()
    await page.set_viewport_size({"width": 430, "height": 860})  # phone-shaped, so it fits a phone screen
    cdp = await ctx.new_cdp_session(page)
    frames: asyncio.Queue = asyncio.Queue(maxsize=2)

    def on_frame(params):
        asyncio.ensure_future(cdp.send("Page.screencastFrameAck", {"sessionId": params["sessionId"]}))
        if frames.full():
            try:
                frames.get_nowait()
            except asyncio.QueueEmpty:
                pass
        frames.put_nowait(params)

    cdp.on("Page.screencastFrame", on_frame)
    await cdp.send("Page.startScreencast", {"format": "jpeg", "quality": 60, "maxWidth": 860, "maxHeight": 1720})
    await page.goto(SIGN_IN.get(site, f"https://www.{RECIPES[site].domain}/"), wait_until="domcontentloaded")

    async def pump():
        while True:
            f = await frames.get()
            m = f["metadata"]
            await ws.send_json({"img": f["data"], "w": m["deviceWidth"], "h": m["deviceHeight"], "url": page.url})

    pumping = asyncio.create_task(pump())
    try:
        while True:
            msg = await ws.receive_json()
            kind = msg.get("type")
            if kind == "click":
                await page.mouse.click(float(msg["x"]), float(msg["y"]))
            elif kind == "type":
                await page.keyboard.type(str(msg.get("text", "")), delay=20)
            elif kind == "key":
                await page.keyboard.press(str(msg.get("key", "Enter")))
            elif kind == "scroll":
                await page.mouse.wheel(0, float(msg.get("dy", 400)))
            elif kind == "back":
                await page.go_back()
            elif kind == "done":
                await prov.save(USER_ID, site, ctx)
                consents().grant(USER_ID, site, msg.get("scopes") or ["search", "list"])
                _log_event("consent", {"type": "connect", "site": site})
                await ws.send_json({"connected": True})
                break
    except WebSocketDisconnect:
        pass
    finally:
        pumping.cancel()
        try:
            await cdp.send("Page.stopScreencast")
            await page.close()
        except Exception:  # noqa: BLE001
            pass
