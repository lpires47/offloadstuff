"""Data shapes for Find it: what the shopper is looking for, what sources return, and the ladder.

The ladder is the product: the exact item new, then the exact item used, then similar pieces that
keep the details that define the item. Everything here is plain data; decisions live in ladder.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

from offload.vision.schema import Category

Condition = Literal["new", "used", "unknown"]

# eBay API License Agreement (updated 2025-09-03): eBay content may not be co-mingled with non-eBay
# content in a public display (8.1(b)(2)), used to suggest or model prices (9.5), or used to train
# algorithms (9.10) without eBay's written consent. So eBay results live in their own module, never
# feed price badges, comps or typical prices, and are dropped from any training export.
SEPARATE_DISPLAY_SOURCES = {"ebay"}
NO_PRICING_SOURCES = {"ebay"}
NO_TRAINING_SOURCES = {"ebay"}
Rung = Literal["exact_new", "exact_used", "similar"]


# ---------- what we're looking for (filled by the model from photos or text) ----------


class DefiningDetail(BaseModel):
    detail: str = Field(description="A concrete, visible feature, e.g. 'cantilevered chrome tube frame'.")
    why: str = Field(description="Why it defines the item, in a few words.")
    must_match: bool = Field(
        description="True if a 'similar' item without this detail would feel wrong to a buyer "
        "(the Cesca's cane seat). False for details that may vary (color, wood tone)."
    )


class ItemProfile(BaseModel):
    """Search-oriented understanding of one item. Lighter and faster than a full Identification."""

    category: Category
    subcategory: str
    brand: str | None = Field(description="Null rather than a guess.")
    brand_confidence: float
    model_name: str | None = Field(description="Product line / model / design name. Null rather than a guess.")
    model_confidence: float
    designer: str | None = Field(description="For design objects: the designer, e.g. 'Marcel Breuer'.")
    variant: str | None = Field(description="Colorway, edition, finish, year or generation if identifiable.")
    style_code: str | None = Field(description="SKU / style / model number if legible. Never invented.")
    gtin: str | None = Field(description="UPC/EAN if legible on a tag or box.")
    era: str | None = Field(description="Approximate era for vintage or design pieces, e.g. '1970s'.")
    materials: list[str]
    colors: list[str]
    defining_details: list[DefiningDetail] = Field(
        description="3-6 features that make this item what it is, most important first."
    )
    exact_queries: list[str] = Field(
        description="1-3 search queries that should return this exact product (brand + model + variant/code). "
        "Empty if the exact product is unknown."
    )
    similar_queries: list[str] = Field(
        description="1-3 queries built from the defining details, without brand or model, to find "
        "pieces that share the look, e.g. 'cantilever chrome chair cane seat'."
    )
    reproduction_risk: Literal["low", "some", "high", "not_applicable"] = Field(
        description="How common licensed reissues, replicas or fakes are for this design."
    )
    notes: str = Field(description="One line on what to watch for when matching (look-alikes, reissues).")


# ---------- what sources return ----------


@dataclass
class Listing:
    source: str  # "ebay", "etsy", "poshmark.com", "shopify:storename.com", ...
    url: str
    title: str
    price_cents: int | None
    currency: str = "USD"
    condition: Condition = "unknown"
    image_urls: list[str] = field(default_factory=list)
    available: bool | None = None
    seller_type: Literal["retail", "resale", "unknown"] = "unknown"
    location: str | None = None
    shipping_cents: int | None = None
    gtin: str | None = None
    mpn: str | None = None
    brand: str | None = None
    found_via: str = ""  # which query / connector produced it
    fetched_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def key(self) -> str:
        return self.url.split("?")[0].rstrip("/").lower()


# ---------- the verifier's judgment of a candidate ----------


class CandidateVerdict(BaseModel):
    index: int = Field(description="Index of the candidate as numbered in the request.")
    match: Literal["exact", "same_model_other_variant", "similar", "unrelated", "cannot_tell"]
    matched_details: list[str] = Field(description="Which of the defining details this candidate clearly has.")
    missing_details: list[str] = Field(description="Which must-match details it lacks or contradicts.")
    looks: Literal["new", "used", "unknown"] = Field(description="Condition as shown in the listing photo/title.")
    confidence: float
    reason: str = Field(description="One short line a shopper would understand.")


class Verdicts(BaseModel):
    verdicts: list[CandidateVerdict]


# ---------- the answer ----------


@dataclass
class Result:
    listing: Listing
    rung: Rung
    score: float  # within-rung ordering, higher first
    confidence: float
    reason: str
    matched_details: list[str] = field(default_factory=list)
    price_badge: Literal["good_price", "typical", "high", None] = None


@dataclass
class Ladder:
    exact_new: list[Result] = field(default_factory=list)
    exact_used: list[Result] = field(default_factory=list)
    similar: list[Result] = field(default_factory=list)
    ebay: list[Result] = field(default_factory=list)  # shown as its own module; see SEPARATE_DISPLAY_SOURCES
    typical_used_cents: int | None = None  # median ask of non-eBay exact used listings, for the badge
    sources_searched: list[str] = field(default_factory=list)
    sources_failed: dict[str, str] = field(default_factory=dict)

    def all(self) -> list[Result]:
        return [*self.exact_new, *self.exact_used, *self.similar, *self.ebay]
