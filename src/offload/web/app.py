"""The test app: Find it (buy side) and Photo -> listing (sell side) on one engine.

Run:  uvicorn offload.web.app:app --host 0.0.0.0 --port 8000
Needs ANTHROPIC_API_KEY; each of EBAY_CLIENT_ID/EBAY_CLIENT_SECRET, BRAVE_API_KEY, ETSY_API_KEY adds sources.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from offload.config import settings
from offload.find.engine import FindSettings, Sources, find, ladder_dict
from offload.find.profile import build_profile
from offload.find.router import RouterStats
from offload.images import load_photo
from offload.listing.compose import compose_listing
from offload.listing.from_ladder import price_from_ladder
from offload.llm import AnthropicLLM, LLM
from offload.vision.pipeline import _finish, identify_item

log = logging.getLogger("offload.web")
STATIC = Path(__file__).parent / "static"
MAX_PHOTOS = 4
MAX_BYTES = 15 * 1024 * 1024

app = FastAPI(title="Offload test app")
_state: dict = {}


def llm() -> LLM:
    if "llm" not in _state:
        _state["llm"] = AnthropicLLM()
    return _state["llm"]


def sources() -> Sources:
    if "sources" not in _state:
        _state["sources"] = Sources.from_settings(FindSettings())
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
async def api_find(photos: list[UploadFile] | None = File(None), text: str | None = Form(None)):
    pics = await _photos(photos)
    if not pics and not (text and text.strip()):
        raise HTTPException(400, "send a photo or a description")
    run_id = uuid.uuid4().hex[:12]

    async def stream():
        segment = None
        try:
            async for event in find(llm(), photos=pics, text=text, sources=sources()):
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


@app.post("/api/sell")
async def api_sell(photos: list[UploadFile] = File(...), speed: str = Form("balanced")):
    """Photo -> a listing draft for one-step sign-off, priced from the exact item's market."""
    pics = await _photos(photos)
    if not pics:
        raise HTTPException(400, "send at least one photo")
    run_id = uuid.uuid4().hex[:12]
    cfg = settings()

    ident_task = asyncio.create_task(asyncio.to_thread(identify_item, pics, llm(), cfg=cfg))
    profile = await asyncio.to_thread(build_profile, llm(), photos=pics, cfg=cfg)
    final = None
    async for event in find(llm(), photos=pics, sources=sources(), profile=profile):
        if event["type"] == "ladder" and event["stage"] == "final":
            final = event["_ladder"]
    ident = await ident_task
    analysis = _finish(None, ident, pics)
    price = price_from_ladder(final, ident.condition, speed) if final else None
    body: dict = {
        "run": run_id,
        "ready_to_list": analysis.ready_to_list,
        "photo_requests": [r.model_dump() for r in analysis.photo_requests],
        "flagged_fields": sorted(set(analysis.low_confidence + analysis.missing)),
        "market": ladder_dict(final) if final else None,
    }
    if price is None:
        body["draft"] = None
        body["price_note"] = "Not enough market data for this item yet; set a price on the sign-off screen."
    else:
        draft = compose_listing(analysis, price)
        body["draft"] = {
            **draft.public_view(),
            "hidden_minimum_cents": draft.floor_cents,
            "expected_cents": draft.expected_cents,
            "range_cents": [price.p10_cents, price.p90_cents],
            "package": draft.package.__dict__ if hasattr(draft.package, "__dict__") else str(draft.package),
            "price_confidence": price.confidence,
            "price_notes": price.notes,
            "comps": [{"title": c.title, "price_cents": c.price_cents, "url": c.url} for c in price.comps_used[:8]],
        }
    _log_event(run_id, {"type": "sell", **{k: v for k, v in body.items() if k != "market"}})
    return body
