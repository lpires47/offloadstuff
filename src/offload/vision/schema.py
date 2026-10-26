"""Structured outputs for detection and identification.

The model fills these; our code makes every decision downstream (what to ask for, what's ready to
list). Each important attribute carries a confidence and the visual evidence behind it, so we can
gate autofill on confidence the way eBay's bulk tool does, and show the seller *why*.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Category = Literal[
    "apparel",
    "footwear",
    "bags",
    "accessories",
    "jewelry",
    "watches",
    "electronics",
    "home_decor",
    "furniture",
    "kitchen",
    "books_media",
    "toys_games",
    "collectibles",
    "sports_outdoors",
    "beauty",
    "other",
]

Condition = Literal[
    "new_with_tags",
    "new_without_tags",
    "like_new",
    "very_good",
    "good",
    "fair",
    "poor",
    "unknown",
]

Gender = Literal["mens", "womens", "unisex", "boys", "girls", "baby", "not_applicable", "unknown"]

Shot = Literal[
    "brand_tag",
    "size_tag",
    "care_label",
    "sole",
    "serial_or_model_number",
    "flaw_closeup",
    "front",
    "back",
    "inside",
    "hardware",
    "laid_flat_with_scale",
    "packaging",
]


# ---------- detection (one photo -> which things are in it) ----------


class DetectedItem(BaseModel):
    id: str = Field(description="Short id, i1, i2, ... in reading order (left to right, top to bottom).")
    label: str = Field(description="Plain description, e.g. 'black hooded synthetic jacket'. No brand guesses here.")
    x0: int = Field(description="Left edge, in pixels of the image as sent.")
    y0: int = Field(description="Top edge, in pixels.")
    x1: int = Field(description="Right edge, in pixels.")
    y1: int = Field(description="Bottom edge, in pixels.")
    is_for_sale_candidate: bool = Field(
        description="False for things that are clearly the setting, not the goods: the bed, floor, table, "
        "hangers, people, pets, walls."
    )
    visibility: Literal["clear", "partly_hidden", "mostly_hidden"]
    count: int = Field(description="Units in this box: 1 normally; 2 for a pair of shoes counts as 1 item.")


class Detection(BaseModel):
    scene: Literal["single_item", "multiple_items", "no_items"]
    items: list[DetectedItem]
    photo_issues: list[Literal["blurry", "too_dark", "glare", "too_far", "cropped_off", "cluttered"]] = Field(
        description="Problems with the photo itself that hurt identification."
    )


# ---------- identification (one item -> what exactly it is) ----------


class Attr(BaseModel):
    value: str | None = Field(description="The value, or null if it cannot be determined from the photos.")
    confidence: float = Field(description="0-1. Calibrated: 0.9 means you'd be wrong 1 time in 10.")
    evidence: str = Field(description="What in the photo supports this, e.g. 'size tag reads M'. Empty if null.")


class Candidate(BaseModel):
    brand: str | None
    model_name: str | None
    confidence: float


class Flaw(BaseModel):
    kind: Literal[
        "stain", "hole", "tear", "pilling", "fading", "scuff", "scratch", "crease", "yellowing",
        "missing_part", "broken_hardware", "odor_unknown", "repair", "other",
    ]
    location: str = Field(description="Where on the item, e.g. 'left cuff'.")
    severity: Literal["minor", "moderate", "major"]
    note: str


class Dimensions(BaseModel):
    width_in: float | None
    height_in: float | None
    depth_in: float | None
    method: Literal["known_product_spec", "estimated_from_photo", "category_typical", "unknown"]
    note: str = Field(description="For apparel: laid-flat measurements, e.g. pit-to-pit; else overall size.")


class PhotoRequest(BaseModel):
    shot: Shot
    reason: str = Field(description="One short sentence shown to the seller, e.g. 'To confirm the size'.")


class Identification(BaseModel):
    category: Category
    subcategory: str = Field(description="E.g. 'insulated jacket', 'crossbody bag', 'running shoes'.")
    brand: Attr
    model_name: Attr = Field(description="Product line/model, e.g. 'Atom LT Hoody'. Null rather than a guess.")
    variant: Attr = Field(description="Colorway name, edition, year or generation if identifiable.")
    style_code: Attr = Field(description="SKU / style number / model number if printed and legible.")
    size: Attr
    size_system: Literal["alpha", "us", "uk", "eu", "waist_inseam", "numeric", "one_size", "not_applicable", "unknown"]
    gender: Gender
    gender_confidence: float
    colors: list[str] = Field(description="Main colors, most dominant first, plain names.")
    material: Attr
    condition: Condition
    condition_confidence: float
    flaws: list[Flaw]
    dimensions: Dimensions
    weight_lb: float | None = Field(description="Estimated shipping weight of the item alone.")
    text_seen: list[str] = Field(description="All legible text on the item and tags, verbatim.")
    alternatives: list[Candidate] = Field(description="Other plausible identities, if any.")
    authenticity_risk: Literal["low", "check", "high", "not_applicable"]
    authenticity_notes: str
    photo_requests: list[PhotoRequest] = Field(
        description="Only shots that would materially change identification, size, condition or authenticity."
    )
    search_query: str = Field(description="Best query to find sold comps for this exact item.")
    style_tags: list[str] = Field(description="Up to 6 buyer search terms: era, aesthetic, fit.")
