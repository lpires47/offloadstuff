"""Per-user, per-platform browser sessions: the user's own logged-in state, cookies only.

The user signs in themselves (in production: through our streamed cloud browser; locally: a headed
window from `offload login`). We store the resulting storage state and reuse it for tasks. We never
see or store their password. Storage state files are secrets: encrypt at rest in production.
"""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

from ...config import settings
from .tasks import PLATFORMS

VIEWPORT = {"width": 1280, "height": 800}  # recommended size for web apps with computer use


def session_path(user_id: str, platform: str, root: Path | None = None) -> Path:
    root = root or settings().sessions_dir
    safe = "".join(ch for ch in user_id if ch.isalnum() or ch in "-_")
    return root / safe / f"{platform}.json"


@contextmanager
def browser_page(user_id: str, platform: str, *, headless: bool = True, root: Path | None = None):
    """Yield a Playwright page logged in as the user; save refreshed cookies afterwards."""
    from playwright.sync_api import sync_playwright

    path = session_path(user_id, platform, root)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=headless)
        context = browser.new_context(
            viewport=VIEWPORT,
            storage_state=str(path) if path.exists() else None,
            locale="en-US",
            timezone_id="America/Los_Angeles",
        )
        page = context.new_page()
        try:
            yield page
        finally:
            path.parent.mkdir(parents=True, exist_ok=True)
            context.storage_state(path=str(path))
            browser.close()


def interactive_login(user_id: str, platform: str, root: Path | None = None) -> Path:
    """Open a visible browser on the platform; the user signs in; we save the session."""
    with browser_page(user_id, platform, headless=False, root=root) as page:
        page.goto(PLATFORMS[platform]["home"])
        input(f"Sign in to {platform} in the browser window, then press Enter here... ")
    return session_path(user_id, platform, root)
