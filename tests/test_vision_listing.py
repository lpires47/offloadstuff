from offload.images import Box, load_photo
from offload.listing import compose_listing, package_for
from offload.llm import ScriptedLLM
from offload.pricing import Comp, estimate_price
from offload.vision.pipeline import add_photos, analyze_photo, assess
from offload.vision.schema import Identification, PhotoRequest

from .conftest import attr, detected, detection, make_ident, png_bytes


def test_box_math():
    a, b = Box(0, 0, 500, 500), Box(250, 250, 750, 750)
    assert round(a.iou(b), 3) == round(62500 / 437500, 3)
    assert Box.clamp(900, 900, 1200, -5) == Box(900, 0, 1000, 900)


def test_crop_upscales_small_regions(photo):
    crop = photo.crop(Box(0, 0, 100, 100))
    assert max(crop.size) >= 512
    assert crop.sha256 == photo.sha256  # provenance follows the crop


def test_exif_and_resize():
    big = load_photo(png_bytes((5000, 3000)), max_edge=2048)
    assert max(big.size) == 2048


def test_single_item_skips_cropping(photo):
    llm = ScriptedLLM([detection("single_item", [detected("i1", 50, 50, 950, 950)]), make_ident()])
    out = analyze_photo(photo, llm)
    assert len(out.items) == 1 and out.items[0].ready_to_list
    assert len(llm.calls[1]["content"]) == 2  # one image + instructions, no overview


def test_pile_identifies_each_candidate_and_skips_setting(photo):
    det = detection("multiple_items", [
        detected("i1", 0, 0, 400, 400, "jacket"),
        detected("i2", 500, 0, 1000, 400, "jeans"),
        detected("i3", 0, 0, 1000, 1000, "bed", for_sale=False),
        detected("i4", 10, 5, 405, 400, "jacket again"),  # duplicate box of i1
    ])
    llm = ScriptedLLM([det, make_ident(), make_ident(subcategory="jeans", model_name=attr("501", 0.9))])
    out = analyze_photo(photo, llm)
    assert len(out.items) == 2
    assert [s.label for s in out.skipped] == ["bed"]
    assert len(llm.calls[1]["content"]) == 3  # crop + outlined overview + instructions


def test_missing_size_asks_for_size_tag_and_caps_requests():
    ident = make_ident(
        size=attr(None, 0.0), authenticity_risk="check",
        photo_requests=[PhotoRequest(shot="sole", reason="x"), PhotoRequest(shot="care_label", reason="y")],
    )
    missing, low, requests = assess(ident)
    assert "size" in missing
    assert [r.shot for r in requests] == ["size_tag", "brand_tag"]  # at most two asks


def test_low_confidence_flagged_not_missing_for_non_required():
    ident = make_ident(category="home_decor", brand=attr("IKEA", 0.5))
    missing, low, _ = assess(ident)
    assert "brand" in low and "brand" not in missing


def test_extra_photo_reidentifies_with_all_photos(photo):
    llm = ScriptedLLM([detection("single_item", [detected("i1", 0, 0, 1000, 1000)]), make_ident(size=attr(None, 0)), make_ident()])
    first = analyze_photo(photo, llm).items[0]
    assert not first.ready_to_list
    second = add_photos(first, [load_photo(png_bytes(color=(200, 200, 200)))], llm)
    assert second.ready_to_list and len(second.photos) == 2


def test_listing_is_honest_and_hides_floor(photo):
    llm = ScriptedLLM([detection("single_item", [detected("i1", 0, 0, 1000, 1000)]), make_ident()])
    item = analyze_photo(photo, llm).items[0]
    comps = [Comp("x", c, True, "ebay", "very_good") for c in (12100, 12800, 13400, 13800, 14500, 16500, 11800, 13200)]
    draft = compose_listing(item, estimate_price(comps, "very_good"))
    assert len(draft.title) <= 80 and draft.title.startswith("Arc'teryx Atom LT Hoody")
    assert "pilling at both cuffs" in draft.description
    assert "floor" not in str(draft.public_view()).lower()
    assert draft.floor_cents < draft.expected_cents <= draft.list_cents


def test_uncertain_model_not_stated_in_title(photo):
    llm = ScriptedLLM([detection("single_item", [detected("i1", 0, 0, 1000, 1000)]), make_ident(model_name=attr("Atom LT Hoody", 0.4))])
    item = analyze_photo(photo, llm).items[0]
    draft = compose_listing(item, estimate_price([], "very_good", retail_cents=26000))
    assert "Atom" not in draft.title and "Insulated Jacket" in draft.title


def test_pricing_quantiles_and_fallback():
    comps = [Comp("x", c * 100, True, "ebay", "very_good", 0.95) for c in range(100, 160, 5)]
    fast, slow = estimate_price(comps, "very_good", "fast"), estimate_price(comps, "very_good", "most")
    assert fast.list_cents < slow.list_cents and fast.floor_cents <= fast.expected_cents
    junk = [Comp("x", 99900, False, "ebay")] + [Comp("x", 500, True, "ebay", match_score=0.2)]
    est = estimate_price(junk, "good", retail_cents=20000)
    assert est.method == "retail_fallback" and est.comps_dropped == 2 and est.confidence == "low"


def test_condition_adjustment_lowers_price_for_worse_items():
    comps = [Comp("x", 13000, True, "ebay", "very_good")] * 8
    assert estimate_price(comps, "fair").expected_cents < estimate_price(comps, "very_good").expected_cents


def test_package_tiers():
    assert package_for("apparel", 0.9).tier in ("medium", "small")
    assert package_for("furniture").tier == "local_only"
    assert package_for("jewelry", 0.1).tier in ("small", "envelope")
