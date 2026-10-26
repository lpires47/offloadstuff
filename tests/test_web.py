"""Web app smoke tests: the page loads, /api/find streams NDJSON, /api/sell returns a sign-off draft."""

from __future__ import annotations

import io
import json

from fastapi.testclient import TestClient
from PIL import Image

from offload.find.engine import Sources
from offload.find.models import CandidateVerdict, Verdicts
from offload.llm import ScriptedLLM
from offload.web import app as web
from tests.test_find import FakeSource, cesca, lst


def jpeg() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (64, 64), (120, 90, 60)).save(buf, "JPEG")
    return buf.getvalue()


def all_exact(req):
    text = req["content"][-1]["text"]
    n = text.count("\n#")
    return Verdicts(verdicts=[CandidateVerdict(index=i, match="exact", matched_details=[], missing_details=[],
                                               looks="used", confidence=0.9, reason="same") for i in range(n)])


def setup(monkeypatch, tmp_path, llm):
    monkeypatch.chdir(tmp_path)
    items = [lst("Knoll Cesca Chair cane", 40000 + i * 2000, f"https://a/{i}") for i in range(6)]
    web._state.clear()
    web._state["llm"] = llm
    web._state["sources"] = Sources(extra=[FakeSource("fake", items)])
    return TestClient(web.app)


def test_index_and_find_stream(monkeypatch, tmp_path):
    client = setup(monkeypatch, tmp_path, ScriptedLLM([cesca(), all_exact]))
    assert "Find it" in client.get("/").text
    r = client.post("/api/find", data={"text": "cesca chair"})
    events = [json.loads(line) for line in r.text.splitlines()]
    assert events[0]["type"] == "profile" and events[-1]["type"] == "done"
    final = [e for e in events if e["type"] == "ladder" and e["stage"] == "final"][0]
    assert len(final["ladder"]["exact_used"]) == 6
    run = events[0]["run"]
    assert client.post("/api/click", json={"run": run, "segment": "furniture", "source": "chairish.com",
                                           "url": "https://a/1", "rung": "exact_used"}).json() == {"ok": True}
    assert (tmp_path / "data" / "runs").exists()


def test_sell_returns_signoff_draft(monkeypatch, tmp_path):
    from tests.conftest import make_ident

    ident = make_ident()
    # Identification runs alongside the profile; ScriptedLLM answers by requested type.
    answers = {"Identification": ident, "ItemProfile": cesca()}

    class ByType(ScriptedLLM):
        def parse(self, *, model, system, content, output_model, max_tokens=4096):
            if output_model.__name__ in answers:
                return answers[output_model.__name__]
            return all_exact({"content": list(content)})

    client = setup(monkeypatch, tmp_path, ByType())
    r = client.post("/api/sell", files=[("photos", ("a.jpg", jpeg(), "image/jpeg"))])
    body = r.json()
    assert r.status_code == 200, body
    d = body["draft"]
    assert d and d["hidden_minimum_cents"] <= d["expected_cents"] <= d["price_cents"]
    assert d["comps"] and "current listings" in " ".join(d["price_notes"])
