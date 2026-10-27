from offload.images import load_photo
from offload.listing import compose_listing
from offload.pricing import estimate_price
from offload.vision.attributes import ProductAttribute, prompt_block, template_for
from offload.vision.pipeline import _finish

from .conftest import make_ident, png_bytes


def test_templates_match_whole_words():
    assert dict(template_for("high-rise jeans"))["rise"]
    assert "seat height" in dict(template_for("side chair"))
    assert "drawer count" in dict(template_for("walnut dresser"))
    assert template_for("laptop stand") == []  # not a "top"
    assert "pocket count" in prompt_block()


def test_confident_attributes_reach_the_listing_estimates_are_labeled():
    ident = make_ident(subcategory="jeans", attributes=[
        ProductAttribute(name="rise", value="high", confidence=0.9, evidence="tag", source="tag"),
        ProductAttribute(name="inseam", value="30 in", confidence=0.8, evidence="ruler", source="measured"),
        ProductAttribute(name="leg opening", value="15 in", confidence=0.8, evidence="guess", source="estimated"),
        ProductAttribute(name="pocket count", value="5", confidence=0.5, evidence="partly visible", source="visible"),
    ])
    photo = load_photo(png_bytes())
    draft = compose_listing(_finish(None, ident, [photo]), estimate_price([], "very_good", retail_cents=9800))
    assert draft.attributes["rise"] == "high" and draft.attributes["inseam"] == "30 in"
    assert "leg opening" not in draft.attributes  # estimates aren't stated as fact
    assert "Approx. leg opening: 15 in" in draft.description
    assert "pocket count" not in draft.attributes and "Pocket count" not in draft.description
