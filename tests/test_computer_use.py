"""The computer-use loop against a real (headless) browser and a local mock listing form."""

from pathlib import Path

import pytest

from offload.llm import ScriptedLLM
from offload.posting.browser.computer_use import NOT_EXECUTED, ComputerUseRunner, _host_allowed
from offload.posting.browser.executor import Executor, to_playwright_key
from offload.posting.browser.tasks import BrowserTask, create_listing

from .conftest import computer, png_bytes, response, tool

playwright = pytest.importorskip("playwright.sync_api")

FORM = """<!doctype html><html><body style="margin:0;font:16px sans-serif">
<input id="title" style="position:absolute;left:100px;top:100px;width:400px;height:30px">
<input id="price" style="position:absolute;left:100px;top:160px;width:120px;height:30px">
<label id="upload" style="position:absolute;left:100px;top:220px;width:200px;height:40px;background:#ddd">
  Add photos<input id="photos" type="file" multiple style="display:none"></label>
<button id="publish" style="position:absolute;left:100px;top:300px;width:120px;height:40px"
  onclick="document.body.dataset.published = document.getElementById('title').value + '|' + document.getElementById('price').value + '|' + document.getElementById('photos').files.length">Publish</button>
<a id="away" href="https://evil.example/" style="position:absolute;left:100px;top:380px">elsewhere</a>
</body></html>"""


@pytest.fixture
def page(tmp_path):
    with playwright.sync_playwright() as pw:
        browser = pw.chromium.launch()
        pg = browser.new_page(viewport={"width": 1280, "height": 800})
        (tmp_path / "form.html").write_text(FORM)
        pg.goto((tmp_path / "form.html").as_uri())
        yield pg
        browser.close()


def task(tmp_path, files=()):
    return BrowserTask("mock", "create_listing", "post it", {"title": "Hoody"}, '{"listing_url": str}',
                       None, ("file",), files=tuple(files))


def test_key_mapping():
    assert to_playwright_key("ctrl+a") == "Control+a"
    assert to_playwright_key("Return") == "Enter"
    assert to_playwright_key("shift+Tab") == "Shift+Tab"


def test_fills_and_publishes_a_listing(page, tmp_path):
    img = tmp_path / "p.png"
    img.write_bytes(png_bytes())
    llm = ScriptedLLM(create_responses=[
        response(computer("a", "left_click", coordinate=[300, 115]), computer("b", "type", text="Arc'teryx Atom LT Hoody")),
        response(computer("c", "left_click", coordinate=[150, 175]), computer("d", "type", text="149")),
        response(computer("e", "left_click", coordinate=[200, 240]), computer("f", "screenshot")),
        response(computer("g", "left_click", coordinate=[160, 320])),
        response(tool("h", "report_done", summary="published", result={"listing_url": "file://form"})),
    ])
    runner = ComputerUseRunner(llm, page, executor=Executor(page, pace=(0, 0), type_delay_ms=0))
    result = runner.run(task(tmp_path, files=[str(img)]))
    assert result.status == "done", result.summary
    assert page.evaluate("document.body.dataset.published") == "Arc'teryx Atom LT Hoody|149|1"
    # tool results echo toolset_name, and only the last few screenshots stay in context
    last_user = llm.calls[-1]["messages"][-1]
    assert all(b.get("toolset_name") == "computer" for b in last_user["content"])
    assert llm.calls[0]["tools"][0] == {"type": "computer_toolset_20260801"}


def test_batch_stops_at_first_failure(page, tmp_path):
    llm = ScriptedLLM(create_responses=[
        response(computer("a", "left_click", coordinate=[5000, 10]), computer("b", "type", text="nope")),
        response(tool("c", "report_blocked", reason="gave up", needs_user=False)),
    ])
    result = ComputerUseRunner(llm, page, executor=Executor(page, pace=(0, 0))).run(task(tmp_path))
    results = llm.calls[1]["messages"][-1]["content"]
    assert results[0]["is_error"] and "outside" in results[0]["content"]
    assert results[1]["content"] == NOT_EXECUTED
    assert result.status == "blocked"


def test_navigation_off_allowlist_is_reverted(page, tmp_path):
    page.route("https://evil.example/**", lambda route: route.fulfill(body="<h1>phish</h1>", content_type="text/html"))
    llm = ScriptedLLM(create_responses=[
        response(computer("a", "left_click", coordinate=[130, 388])),
        response(tool("b", "report_blocked", reason="x", needs_user=False)),
    ])
    ComputerUseRunner(llm, page, executor=Executor(page, pace=(0, 0))).run(task(tmp_path))
    err = llm.calls[1]["messages"][-1]["content"][0]
    assert err["is_error"] and "not allowed" in err["content"]
    assert page.url.startswith("file://")


def test_ask_user_decline_is_relayed(page, tmp_path):
    llm = ScriptedLLM(create_responses=[
        response(tool("a", "ask_user", action_summary="Pay $130")),
        response(tool("b", "report_blocked", reason="owner declined", needs_user=False)),
    ])
    asked = []
    result = ComputerUseRunner(llm, page, approve=lambda s: asked.append(s) or False,
                               executor=Executor(page, pace=(0, 0))).run(task(tmp_path))
    assert asked == ["Pay $130"] and "DECLINED" in llm.calls[1]["messages"][-1]["content"][0]["content"]
    assert result.status == "blocked"


def test_listing_task_never_carries_the_floor():
    with pytest.raises(ValueError):
        create_listing("depop", {"title": "x", "floor_cents": 100}, [])


def test_host_allowlist():
    assert _host_allowed("https://www.depop.com/x", ("depop.com",))
    assert not _host_allowed("https://depop.com.evil.io/x", ("depop.com",))
    assert not _host_allowed("https://notdepop.com/", ("depop.com",))
