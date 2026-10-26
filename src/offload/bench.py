"""The Find-it benchmark: real photos with known answers, scored on every rung of the ladder.

Folder layout (one subfolder per item, as uploaded to Drive):
    evals/benchmark/<item-id>/photo1.jpg, photo2.jpg, note.txt

`offload bench-init evals/benchmark` drafts benchmark.yaml from the folders (note.txt becomes the
truth name; correct it by hand). `offload bench evals/benchmark/benchmark.yaml` runs every item
through the engine and writes, per run:
    runs/<stamp>/<item>.json   every streamed event, with timings
    runs/<stamp>/summary.md    identity accuracy, rung coverage, latency
    runs/<stamp>/judge.json    the top results per rung, for people to judge exact / similar quality
Pile photos (kind: pile) are scored on item count and identities; see docs for the pile scope.
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .find.engine import FindSettings, Sources, find
from .find.ladder import words
from .images import load_photo
from .llm import LLM

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".heic", ".webp"}


def draft_benchmark(folder: Path) -> Path:
    entries = []
    for d in sorted(p for p in folder.iterdir() if p.is_dir() and p.name != "runs"):
        photos = sorted(str(p.relative_to(folder)) for p in d.iterdir() if p.suffix.lower() in IMAGE_EXT)
        if not photos:
            continue
        note = (d / "note.txt").read_text().strip() if (d / "note.txt").exists() else ""
        kind = "pile" if "pile" in d.name.lower() else "find"
        entries.append({
            "id": d.name,
            "kind": kind,
            "category": None,
            "photos": photos,
            "truth": {"name": note.splitlines()[0] if note else None, "brand": None, "model": None,
                      "exact_urls": [], "items": [] if kind == "pile" else None},
            "note": note,
        })
    out = folder / "benchmark.yaml"
    out.write_text(yaml.safe_dump(entries, sort_keys=False, allow_unicode=True))
    return out


@dataclass
class ItemScore:
    id: str
    brand_ok: bool | None
    model_ok: bool | None
    exact_new: int
    exact_used: int
    similar: int
    profile_ms: int | None
    first_result_ms: int | None
    final_ms: int | None
    failed_sources: dict = field(default_factory=dict)


def _match(truth: str | None, got: str | None, min_overlap: float = 0.6) -> bool | None:
    if not truth:
        return None
    t, g = words(truth), words(got)
    return bool(t) and len(t & g) / len(t) >= min_overlap


async def _run_item(entry: dict, base: Path, llm: LLM, sources: Sources, fs: FindSettings, out: Path) -> ItemScore:
    photos = [load_photo(base / p) for p in entry["photos"]]
    events, profile, final = [], None, None
    first_result_ms = None
    async for e in find(llm, photos=photos, sources=sources, fs=fs):
        clean = {k: v for k, v in e.items() if not k.startswith("_")}
        events.append(clean)
        if e["type"] == "profile":
            profile = e
        if e["type"] == "ladder" and first_result_ms is None:
            lad = e["ladder"]
            if lad["exact_new"] or lad["exact_used"] or lad["similar"]:
                first_result_ms = e["ms"]
        if e["type"] == "ladder" and e["stage"] == "final":
            final = e
    (out / f"{entry['id']}.json").write_text(json.dumps(events, indent=1, default=str))
    truth = entry.get("truth") or {}
    p = (profile or {}).get("profile", {})
    lad = (final or {}).get("ladder", {})
    return ItemScore(
        id=entry["id"],
        brand_ok=_match(truth.get("brand"), p.get("brand")),
        model_ok=_match(truth.get("model"), " ".join(filter(None, [p.get("model_name"), p.get("designer")]))),
        exact_new=len(lad.get("exact_new", [])),
        exact_used=len(lad.get("exact_used", [])),
        similar=len(lad.get("similar", [])),
        profile_ms=(profile or {}).get("ms"),
        first_result_ms=first_result_ms,
        final_ms=(final or {}).get("ms"),
        failed_sources=lad.get("sources_failed", {}),
    )


def _pct(xs: list[bool | None]) -> str:
    known = [x for x in xs if x is not None]
    return f"{100 * sum(known) / len(known):.0f}% of {len(known)}" if known else "n/a"


def _p(xs: list[int | None], q: float) -> str:
    vals = sorted(x for x in xs if x is not None)
    return f"{vals[min(len(vals) - 1, int(q * len(vals)))] / 1000:.1f}s" if vals else "n/a"


def run_benchmark(path: Path, llm: LLM, sources: Sources | None = None, fs: FindSettings | None = None) -> Path:
    entries = yaml.safe_load(path.read_text())
    base = path.parent
    out = base / "runs" / time.strftime("%Y%m%d-%H%M%S")
    out.mkdir(parents=True)
    sources = sources or Sources.from_settings(FindSettings())
    fs = fs or FindSettings()
    finds = [e for e in entries if e.get("kind", "find") != "pile"]

    async def go():
        return [await _run_item(e, base, llm, sources, fs, out) for e in finds]

    scores = asyncio.run(go())
    lines = [
        f"# Find-it benchmark · {out.name}",
        "",
        f"Items: {len(scores)} (piles are scored separately)",
        "",
        "| Measure | Result |",
        "|---|---|",
        f"| Brand right | {_pct([s.brand_ok for s in scores])} |",
        f"| Model / design right | {_pct([s.model_ok for s in scores])} |",
        f"| Found the exact item new | {_pct([s.exact_new > 0 for s in scores])} |",
        f"| Found the exact item used | {_pct([s.exact_used > 0 for s in scores])} |",
        f"| Returned similar pieces | {_pct([s.similar >= 3 for s in scores])} |",
        f"| Time to understand the item (median / p90) | {_p([s.profile_ms for s in scores], .5)} / {_p([s.profile_ms for s in scores], .9)} |",
        f"| Time to first result (median / p90) | {_p([s.first_result_ms for s in scores], .5)} / {_p([s.first_result_ms for s in scores], .9)} |",
        f"| Time to final ladder (median / p90) | {_p([s.final_ms for s in scores], .5)} / {_p([s.final_ms for s in scores], .9)} |",
        "",
        "Whether each \"exact\" is really exact, and whether \"similar\" is good, is judged by people from judge.json.",
        "",
        "| Item | Brand | Model | New | Used | Similar | Final | Failed sources |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for s in scores:
        mark = lambda v: "–" if v is None else ("✓" if v else "✗")  # noqa: E731
        lines.append(
            f"| {s.id} | {mark(s.brand_ok)} | {mark(s.model_ok)} | {s.exact_new} | {s.exact_used} | {s.similar} | "
            f"{(s.final_ms or 0) / 1000:.1f}s | {', '.join(s.failed_sources) or ''} |"
        )
    (out / "summary.md").write_text("\n".join(lines) + "\n")

    judge = []
    for e in finds:
        events = json.loads((out / f"{e['id']}.json").read_text())
        final = next((x for x in events if x["type"] == "ladder" and x.get("stage") == "final"), None)
        if not final:
            continue
        lad = final["ladder"]
        judge.append({
            "id": e["id"],
            "photos": e["photos"],
            "truth": e.get("truth"),
            "results": {rung: [{"url": r["listing"]["url"], "title": r["listing"]["title"],
                                "image": (r["listing"]["image_urls"] or [None])[0],
                                "price_cents": r["listing"]["price_cents"], "source": r["listing"]["source"]}
                               for r in lad[rung][:5]] for rung in ("exact_new", "exact_used", "similar")},
        })
    (out / "judge.json").write_text(json.dumps(judge, indent=1))
    return out
