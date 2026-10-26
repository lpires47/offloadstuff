"""Find it, end to end: photo or words in, a stream of events out, ending in the verified ladder.

Timeline for a photo (each step streams to the screen as it lands):
  t=0      eBay search-by-image fires (needs no identification)
  ~3-5s    item profile: what it is and the details that define it
  +0-4s    each source answers on its own clock; a text-ranked preliminary ladder after each one
  +3-6s    vision check of the shortlist -> the final ladder: exact new, exact used, similar
"""

from __future__ import annotations

import asyncio
import os
import time
from collections.abc import AsyncIterator, Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path

import httpx

from offload.config import Settings, settings as default_settings
from offload.images import Photo, load_photo
from offload.llm import LLM

from . import ladder as L
from .models import ItemProfile, Ladder, Listing, Result
from .profile import build_profile
from .router import RouterStats, load_shopify_stores, route
from .sources.base import SearchPlan, Source
from .sources.ebay import EbayBrowse
from .sources.etsy import EtsySource
from .sources.shopify import ShopifyStores
from .sources.websearch import BraveSearch, WebSearchSource


@dataclass
class FindSettings:
    ebay_app_id: str = field(default_factory=lambda: os.environ.get("EBAY_CLIENT_ID", ""))
    ebay_cert_id: str = field(default_factory=lambda: os.environ.get("EBAY_CLIENT_SECRET", ""))
    etsy_api_key: str = field(default_factory=lambda: os.environ.get("ETSY_API_KEY", ""))
    brave_api_key: str = field(default_factory=lambda: os.environ.get("BRAVE_API_KEY", ""))
    shopify_stores_file: Path = field(
        default_factory=lambda: Path(os.environ.get("OFFLOAD_SHOPIFY_STORES", "data/shopify_stores.txt"))
    )
    router_stats_file: Path = field(
        default_factory=lambda: Path(os.environ.get("OFFLOAD_ROUTER_STATS", "data/router_stats.json"))
    )
    source_timeout_s: float = 6.0
    shortlist_size: int = 32
    verify_batch: int = 8


@dataclass
class Sources:
    """Whatever is configured. Missing keys just mean fewer sources, never a crash."""

    ebay: EbayBrowse | None = None
    etsy: EtsySource | None = None
    web: BraveSearch | None = None
    shopify: ShopifyStores | None = None
    extra: list[Source] = field(default_factory=list)  # tests and future connectors

    @classmethod
    def from_settings(cls, fs: FindSettings) -> "Sources":
        return cls(
            ebay=EbayBrowse(fs.ebay_app_id, fs.ebay_cert_id) if fs.ebay_app_id and fs.ebay_cert_id else None,
            etsy=EtsySource(fs.etsy_api_key) if fs.etsy_api_key else None,
            web=BraveSearch(fs.brave_api_key) if fs.brave_api_key else None,
            shopify=ShopifyStores(),
        )


# ---------- serialization for the stream ----------


def listing_dict(x: Listing) -> dict:
    d = asdict(x)
    d["fetched_at"] = x.fetched_at.isoformat()
    return d


def ladder_dict(ladder: Ladder) -> dict:
    def res(r: Result) -> dict:
        return {
            "listing": listing_dict(r.listing),
            "rung": r.rung,
            "confidence": round(r.confidence, 2),
            "reason": r.reason,
            "matched_details": r.matched_details,
            "price_badge": r.price_badge,
        }

    return {
        "exact_new": [res(r) for r in ladder.exact_new],
        "exact_used": [res(r) for r in ladder.exact_used],
        "similar": [res(r) for r in ladder.similar[:30]],
        "typical_used_cents": ladder.typical_used_cents,
        "sources_searched": ladder.sources_searched,
        "sources_failed": ladder.sources_failed,
    }


# ---------- the run ----------


async def _thumb(url: str, client: httpx.AsyncClient) -> Photo | None:
    try:
        r = await client.get(url, timeout=2.5, follow_redirects=True)
        if r.status_code != 200 or not r.headers.get("content-type", "").startswith("image/"):
            return None
        return load_photo(r.content, max_edge=512)
    except (httpx.HTTPError, OSError, ValueError):
        return None


async def find(
    llm: LLM,
    *,
    photos: Sequence[Photo] = (),
    text: str | None = None,
    sources: Sources,
    fs: FindSettings | None = None,
    cfg: Settings | None = None,
    client: httpx.AsyncClient | None = None,
    profile: ItemProfile | None = None,
) -> AsyncIterator[dict]:
    fs = fs or FindSettings()
    cfg = cfg or default_settings()
    own_client = client is None
    client = client or httpx.AsyncClient(timeout=fs.source_timeout_s, http2=False)
    t0 = time.perf_counter()
    ms = lambda: int((time.perf_counter() - t0) * 1000)  # noqa: E731
    pool: list[Listing] = []
    searched: list[str] = []
    failed: dict[str, str] = {}

    async def run(name: str, coro) -> tuple[str, list[Listing] | Exception]:
        try:
            return name, await asyncio.wait_for(coro, fs.source_timeout_s)
        except Exception as e:  # noqa: BLE001 - a source failing must not sink the search
            return name, e

    pending: set[asyncio.Task] = set()
    try:
        photo = photos[0] if photos else None
        if photo is not None and sources.ebay is not None:
            pending.add(asyncio.create_task(run("ebay:image", sources.ebay.search_by_image(photo, client))))

        if profile is None:
            profile = await asyncio.to_thread(build_profile, llm, photos=photos, text=text, cfg=cfg)
        yield {"type": "profile", "ms": ms(), "profile": profile.model_dump()}

        stats = RouterStats.load(fs.router_stats_file) if fs.router_stats_file.exists() else None
        rt = route(profile, stats, load_shopify_stores(fs.shopify_stores_file))
        yield {"type": "route", "ms": ms(), "segment": rt.segment, "groups": rt.resale_groups}

        plan = SearchPlan(
            profile=profile,
            exact_queries=profile.exact_queries,
            similar_queries=profile.similar_queries,
            photo=None,  # image search already running
            shopify_stores=rt.shopify_stores,
        )
        if sources.ebay is not None:
            pending.add(asyncio.create_task(run("ebay", sources.ebay.search(plan, client))))
        if sources.etsy is not None:
            pending.add(asyncio.create_task(run("etsy", sources.etsy.search(plan, client))))
        if sources.shopify is not None and plan.shopify_stores:
            pending.add(asyncio.create_task(run("shopify", sources.shopify.search(plan, client))))
        if sources.web is not None:
            for group in rt.resale_groups:
                ws = WebSearchSource(f"web:{'+'.join(group)}", sources.web, domains=group, group="resale")
                pending.add(asyncio.create_task(run(ws.name, ws.search(plan, client))))
            if profile.exact_queries:
                retail = WebSearchSource("web:retail", sources.web, domains=[], group="retail")
                pending.add(asyncio.create_task(run("web:retail", retail.search(plan, client))))
        for src in sources.extra:
            pending.add(asyncio.create_task(run(src.name, src.search(plan, client))))

        while pending:
            done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                name, got = task.result()
                if isinstance(got, Exception):
                    failed[name] = f"{type(got).__name__}: {got}"[:200]
                    yield {"type": "source", "ms": ms(), "source": name, "error": failed[name]}
                    continue
                searched.append(name)
                pool.extend(got)
                yield {"type": "source", "ms": ms(), "source": name, "count": len(got)}
            prelim = L.preliminary(profile, pool)
            prelim.sources_searched, prelim.sources_failed = list(searched), dict(failed)
            yield {"type": "ladder", "stage": "preliminary", "ms": ms(), "ladder": ladder_dict(prelim)}

        shortlist = L.shortlist(profile, pool, fs.shortlist_size)
        urls = {x.key: x.image_urls[0] for x in shortlist if x.image_urls}
        got = await asyncio.gather(*(_thumb(u, client) for u in urls.values()))
        thumbs = {k: p for k, p in zip(urls, got) if p is not None}

        batches = [shortlist[i : i + fs.verify_batch] for i in range(0, len(shortlist), fs.verify_batch)]

        async def check(offset: int, batch: list[Listing]):
            verdicts = await asyncio.to_thread(
                L.verify, profile, batch, llm, shopper_photos=photos, thumbs=thumbs, batch_size=len(batch), cfg=cfg
            )
            for v in verdicts:
                v.index += offset
            return verdicts

        all_verdicts = []
        results = await asyncio.gather(
            *(check(i * fs.verify_batch, b) for i, b in enumerate(batches)), return_exceptions=True
        )
        for r in results:
            if isinstance(r, Exception):
                failed["verify"] = f"{type(r).__name__}: {r}"[:200]
            else:
                all_verdicts += r
        final = L.final(profile, shortlist, all_verdicts) if all_verdicts else L.preliminary(profile, pool)
        final.sources_searched, final.sources_failed = list(searched), dict(failed)
        # "_ladder" carries the object for in-process callers (the sell flow); the web layer drops it.
        yield {"type": "ladder", "stage": "final", "ms": ms(), "ladder": ladder_dict(final), "_ladder": final}
        yield {"type": "done", "ms": ms()}
    finally:
        for task in pending:  # the shopper left: stop working for them
            task.cancel()
        if own_client:
            await client.aclose()
