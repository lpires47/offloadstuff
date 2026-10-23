"""Identification evals on labeled photos: does the pipeline get brand, model, size... right?

labels.yaml (one entry per photo; see evals/labels.example.yaml):

    - photo: photos/atom-hoody.jpg
      extra_photos: [photos/atom-hoody-tag.jpg]   # optional: same item, more shots
      items:
        - brand: Arc'teryx
          model_name: Atom LT Hoody
          size: M
          gender: mens
          category: apparel
          condition: very_good
          colors: [black]
          box: [80, 60, 900, 950]                  # optional, 0-1000 grid; helps match items in piles

Run: offload eval evals/labels.yaml   ->   evals/runs/<timestamp>/report.md + results.json
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path

import yaml

from .config import Settings, settings as default_settings
from .images import Box, load_photo
from .llm import LLM
from .vision import prompts
from .vision.pipeline import ItemAnalysis, analyze_photo, add_photos

FIELDS = ("category", "brand", "model_name", "size", "gender", "condition", "color")
CONDITION_ORDER = ["new_with_tags", "new_without_tags", "like_new", "very_good", "good", "fair", "poor"]


def norm(s: str | None) -> str:
    if s is None:
        return ""
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    s = re.sub(r"['’`]", "", s.lower())
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(w for w in s.split() if w not in ("the", "a", "an"))


def similar(a: str | None, b: str | None, threshold: float = 0.85) -> bool:
    na, nb = norm(a), norm(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    # token-set comparison tolerates word order and small spelling differences ("hoody" / "hoodie")
    ta, tb = " ".join(sorted(set(na.split()))), " ".join(sorted(set(nb.split())))
    return SequenceMatcher(None, ta, tb).ratio() >= threshold


def predicted_fields(a: ItemAnalysis) -> dict:
    i = a.identification
    return {
        "category": i.category,
        "brand": i.brand.value,
        "model_name": i.model_name.value,
        "size": i.size.value,
        "gender": i.gender,
        "condition": i.condition,
        "color": i.colors[0] if i.colors else None,
        "_conf": {
            "brand": i.brand.confidence, "model_name": i.model_name.confidence, "size": i.size.confidence,
            "gender": i.gender_confidence, "condition": i.condition_confidence,
        },
    }


def score_field(name: str, label, pred) -> bool | None:
    """True/False, or None when the label doesn't specify this field."""
    if label in (None, "", []):
        return None
    if name == "color":
        label = label[0] if isinstance(label, list) else label
        return similar(label, pred, 0.8)
    if name in ("category", "gender", "condition"):
        return norm(label) == norm(pred)
    if name == "size":
        return norm(label).replace(" ", "") == norm(pred).replace(" ", "")
    return similar(label, pred)


@dataclass
class ItemResult:
    photo: str
    label: dict
    predicted: dict | None
    scores: dict = field(default_factory=dict)
    ready_to_list: bool | None = None
    photo_requests: list[str] = field(default_factory=list)


def _match(labels: list[dict], analyses: list[ItemAnalysis]) -> list[tuple[dict, ItemAnalysis | None]]:
    """Greedy matching: by box overlap when labeled, else by how many fields agree."""
    pairs: list[tuple[float, int, int]] = []
    for li, lab in enumerate(labels):
        for ai, an in enumerate(analyses):
            if lab.get("box") and an.detected:
                d = an.detected
                s = Box.clamp(*lab["box"]).iou(Box.clamp(d.x0, d.y0, d.x1, d.y1))
            else:
                pred = predicted_fields(an)
                s = sum(bool(score_field(f, lab.get(f if f != "color" else "colors"), pred.get(f))) for f in FIELDS) / len(FIELDS)
            pairs.append((s, li, ai))
    pairs.sort(reverse=True)
    used_l, used_a, out = set(), set(), {}
    for s, li, ai in pairs:
        if li in used_l or ai in used_a or s <= 0.1:
            continue
        used_l.add(li)
        used_a.add(ai)
        out[li] = analyses[ai]
    return [(lab, out.get(i)) for i, lab in enumerate(labels)]


def run_eval(labels_path: Path, llm: LLM, cfg: Settings | None = None, out_root: Path | None = None) -> Path:
    cfg = cfg or default_settings()
    base = labels_path.parent
    entries = yaml.safe_load(labels_path.read_text()) or []
    results: list[ItemResult] = []
    extra_preds = 0
    for entry in entries:
        photo = load_photo(base / entry["photo"], cfg.max_image_edge)
        analysis = analyze_photo(photo, llm, context=entry.get("context"), cfg=cfg)
        items = analysis.items
        if entry.get("extra_photos") and len(items) == 1:
            extra = [load_photo(base / p, cfg.max_image_edge) for p in entry["extra_photos"]]
            items = [add_photos(items[0], extra, llm, cfg)]
        matched = _match(entry["items"], items)
        extra_preds += max(0, len(items) - sum(1 for _, a in matched if a))
        for lab, an in matched:
            pred = predicted_fields(an) if an else None
            scores = {f: (score_field(f, lab.get(f if f != "color" else "colors"), pred.get(f)) if pred else False) for f in FIELDS}
            if pred and lab.get("condition") in CONDITION_ORDER and pred["condition"] in CONDITION_ORDER:
                scores["condition_within_one"] = abs(CONDITION_ORDER.index(lab["condition"]) - CONDITION_ORDER.index(pred["condition"])) <= 1
            results.append(ItemResult(entry["photo"], lab, pred, scores,
                                      an.ready_to_list if an else None,
                                      [r.shot for r in an.photo_requests] if an else []))

    out = (out_root or base / "runs") / datetime.now().strftime("%Y%m%d-%H%M%S")
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_text(json.dumps([asdict(r) for r in results], indent=2, default=str))
    (out / "report.md").write_text(report(results, extra_preds, cfg))
    return out


def report(results: list[ItemResult], extra_preds: int, cfg: Settings) -> str:
    lines = [
        "# Identification eval",
        f"Prompt {prompts.PROMPT_VERSION} · vision model {cfg.vision_model} · detect model {cfg.detect_model}",
        "",
        f"Items labeled: {len(results)} · found: {sum(r.predicted is not None for r in results)} · extra items predicted: {extra_preds}",
        "",
        "| Field | Accuracy | Labeled |",
        "| --- | --- | --- |",
    ]
    for f in (*FIELDS, "condition_within_one"):
        vals = [r.scores.get(f) for r in results if r.scores.get(f) is not None]
        if vals:
            lines.append(f"| {f} | {sum(vals) / len(vals):.0%} | {len(vals)} |")
    # Calibration: when the model is confident, is it right?
    lines += ["", "## Calibration (confidence ≥ 0.85)", "", "| Field | Accuracy when confident | n |", "| --- | --- | --- |"]
    for f in ("brand", "model_name", "size", "gender", "condition"):
        hits = [r.scores[f] for r in results if r.predicted and r.scores.get(f) is not None and r.predicted["_conf"][f] >= 0.85]
        if hits:
            lines.append(f"| {f} | {sum(hits) / len(hits):.0%} | {len(hits)} |")
    lines += ["", "## Misses", ""]
    for r in results:
        wrong = [f for f in FIELDS if r.scores.get(f) is False]
        if wrong:
            got = {f: (r.predicted or {}).get(f) for f in wrong}
            want = {f: r.label.get(f if f != "color" else "colors") for f in wrong}
            lines.append(f"- {r.photo}: wanted {want}, got {got}" + (f"; asked for {r.photo_requests}" if r.photo_requests else ""))
    return "\n".join(lines) + "\n"


def draft_labels(photos_dir: Path, llm: LLM, out: Path, cfg: Settings | None = None) -> Path:
    """Pre-fill labels with model guesses so a person only corrects them (much faster than typing)."""
    cfg = cfg or default_settings()
    entries = []
    for p in sorted(photos_dir.iterdir()):
        if p.suffix.lower() not in (".jpg", ".jpeg", ".png", ".heic", ".webp"):
            continue
        analysis = analyze_photo(load_photo(p, cfg.max_image_edge), llm, cfg=cfg)
        items = []
        for a in analysis.items:
            pf = predicted_fields(a)
            d = a.detected
            items.append({
                "brand": pf["brand"], "model_name": pf["model_name"], "size": pf["size"], "gender": pf["gender"],
                "category": pf["category"], "condition": pf["condition"], "colors": a.identification.colors[:2],
                **({"box": [d.x0, d.y0, d.x1, d.y1]} if d and len(analysis.items) > 1 else {}),
            })
        entries.append({"photo": str(p.relative_to(out.parent)) if p.is_relative_to(out.parent) else str(p), "items": items,
                        "notes": "MODEL DRAFT: correct every field before using as ground truth"})
    out.write_text(yaml.safe_dump(entries, sort_keys=False, allow_unicode=True))
    return out
