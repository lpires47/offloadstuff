"""Photo -> items -> identifications, plus the rules that decide what's ready to list.

Flow for one photo:
    detect (cheap model)  ->  for each candidate item: crop + identify (best vision model)
                          ->  readiness rules (code, not model): what's missing, which shot to ask for

A single-item photo skips cropping and is identified from the full frame.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field

from PIL import ImageDraw

from ..config import Settings, settings as default_settings
from ..images import Box, Photo
from ..llm import LLM
from . import prompts
from .schema import Detection, DetectedItem, Identification, PhotoRequest

# Per-field confidence needed before we autofill it without flagging it to the seller.
AUTOFILL_MIN_CONFIDENCE = {
    "brand": 0.85,
    "model_name": 0.75,
    "size": 0.9,
    "condition": 0.7,
    "gender": 0.8,
    "material": 0.7,
}

# Fields a listing can't go live without, by category. Size is required where buyers filter on it.
REQUIRED_FIELDS = {
    "apparel": ("brand", "size", "gender", "condition"),
    "footwear": ("brand", "size", "gender", "condition"),
    "bags": ("brand", "condition"),
    "watches": ("brand", "model_name", "condition"),
    "electronics": ("brand", "model_name", "condition"),
}
DEFAULT_REQUIRED = ("condition",)

# Which shot best resolves each missing field.
SHOT_FOR_FIELD = {
    "brand": ("brand_tag", "To confirm the brand"),
    "model_name": ("serial_or_model_number", "To pin down the exact model"),
    "size": ("size_tag", "To confirm the size"),
    "gender": ("size_tag", "To confirm men's or women's sizing"),
    "condition": ("flaw_closeup", "To show the condition up close"),
}


@dataclass
class ItemAnalysis:
    detected: DetectedItem | None
    identification: Identification
    photos: list[Photo]
    low_confidence: list[str] = field(default_factory=list)  # fields to flag on the approval card
    missing: list[str] = field(default_factory=list)  # required fields we couldn't fill
    photo_requests: list[PhotoRequest] = field(default_factory=list)

    @property
    def ready_to_list(self) -> bool:
        # High authenticity risk always goes to a person, never straight to a listing.
        return not self.missing and self.identification.authenticity_risk != "high"


@dataclass
class PhotoAnalysis:
    detection: Detection | None
    items: list[ItemAnalysis]
    skipped: list[DetectedItem] = field(default_factory=list)  # setting / not-for-sale boxes


def _field_confidence(ident: Identification, name: str) -> tuple[bool, float]:
    """(has_value, confidence) for a readiness-checked field."""
    if name == "condition":
        return ident.condition != "unknown", ident.condition_confidence
    if name == "gender":
        known = ident.gender not in ("unknown",)
        return known, ident.gender_confidence
    if name == "material":
        return ident.material.value is not None, ident.material.confidence
    attr = getattr(ident, name)
    return attr.value is not None and str(attr.value).strip() != "", attr.confidence


def assess(ident: Identification) -> tuple[list[str], list[str], list[PhotoRequest]]:
    """Return (missing_required, low_confidence, photo_requests) for an identification."""
    required = REQUIRED_FIELDS.get(ident.category, DEFAULT_REQUIRED)
    if ident.category in ("apparel", "footwear") and ident.size_system == "one_size":
        required = tuple(f for f in required if f != "size")
    missing, low = [], []
    for name, threshold in AUTOFILL_MIN_CONFIDENCE.items():
        has, conf = _field_confidence(ident, name)
        if name in required and (not has or conf < threshold):
            missing.append(name)
        elif has and conf < threshold:
            low.append(name)

    # Every missing required field gets the shot that resolves it, whatever the count: those block
    # listing. Optional asks (authenticity, the model's own suggestions) only fill up to two in total.
    required_asks: list[PhotoRequest] = []
    seen: set[str] = set()
    for name in missing:
        shot, reason = SHOT_FOR_FIELD[name]
        if shot not in seen:
            required_asks.append(PhotoRequest(shot=shot, reason=reason))
            seen.add(shot)
    optional: list[PhotoRequest] = []
    if ident.authenticity_risk in ("check", "high") and "brand_tag" not in seen:
        optional.append(PhotoRequest(shot="brand_tag", reason="To check authenticity"))
        seen.add("brand_tag")
    for req in ident.photo_requests:
        if req.shot not in seen:
            optional.append(req)
            seen.add(req.shot)
    return missing, low, required_asks + optional[: max(0, 2 - len(required_asks))]


def identify_item(
    photos: Sequence[Photo],
    llm: LLM,
    *,
    context: str | None = None,
    overview: Photo | None = None,
    cfg: Settings | None = None,
) -> Identification:
    """Identify one item from one or more photos of it. `overview` is the full scene with the item boxed."""
    cfg = cfg or default_settings()
    content: list[dict] = [p.content_block() for p in photos]
    if overview is not None:
        content.append(overview.content_block())
    content.append(
        {"type": "text", "text": prompts.identify_user_text(context, len(photos), boxed=overview is not None)}
    )
    return llm.parse(
        model=cfg.vision_model,
        system=prompts.IDENTIFY_SYSTEM,
        content=content,
        output_model=Identification,
        max_tokens=4096,
    )


def detect_items(photo: Photo, llm: LLM, cfg: Settings | None = None) -> Detection:
    cfg = cfg or default_settings()
    return llm.parse(
        model=cfg.detect_model,
        system=prompts.DETECT_SYSTEM,
        content=[
            photo.content_block(),
            {"type": "text", "text": f"The image is {photo.size[0]}x{photo.size[1]} pixels. List the items in it."},
        ],
        output_model=Detection,
        max_tokens=4096,
    )


def _outlined(photo: Photo, box: Box) -> Photo:
    img = photo.image.copy()
    img.thumbnail((1024, 1024))
    w, h = img.size
    draw = ImageDraw.Draw(img)
    width = max(3, w // 200)
    draw.rectangle((box.x0 * w / 1000, box.y0 * h / 1000, box.x1 * w / 1000, box.y1 * h / 1000), outline=(255, 0, 0), width=width)
    return Photo(img, photo.sha256, photo.source + "#overview")


def box_of(item: DetectedItem, photo: Photo | None = None) -> Box:
    """The model answers in pixels of the image it saw (Claude localizes worse on normalized grids);
    we convert to our 0-1000 grid. Without the photo, coordinates are taken as already on the grid."""
    coords = (item.x0, item.y0, item.x1, item.y1)
    if photo is not None:
        w, h = photo.size
        coords = (item.x0 * 1000 / w, item.y0 * 1000 / h, item.x1 * 1000 / w, item.y1 * 1000 / h)
    return Box.clamp(*coords)


def _dedupe(items: list[DetectedItem], photo: Photo, iou_threshold: float = 0.7) -> list[DetectedItem]:
    kept: list[DetectedItem] = []
    for item in items:
        box = box_of(item, photo)
        if all(box.iou(box_of(k, photo)) < iou_threshold for k in kept):
            kept.append(item)
    return kept


def _finish(detected: DetectedItem | None, ident: Identification, photos: list[Photo]) -> ItemAnalysis:
    missing, low, requests = assess(ident)
    return ItemAnalysis(detected, ident, photos, low_confidence=low, missing=missing, photo_requests=requests)


def analyze_photo(
    photo: Photo,
    llm: LLM,
    *,
    context: str | None = None,
    cfg: Settings | None = None,
    max_workers: int = 6,
    on_item: Callable[[ItemAnalysis], None] | None = None,
) -> PhotoAnalysis:
    """One photo of one item or a pile -> an analysis per item. No mode switch: the photo decides."""
    cfg = cfg or default_settings()
    detection = detect_items(photo, llm, cfg)
    candidates = _dedupe([i for i in detection.items if i.is_for_sale_candidate], photo)
    skipped = [i for i in detection.items if not i.is_for_sale_candidate]

    if detection.scene == "no_items" or not candidates:
        return PhotoAnalysis(detection, [], skipped)

    if detection.scene == "single_item" and len(candidates) == 1:
        ident = identify_item([photo], llm, context=context, cfg=cfg)
        return PhotoAnalysis(detection, [_finish(candidates[0], ident, [photo])], skipped)

    def work(item: DetectedItem) -> ItemAnalysis:
        box = box_of(item, photo)
        crop = photo.crop(box)
        ident = identify_item([crop], llm, overview=_outlined(photo, box), cfg=cfg)
        return _finish(item, ident, [crop])

    # Items stream out as each is identified (on_item), but the result keeps reading order.
    results: dict[int, ItemAnalysis] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(work, item): n for n, item in enumerate(candidates)}
        for fut in as_completed(futures):
            results[futures[fut]] = fut.result()
            if on_item is not None:
                on_item(results[futures[fut]])
    return PhotoAnalysis(detection, [results[n] for n in range(len(candidates))], skipped)


def add_photos(analysis: ItemAnalysis, new_photos: Sequence[Photo], llm: LLM, cfg: Settings | None = None) -> ItemAnalysis:
    """The seller took the extra shot we asked for: re-identify with all photos of the item."""
    photos = [*analysis.photos, *new_photos]
    ident = identify_item(photos, llm, cfg=cfg)
    return _finish(analysis.detected, ident, photos)
