"""Runtime configuration, read from the environment."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def load_dotenv(path: str | Path = ".env") -> None:
    """Read KEY=value lines from .env into the environment (without overriding what's already set)."""
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.split(" #", 1)[0].strip().strip('"').strip("'")
        if key.strip() and value:
            os.environ.setdefault(key.strip(), value)


load_dotenv()


def _env(name: str, default: str) -> str:
    value = os.environ.get(name, "").strip()
    return value or default


@dataclass(frozen=True)
class Settings:
    # Identification needs the best vision we can get; detection (finding items in a pile) is cheaper.
    vision_model: str = field(default_factory=lambda: _env("OFFLOAD_VISION_MODEL", "claude-opus-5-5"))
    detect_model: str = field(default_factory=lambda: _env("OFFLOAD_DETECT_MODEL", "claude-sonnet-5-5"))
    text_model: str = field(default_factory=lambda: _env("OFFLOAD_TEXT_MODEL", "claude-sonnet-5-5"))
    # Fast first look: just enough to start searching while the full read continues.
    fast_model: str = field(default_factory=lambda: _env("OFFLOAD_FAST_MODEL", "claude-haiku-5-5"))
    computer_model: str = field(default_factory=lambda: _env("OFFLOAD_COMPUTER_MODEL", "claude-opus-5-5"))
    sessions_dir: Path = field(default_factory=lambda: Path(_env("OFFLOAD_SESSIONS_DIR", "./sessions")))
    # Long edge we send to the model. Models from Opus 4.7 on accept up to 2,576 px.
    max_image_edge: int = 2048

    @property
    def has_api_key(self) -> bool:
        return bool(os.environ.get("ANTHROPIC_API_KEY"))


def settings() -> Settings:
    return Settings()
