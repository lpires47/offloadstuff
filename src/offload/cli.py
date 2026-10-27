"""offload: command line for the engine.

    offload identify PHOTO [--extra TAG_PHOTO ...] [--retail 250] [--speed balanced]
    offload label-draft PHOTOS_DIR --out evals/labels.yaml
    offload eval evals/labels.yaml
    offload simulate
    offload find PHOTO|--text "..."         (Find it from the command line)
    offload bench-init evals/benchmark      (draft benchmark.yaml from photo folders)
    offload bench evals/benchmark/benchmark.yaml
    offload serve [--port 8000]             (the test app)
    offload login --user USER --platform depop
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path


def _llm():
    from .config import settings
    from .llm import AnthropicLLM

    if not settings().has_api_key:
        sys.exit("Set ANTHROPIC_API_KEY (see .env.example).")
    return AnthropicLLM()


def cmd_identify(args) -> None:
    from .config import settings
    from .images import load_photo
    from .listing import compose_listing
    from .pricing import estimate_price
    from .vision.pipeline import add_photos, analyze_photo

    cfg = settings()
    llm = _llm()
    analysis = analyze_photo(load_photo(args.photo, cfg.max_image_edge), llm, context=args.note, cfg=cfg)
    if args.extra and len(analysis.items) == 1:
        analysis.items = [add_photos(analysis.items[0], [load_photo(p, cfg.max_image_edge) for p in args.extra], llm, cfg)]
    out = {"scene": analysis.detection.scene if analysis.detection else None, "items": []}
    for item in analysis.items:
        entry = {
            "identification": item.identification.model_dump(),
            "ready_to_list": item.ready_to_list,
            "missing": item.missing,
            "low_confidence": item.low_confidence,
            "ask_for": [r.model_dump() for r in item.photo_requests],
        }
        if args.retail:
            price = estimate_price([], item.identification.condition, args.speed, retail_cents=int(args.retail * 100))
            draft = compose_listing(item, price)
            entry["listing_draft"] = {**asdict(draft), "note": "price from retail fallback until comps are connected"}
        out["items"].append(entry)
    out["skipped_as_setting"] = [s.label for s in analysis.skipped]
    print(json.dumps(out, indent=2, default=str))


def cmd_eval(args) -> None:
    from .evals import run_eval

    out = run_eval(Path(args.labels), _llm())
    print((out / "report.md").read_text())
    print(f"Saved to {out}")


def cmd_label_draft(args) -> None:
    from .evals import draft_labels

    print(f"Wrote {draft_labels(Path(args.photos), _llm(), Path(args.out))}. Correct every field before running evals.")


def cmd_simulate(args) -> None:
    from .simulate import run_demo

    run_demo()


def cmd_login(args) -> None:
    from .posting.browser.sessions import interactive_login

    print(f"Saved session to {interactive_login(args.user, args.platform)}")


def cmd_find(args) -> None:
    import asyncio

    from .find.engine import FindSettings, Sources, find
    from .images import load_photo

    photos = [load_photo(p) for p in (args.photos or [])]

    async def go():
        async for e in find(_llm(), photos=photos, text=args.text, sources=Sources.from_settings(FindSettings())):
            e = {k: v for k, v in e.items() if not k.startswith("_")}
            if e["type"] == "ladder" and e["stage"] != "final":
                continue
            print(json.dumps(e, default=str) if args.json else _brief(e))

    asyncio.run(go())


def _brief(e: dict) -> str:
    if e["type"] == "profile":
        p = e["profile"]
        what = " ".join(x for x in (p["brand"], p["model_name"], p["variant"]) if x) or p["subcategory"]
        return f"[{e['ms']}ms] {what} · details: {'; '.join(d['detail'] for d in p['defining_details'])}"
    if e["type"] == "source":
        return f"[{e['ms']}ms] {e['source']}: {e.get('count', e.get('error'))}"
    if e["type"] == "ladder":
        lines = [f"[{e['ms']}ms] final ladder"]
        for rung in ("exact_new", "exact_used", "similar"):
            lines.append(f"  {rung}:")
            for r in e["ladder"][rung][:8]:
                l = r["listing"]
                price = f"${l['price_cents'] / 100:,.0f}" if l["price_cents"] else "?"
                lines.append(f"    {price:>8}  {l['source']:<22} {l['title'][:60]}  {r['price_badge'] or ''}")
        return "\n".join(lines)
    return json.dumps(e, default=str)


def cmd_bench_init(args) -> None:
    from .bench import draft_benchmark

    print(f"Wrote {draft_benchmark(Path(args.folder))}. Fill in brand, model and category for each item.")


def cmd_bench(args) -> None:
    from .bench import run_benchmark

    out = run_benchmark(Path(args.file), _llm())
    print((out / "summary.md").read_text())
    print(f"Saved to {out}")


def cmd_sites(args) -> None:
    """Every source: what it is, whether it's on, and (with --check) whether it answers right now."""
    import asyncio

    import httpx

    from .find.engine import FindSettings, Sources
    from .find.models import DefiningDetail, ItemProfile
    from .find.sources.base import SearchPlan
    from .find.sources.sites.registry import CONNECTORS, NOT_CONNECTED, enabled_names

    on = set(enabled_names())
    src = Sources.from_settings(FindSettings())
    rows = [("ebay (official API)", "on" if src.ebay else "needs EBAY_CLIENT_ID/SECRET"),
            ("etsy (official API)", "on" if src.etsy else "needs ETSY_API_KEY"),
            ("web search (Brave)", "on" if src.web else "needs BRAVE_API_KEY")]
    rows += [(f"{n} (direct)", "on" if n in on else "off: set OFFLOAD_ENABLED_SITES") for n in CONNECTORS]
    rows += [(f"{n}", f"not connected: {why}") for n, why in NOT_CONNECTED.items()]
    for name, status in rows:
        print(f"{name:<28} {status}")
    if not args.check:
        return
    q = args.query
    profile = ItemProfile(category="apparel", subcategory="jeans", brand=None, brand_confidence=0, model_name=None,
                          model_confidence=0, designer=None, variant=None, style_code=None, gtin=None, era=None,
                          materials=[], colors=[], attributes=[], defining_details=[DefiningDetail(detail=q, why="", must_match=True)],
                          exact_queries=[q], similar_queries=[], reproduction_risk="low", notes="")
    plan = SearchPlan(profile, [q], [])

    async def check():
        async with httpx.AsyncClient(timeout=8) as client:
            targets = [(n, CONNECTORS[n]()) for n in CONNECTORS if n in on]
            if src.ebay:
                targets.append(("ebay", src.ebay))
            if src.etsy:
                targets.append(("etsy", src.etsy))
            for name, conn in targets:
                try:
                    out = await conn.search(plan, client)
                    priced = sum(1 for x in out if x.price_cents)
                    print(f"  {name:<12} OK  {len(out)} results, {priced} priced, e.g. {out[0].title[:50] if out else '-'}")
                except Exception as e:  # noqa: BLE001
                    print(f"  {name:<12} FAIL {type(e).__name__}: {str(e)[:120]}")

    print(f"\nLive check for {q!r}:")
    asyncio.run(check())


def cmd_connect(args) -> None:
    """Sign in to a site yourself in a visible browser; we keep the session (never the password)
    and record your consent to search it as you."""
    import asyncio

    from .find.sources.asuser.providers import Consents, LocalProvider
    from .find.sources.asuser.recipes import RECIPES

    recipe = RECIPES[args.site]

    async def go():
        provider = LocalProvider(headless=False)
        try:
            ctx = await provider.context(args.user, recipe.name)
            page = await ctx.new_page()
            await page.goto(f"https://www.{recipe.domain}/")
            await asyncio.to_thread(input, f"Sign in to {recipe.domain} in the window, then press Enter here... ")
            await provider.save(args.user, recipe.name, ctx)
        finally:
            await provider.close()

    asyncio.run(go())
    Consents().grant(args.user, recipe.name, args.scopes)
    print(f"Connected {recipe.name} for {args.user} with consent to: {', '.join(args.scopes)}")


def cmd_serve(args) -> None:
    import uvicorn

    uvicorn.run("offload.web.app:app", host=args.host, port=args.port)


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="offload")
    sub = p.add_subparsers(required=True)

    s = sub.add_parser("identify", help="identify the item(s) in a photo")
    s.add_argument("photo")
    s.add_argument("--extra", nargs="*", help="more photos of the same item (tag, sole, flaw)")
    s.add_argument("--note", help="optional seller note")
    s.add_argument("--retail", type=float, help="current retail price in USD, to draft a listing before comps exist")
    s.add_argument("--speed", choices=["most", "balanced", "fast"], default="balanced")
    s.set_defaults(fn=cmd_identify)

    s = sub.add_parser("eval", help="run identification evals")
    s.add_argument("labels")
    s.set_defaults(fn=cmd_eval)

    s = sub.add_parser("label-draft", help="pre-fill labels for a folder of photos")
    s.add_argument("photos")
    s.add_argument("--out", default="evals/labels.yaml")
    s.set_defaults(fn=cmd_label_draft)

    s = sub.add_parser("simulate", help="run a multi-platform negotiation simulation (no network)")
    s.set_defaults(fn=cmd_simulate)

    s = sub.add_parser("login", help="sign in to a platform in a visible browser and save the session")
    s.add_argument("--user", required=True)
    s.add_argument("--platform", required=True)
    s.set_defaults(fn=cmd_login)

    s = sub.add_parser("find", help="Find it: the exact item new, used, and similar pieces")
    s.add_argument("photos", nargs="*")
    s.add_argument("--text", help="describe the item instead of (or as well as) photos")
    s.add_argument("--json", action="store_true", help="print every event as JSON")
    s.set_defaults(fn=cmd_find)

    s = sub.add_parser("bench-init", help="draft benchmark.yaml from a folder of item folders")
    s.add_argument("folder")
    s.set_defaults(fn=cmd_bench_init)

    s = sub.add_parser("bench", help="run the Find-it benchmark")
    s.add_argument("file")
    s.set_defaults(fn=cmd_bench)

    s = sub.add_parser("sites", help="list every source and whether it's on; --check queries them live")
    s.add_argument("--check", action="store_true")
    s.add_argument("--query", default="levis 501")
    s.set_defaults(fn=cmd_sites)

    s = sub.add_parser("connect", help="sign in to a site as yourself and allow searching it as you")
    s.add_argument("site")
    s.add_argument("--user", default="liselle")
    s.add_argument("--scopes", nargs="+", default=["search"])
    s.set_defaults(fn=cmd_connect)

    s = sub.add_parser("serve", help="run the test app")
    s.add_argument("--host", default="0.0.0.0")
    s.add_argument("--port", type=int, default=8000)
    s.set_defaults(fn=cmd_serve)

    args = p.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
