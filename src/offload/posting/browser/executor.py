"""Carries out computer-use actions on a Playwright page.

The page's viewport *is* the screen: screenshots are taken at viewport size, so the model's
coordinates map 1:1 to page pixels. No display scaling to undo.
"""

from __future__ import annotations

import base64
import io
import random
import time
from dataclasses import dataclass
from typing import Any

from PIL import Image

# xdotool-style key names (what the model sends) -> Playwright key names.
_KEYS = {
    "return": "Enter", "enter": "Enter", "kp_enter": "Enter",
    "backspace": "Backspace", "tab": "Tab", "escape": "Escape", "esc": "Escape", "space": "Space",
    "delete": "Delete", "home": "Home", "end": "End",
    "page_up": "PageUp", "pageup": "PageUp", "prior": "PageUp",
    "page_down": "PageDown", "pagedown": "PageDown", "next": "PageDown",
    "up": "ArrowUp", "down": "ArrowDown", "left": "ArrowLeft", "right": "ArrowRight",
    "ctrl": "Control", "control": "Control", "alt": "Alt", "shift": "Shift",
    "super": "Meta", "cmd": "Meta", "meta": "Meta", "win": "Meta",
}


def to_playwright_key(combo: str) -> str:
    parts = [p.strip() for p in combo.replace(" ", "").split("+") if p.strip()]
    out = []
    for p in parts:
        low = p.lower()
        if low in _KEYS:
            out.append(_KEYS[low])
        elif low.startswith("f") and low[1:].isdigit():
            out.append(p.upper())
        elif len(p) == 1:
            out.append(p)
        else:
            out.append(p[:1].upper() + p[1:])
    return "+".join(out)


class ActionError(Exception):
    pass


@dataclass
class Executor:
    page: Any  # playwright.sync_api.Page
    pace: tuple[float, float] = (0.25, 0.9)  # human-like pause between actions, seconds
    type_delay_ms: int = 35
    _cursor: tuple[int, int] = (0, 0)

    def _pause(self) -> None:
        if self.pace[1] > 0:
            time.sleep(random.uniform(*self.pace))

    def screenshot_png(self) -> bytes:
        return self.page.screenshot(type="png")

    def _image_block(self, png: bytes) -> dict:
        return {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": base64.b64encode(png).decode()}}

    def run(self, name: str, args: dict) -> list[dict]:
        """Execute one action; return tool_result content blocks."""
        m = self.page.mouse
        kb = self.page.keyboard

        def xy(key: str = "coordinate") -> tuple[int, int]:
            c = args.get(key)
            if not (isinstance(c, (list, tuple)) and len(c) == 2):
                raise ActionError(f"{name} needs {key}=[x, y]")
            vp = self.page.viewport_size or {"width": 10**6, "height": 10**6}
            x, y = int(c[0]), int(c[1])
            if not (0 <= x < vp["width"] and 0 <= y < vp["height"]):
                raise ActionError(f"coordinate {x},{y} outside the {vp['width']}x{vp['height']} screen")
            return x, y

        if name == "screenshot":
            return [self._image_block(self.screenshot_png())]
        if name == "zoom":
            region = args.get("region")
            if not (isinstance(region, (list, tuple)) and len(region) == 4):
                raise ActionError("zoom needs region=[x0, y0, x1, y1]")
            img = Image.open(io.BytesIO(self.screenshot_png()))
            crop = img.crop(tuple(int(v) for v in region))
            scale = min(4.0, 1280 / max(1, crop.width))
            if scale > 1:
                crop = crop.resize((int(crop.width * scale), int(crop.height * scale)), Image.LANCZOS)
            buf = io.BytesIO()
            crop.save(buf, format="PNG")
            return [self._image_block(buf.getvalue())]
        if name == "cursor_position":
            return [{"type": "text", "text": f"{self._cursor[0]},{self._cursor[1]}"}]
        if name == "wait":
            time.sleep(min(float(args.get("duration", 1)), 10))
            return [{"type": "text", "text": "OK"}]

        self._pause()
        if name in ("left_click", "right_click", "middle_click", "double_click", "triple_click"):
            x, y = xy()
            button = {"right_click": "right", "middle_click": "middle"}.get(name, "left")
            count = {"double_click": 2, "triple_click": 3}.get(name, 1)
            modifier = args.get("text")  # e.g. "shift" held during the click
            if modifier:
                kb.down(to_playwright_key(modifier))
            m.click(x, y, button=button, click_count=count)
            if modifier:
                kb.up(to_playwright_key(modifier))
            self._cursor = (x, y)
        elif name == "mouse_move":
            self._cursor = xy()
            m.move(*self._cursor, steps=8)
        elif name == "left_click_drag":
            sx, sy = xy("start_coordinate")
            ex, ey = xy()
            m.move(sx, sy)
            m.down()
            m.move(ex, ey, steps=12)
            m.up()
            self._cursor = (ex, ey)
        elif name == "left_mouse_down":
            m.down()
        elif name == "left_mouse_up":
            m.up()
        elif name == "scroll":
            if "coordinate" in args:
                self._cursor = xy()
                m.move(*self._cursor)
            amount = int(args.get("scroll_amount", 3)) * 100
            direction = args.get("scroll_direction", "down")
            dx, dy = {"up": (0, -amount), "down": (0, amount), "left": (-amount, 0), "right": (amount, 0)}[direction]
            m.wheel(dx, dy)
        elif name == "type":
            kb.type(str(args.get("text", "")), delay=self.type_delay_ms)
        elif name == "key":
            key = to_playwright_key(str(args.get("text", "")))
            for _ in range(int(args.get("repeat", 1) or 1)):
                kb.press(key)
        elif name == "hold_key":
            key = to_playwright_key(str(args.get("text", "")))
            kb.down(key)
            time.sleep(min(float(args.get("duration", 1)), 10))
            kb.up(key)
        else:
            raise ActionError(f"unsupported action {name}")
        try:
            self.page.wait_for_timeout(150)  # let a click-triggered navigation start before we check the URL
            self.page.wait_for_load_state("domcontentloaded", timeout=5000)
        except Exception:
            pass
        return [{"type": "text", "text": "OK"}]
