from __future__ import annotations

import io
from types import SimpleNamespace

import pytest
from PIL import Image

from offload.vision.schema import Attr, Detection, DetectedItem, Dimensions, Flaw, Identification


def attr(value, conf=0.95, evidence="seen"):
    return Attr(value=value, confidence=conf, evidence=evidence if value else "")


def make_ident(**over) -> Identification:
    base = dict(
        category="apparel",
        subcategory="insulated jacket",
        brand=attr("Arc'teryx", 0.97, "chest logo"),
        model_name=attr("Atom LT Hoody", 0.9, "hood shape, logo placement"),
        variant=attr(None, 0.0),
        style_code=attr(None, 0.0),
        size=attr("M", 0.95, "size tag reads M"),
        size_system="alpha",
        gender="mens",
        gender_confidence=0.92,
        colors=["black"],
        material=attr("nylon shell, synthetic insulation", 0.8, "care label"),
        attributes=[],
        condition="very_good",
        condition_confidence=0.85,
        flaws=[Flaw(kind="pilling", location="both cuffs", severity="minor", note="light")],
        dimensions=Dimensions(width_in=22, height_in=27, depth_in=None, method="known_product_spec", note="laid flat"),
        weight_lb=0.9,
        text_seen=["ARC'TERYX", "M"],
        alternatives=[],
        authenticity_risk="low",
        authenticity_notes="",
        photo_requests=[],
        search_query="arcteryx atom lt hoody mens M black",
        style_tags=["gorpcore"],
    )
    base.update(over)
    return Identification(**base)


def detected(i, x0, y0, x1, y1, label="item", for_sale=True):
    return DetectedItem(id=i, label=label, x0=x0, y0=y0, x1=x1, y1=y1, is_for_sale_candidate=for_sale, visibility="clear", count=1)


def detection(scene, items, issues=()):
    return Detection(scene=scene, items=items, photo_issues=list(issues))


def png_bytes(size=(800, 600), color=(40, 40, 40)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


def response(*blocks, stop_reason="tool_use"):
    return SimpleNamespace(content=list(blocks), stop_reason=stop_reason)


def computer(tid, name, **inp):
    return {"type": "tool_use", "id": tid, "name": name, "toolset_name": "computer", "input": inp}


def tool(tid, name, **inp):
    return {"type": "tool_use", "id": tid, "name": name, "input": inp}


@pytest.fixture
def photo():
    from offload.images import load_photo

    return load_photo(png_bytes())
