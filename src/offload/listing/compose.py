"""Identification + price -> a listing draft the seller approves (sign-off #1).

Title and description are built deterministically from identified facts, so every claim in the
listing traces back to a field with evidence. Low-confidence fields are flagged on the approval card,
never silently stated as fact.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..pricing import PriceEstimate
from ..vision.pipeline import AUTOFILL_MIN_CONFIDENCE, ItemAnalysis
from .shipping import Package, package_for

CONDITION_LABEL = {
    "new_with_tags": "New with tags",
    "new_without_tags": "New without tags",
    "like_new": "Like new",
    "very_good": "Very good",
    "good": "Good",
    "fair": "Fair",
    "poor": "Poor",
    "unknown": "Pre-owned",
}
GENDER_LABEL = {"mens": "Men's", "womens": "Women's", "unisex": "Unisex", "boys": "Boys'", "girls": "Girls'", "baby": "Baby"}
TITLE_MAX = 80  # eBay's limit; the strictest of the platforms we post to


@dataclass
class ListingDraft:
    title: str
    description: str
    category: str
    subcategory: str
    attributes: dict[str, str]
    condition: str
    package: Package
    list_cents: int
    floor_cents: int  # hidden minimum: never shown to buyers
    expected_cents: int
    flagged_fields: list[str] = field(default_factory=list)
    photo_hashes: list[str] = field(default_factory=list)
    search_query: str = ""

    def public_view(self) -> dict:
        """What a platform or buyer may see. The floor is deliberately absent."""
        return {
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "subcategory": self.subcategory,
            "attributes": dict(self.attributes),
            "condition": self.condition,
            "price_cents": self.list_cents,
        }


def _val(attr, min_conf: float = 0.0) -> str | None:
    return attr.value if attr.value and attr.confidence >= min_conf else None


def build_title(a: ItemAnalysis) -> str:
    i = a.identification
    parts = [
        _val(i.brand, AUTOFILL_MIN_CONFIDENCE["brand"]),
        _val(i.model_name, AUTOFILL_MIN_CONFIDENCE["model_name"]),
        GENDER_LABEL.get(i.gender) if i.gender_confidence >= 0.8 else None,
        f"Size {i.size.value}" if _val(i.size, 0.8) else None,
        i.colors[0].title() if i.colors else None,
        _val(i.variant, 0.7),
    ]
    if not parts[1]:
        parts.insert(2, i.subcategory.title())
    title = " ".join(p for p in parts if p)
    # Drop trailing parts until it fits, rather than cutting words.
    words = title.split()
    while len(" ".join(words)) > TITLE_MAX and len(words) > 1:
        words.pop()
    return " ".join(words)


def build_description(a: ItemAnalysis, pkg: Package) -> str:
    i = a.identification
    lines: list[str] = []
    name = " ".join(p for p in (_val(i.brand, AUTOFILL_MIN_CONFIDENCE["brand"]), _val(i.model_name, AUTOFILL_MIN_CONFIDENCE["model_name"])) if p) or i.subcategory
    lines.append(f"{name}, {CONDITION_LABEL[i.condition].lower()} condition.")
    if i.flaws:
        flaw_txt = "; ".join(f"{f.kind.replace('_', ' ')} at {f.location} ({f.severity})" for f in i.flaws)
        lines.append(f"Flaws, shown in photos: {flaw_txt}.")
    elif i.condition in ("new_with_tags", "new_without_tags", "like_new") and i.condition_confidence >= 0.8:
        lines.append("No visible flaws in the photos.")
    else:
        lines.append("See photos for condition.")
    details = []
    if _val(i.size, 0.8):
        details.append(f"Size: {i.size.value}")
    if i.colors:
        details.append("Color: " + ", ".join(c.lower() for c in i.colors[:3]))
    if _val(i.material, AUTOFILL_MIN_CONFIDENCE["material"]):
        details.append(f"Material: {i.material.value}")
    d = i.dimensions
    if d.width_in and d.height_in and d.method in ("known_product_spec", "estimated_from_photo"):
        label = "Measurements" if d.method == "known_product_spec" else "Approx. measurements"
        dims = f"{d.width_in:g} x {d.height_in:g}" + (f" x {d.depth_in:g}" if d.depth_in else "") + " in"
        details.append(f"{label}: {dims}" + (f" ({d.note})" if d.note else ""))
    if details:
        lines.append(" · ".join(details))
    return "\n".join(lines)


def compose_listing(a: ItemAnalysis, price: PriceEstimate) -> ListingDraft:
    i = a.identification
    dims = i.dimensions
    item_dims = (dims.width_in, dims.height_in, dims.depth_in) if dims.width_in and dims.height_in and dims.depth_in else None
    pkg = package_for(i.category, i.weight_lb, item_dims)
    # Only confident facts are stated to platforms and buyers; the rest are flagged for the seller.
    attributes = {
        k: v
        for k, v in {
            "brand": _val(i.brand, AUTOFILL_MIN_CONFIDENCE["brand"]),
            "model": _val(i.model_name, AUTOFILL_MIN_CONFIDENCE["model_name"]),
            "style_code": _val(i.style_code, 0.8),
            "size": _val(i.size, AUTOFILL_MIN_CONFIDENCE["size"]),
            "size_system": i.size_system if i.size_system not in ("unknown", "not_applicable") else None,
            "gender": GENDER_LABEL.get(i.gender) if i.gender_confidence >= AUTOFILL_MIN_CONFIDENCE["gender"] else None,
            "color": ", ".join(i.colors) if i.colors else None,
            "material": _val(i.material, AUTOFILL_MIN_CONFIDENCE["material"]),
        }.items()
        if v
    }
    if "size" not in attributes:
        attributes.pop("size_system", None)
    return ListingDraft(
        title=build_title(a),
        description=build_description(a, pkg),
        category=i.category,
        subcategory=i.subcategory,
        attributes=attributes,
        condition=i.condition,
        package=pkg,
        list_cents=price.list_cents,
        floor_cents=price.floor_cents,
        expected_cents=price.expected_cents,
        flagged_fields=sorted(set(a.low_confidence + a.missing)),
        photo_hashes=[p.sha256 for p in a.photos],
        search_query=i.search_query,
    )
