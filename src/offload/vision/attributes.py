"""What to capture about each kind of product: the attributes buyers filter on, that tell look-alikes
apart, that move price, or that decide fit. The model fills the template for the item's type, plus
anything else that matters for this particular piece.

Each attribute says why it matters: identity (tells this model from others), similar (what a
"similar" suggestion must share), price (moves value), fit (decides whether it works for the buyer).
Names follow marketplace item-specifics where they exist (eBay aspects, Poshmark/Depop fields).
"""

from __future__ import annotations

import re

from pydantic import BaseModel, Field


class ProductAttribute(BaseModel):
    name: str = Field(description="Attribute name from the template for this product type, or a clear new one.")
    value: str | None = Field(description="Value as a buyer would say it, with units, e.g. '31 in', 'high rise'. Null if not determinable.")
    confidence: float = Field(description="0-1, calibrated.")
    evidence: str = Field(description="What shows it: 'tag reads W30', 'measured against the 12 in ruler', 'visible in photo 2'.")
    source: str = Field(description="One of: tag, measured, product_spec, visible, estimated.")


# type -> list of (attribute, why it matters). Keep each list to what a specialist would actually check.
TEMPLATES: dict[str, list[tuple[str, str]]] = {
    "jeans": [("rise", "fit, similar"), ("leg shape", "fit, similar"), ("wash", "identity, similar"),
              ("waist", "fit"), ("inseam", "fit"), ("leg opening", "fit"), ("fabric", "price"),
              ("stretch", "fit"), ("selvedge", "price, identity"), ("closure", "identity"),
              ("pocket count", "identity"), ("made in", "price, identity"), ("distressing", "similar")],
    "pants": [("rise", "fit"), ("leg shape", "fit, similar"), ("waist", "fit"), ("inseam", "fit"),
              ("fabric", "price, similar"), ("pleats", "similar"), ("closure", "identity"), ("pocket count", "identity")],
    "top": [("neckline", "similar"), ("sleeve length", "similar"), ("fit", "fit"), ("fabric", "price, similar"),
            ("pattern", "similar"), ("pit to pit", "fit"), ("length", "fit"), ("closure", "identity")],
    "knitwear": [("knit type", "similar"), ("fiber content", "price"), ("gauge", "similar"), ("neckline", "similar"),
                 ("pit to pit", "fit"), ("length", "fit"), ("pilling", "price")],
    "dress": [("silhouette", "similar"), ("length", "similar, fit"), ("neckline", "similar"), ("sleeve length", "similar"),
              ("fabric", "price, similar"), ("pattern", "similar"), ("closure", "identity"), ("lined", "price")],
    "skirt": [("silhouette", "similar"), ("length", "similar, fit"), ("waist", "fit"), ("fabric", "price"), ("pattern", "similar")],
    "outerwear": [("type", "similar"), ("shell fabric", "price, identity"), ("insulation", "price, identity"),
                  ("fill power", "price, identity"), ("hood", "identity, similar"), ("closure", "identity"),
                  ("pocket count", "identity"), ("pit to pit", "fit"), ("length", "fit, similar"),
                  ("hardware color", "identity"), ("lining", "price")],
    "sneakers": [("style code", "identity"), ("colorway", "identity, similar"), ("size", "fit, price"),
                 ("size system", "fit"), ("upper material", "identity"), ("sole condition", "price"),
                 ("original box", "price"), ("insoles", "price"), ("yellowing", "price")],
    "shoes": [("type", "similar"), ("heel height", "similar, fit"), ("toe shape", "similar"), ("upper material", "price, similar"),
              ("sole material", "identity"), ("size", "fit"), ("width", "fit"), ("closure", "identity"), ("made in", "price")],
    "bag": [("style", "similar"), ("width", "similar, fit"), ("height", "similar"), ("depth", "similar"),
            ("material", "price, identity"), ("hardware color", "identity"), ("strap type", "similar"),
            ("strap drop", "fit"), ("closure", "identity"), ("interior pockets", "identity"), ("date code or serial", "identity, price"),
            ("dust bag", "price"), ("corner wear", "price")],
    "jewelry": [("metal", "price"), ("purity mark", "price, identity"), ("stone", "price"), ("length or size", "fit"),
                ("clasp", "identity"), ("maker's mark", "identity, price"), ("weight", "price")],
    "watch": [("reference number", "identity"), ("case diameter", "fit, identity"), ("case material", "price"),
              ("movement", "price, identity"), ("dial color", "identity"), ("bracelet or strap", "identity"),
              ("box and papers", "price"), ("serial", "identity")],
    "chair": [("seat height", "fit"), ("overall height", "fit, similar"), ("width", "fit"), ("depth", "fit"),
              ("frame material", "similar, price"), ("seat material", "similar"), ("arms", "similar"),
              ("base type", "similar"), ("stackable", "similar"), ("maker's mark or label", "identity, price"),
              ("upholstery condition", "price"), ("set size", "price")],
    "sofa": [("width", "fit"), ("depth", "fit"), ("height", "fit"), ("seat height", "fit"), ("seat count", "similar"),
             ("arm style", "similar"), ("upholstery", "similar, price"), ("frame", "price"), ("cushions", "similar"),
             ("modular", "similar"), ("legs", "similar"), ("label", "identity, price")],
    "table": [("type", "similar"), ("top shape", "similar"), ("length or diameter", "fit"), ("width", "fit"),
              ("height", "fit"), ("top material", "similar, price"), ("base type", "similar"), ("leaves", "fit, price"),
              ("seats", "fit"), ("maker's mark", "identity, price")],
    "storage": [("type", "similar"), ("width", "fit"), ("height", "fit"), ("depth", "fit"), ("material", "price, similar"),
                ("drawer count", "similar, identity"), ("hardware", "identity"), ("joinery", "price, identity"),
                ("maker's mark", "identity, price")],
    "lamp": [("type", "similar"), ("height", "fit, similar"), ("shade material", "similar"), ("shade diameter", "fit"),
             ("base material", "similar, price"), ("finish", "similar"), ("bulb socket", "identity"),
             ("wiring", "price"), ("maker's label", "identity, price")],
    "rug": [("width", "fit"), ("length", "fit"), ("construction", "price, identity"), ("fiber", "price"),
            ("pile height", "similar"), ("pattern", "similar"), ("origin", "price, identity"), ("knot density", "price")],
    "mirror": [("width", "fit"), ("height", "fit"), ("shape", "similar"), ("frame material", "similar, price"), ("maker", "identity")],
    "art": [("medium", "price"), ("width", "fit"), ("height", "fit"), ("framed", "price"), ("signed", "price, identity"),
            ("edition", "price, identity"), ("artist", "identity, price")],
    "decor": [("material", "similar, price"), ("height", "fit"), ("width", "fit"), ("color", "similar"),
              ("maker's mark", "identity, price"), ("period", "price, similar")],
}

ALIASES = {
    "denim": "jeans", "trousers": "pants", "shirt": "top", "t-shirt": "top", "blouse": "top", "sweater": "knitwear",
    "cardigan": "knitwear", "jacket": "outerwear", "coat": "outerwear", "parka": "outerwear", "boots": "shoes",
    "heels": "shoes", "sandals": "shoes", "loafers": "shoes", "trainers": "sneakers", "handbag": "bag", "tote": "bag",
    "necklace": "jewelry", "ring": "jewelry", "bracelet": "jewelry", "earrings": "jewelry", "stool": "chair",
    "armchair": "chair", "bench": "chair", "couch": "sofa", "loveseat": "sofa", "desk": "table", "dresser": "storage",
    "credenza": "storage", "sideboard": "storage", "bookcase": "storage", "shelf": "storage", "cabinet": "storage",
    "sconce": "lamp", "pendant": "lamp", "chandelier": "lamp", "print": "art", "painting": "art", "vase": "decor",
}


def template_for(subcategory: str) -> list[tuple[str, str]]:
    """Match on whole words (so 'laptop stand' isn't a top), last word first: 'chair cushion' is decor-ish,
    'side chair' is a chair."""
    words = re.findall(r"[a-z\-]+", subcategory.lower())
    for w in reversed(words):
        for cand in (w, w.rstrip("s")):
            if cand in TEMPLATES:
                return TEMPLATES[cand]
            if cand in ALIASES:
                return TEMPLATES[ALIASES[cand]]
    return []


def prompt_block() -> str:
    """All templates, compactly, for the model to pick from (a few hundred tokens)."""
    lines = ["Attribute templates by product type (fill the one that fits; add others that matter):"]
    for key, attrs in TEMPLATES.items():
        lines.append(f"- {key}: " + ", ".join(a for a, _ in attrs))
    lines.append(
        "Measurements: only from a tag, a known product spec, or a measuring reference in the photo; "
        "otherwise give an estimate with source 'estimated' and low confidence. Never invent a code or serial."
    )
    return "\n".join(lines)


def why(subcategory: str, attribute: str) -> str:
    return dict(template_for(subcategory)).get(attribute.lower(), "")
