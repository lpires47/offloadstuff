"""Image loading, normalizing, and cropping.

Coordinates in this codebase are *normalized* to a 0-1000 grid on both axes, independent of the
photo's pixel size. The model is asked to answer in that grid, which keeps boxes valid when we resize.
"""

from __future__ import annotations

import base64
import hashlib
import io
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageOps

GRID = 1000


@dataclass(frozen=True)
class Box:
    """Axis-aligned box on the 0-1000 grid: (x0, y0) top-left, (x1, y1) bottom-right."""

    x0: int
    y0: int
    x1: int
    y1: int

    def __post_init__(self) -> None:
        if not (0 <= self.x0 < self.x1 <= GRID and 0 <= self.y0 < self.y1 <= GRID):
            raise ValueError(f"invalid box {self}")

    @classmethod
    def clamp(cls, x0: float, y0: float, x1: float, y1: float) -> "Box":
        x0, x1 = sorted((x0, x1))
        y0, y1 = sorted((y0, y1))
        x0, y0 = min(max(0, int(x0)), GRID - 1), min(max(0, int(y0)), GRID - 1)
        x1, y1 = min(GRID, max(int(round(x1)), x0 + 1)), min(GRID, max(int(round(y1)), y0 + 1))
        return cls(x0, y0, x1, y1)

    @property
    def area(self) -> int:
        return (self.x1 - self.x0) * (self.y1 - self.y0)

    def iou(self, other: "Box") -> float:
        ix0, iy0 = max(self.x0, other.x0), max(self.y0, other.y0)
        ix1, iy1 = min(self.x1, other.x1), min(self.y1, other.y1)
        inter = max(0, ix1 - ix0) * max(0, iy1 - iy0)
        union = self.area + other.area - inter
        return inter / union if union else 0.0

    def padded(self, frac: float) -> "Box":
        dx = (self.x1 - self.x0) * frac
        dy = (self.y1 - self.y0) * frac
        return Box.clamp(self.x0 - dx, self.y0 - dy, self.x1 + dx, self.y1 + dy)


@dataclass(frozen=True)
class Photo:
    """A normalized photo: upright (EXIF applied), RGB, long edge capped."""

    image: Image.Image
    sha256: str  # hash of the ORIGINAL bytes: provenance against later photo disputes
    source: str

    @property
    def size(self) -> tuple[int, int]:
        return self.image.size

    def jpeg_bytes(self, quality: int = 90) -> bytes:
        buf = io.BytesIO()
        self.image.save(buf, format="JPEG", quality=quality)
        return buf.getvalue()

    def content_block(self) -> dict:
        """An Anthropic Messages API image block."""
        return {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/jpeg",
                "data": base64.b64encode(self.jpeg_bytes()).decode("ascii"),
            },
        }

    def crop(self, box: Box, pad: float = 0.08, min_edge: int = 512) -> "Photo":
        """Crop to a box (with padding). Small crops are upscaled so fine print stays legible."""
        w, h = self.size
        b = box.padded(pad)
        region = self.image.crop((b.x0 * w // GRID, b.y0 * h // GRID, b.x1 * w // GRID, b.y1 * h // GRID))
        long_edge = max(region.size)
        if long_edge < min_edge:
            scale = min_edge / long_edge
            region = region.resize((round(region.width * scale), round(region.height * scale)), Image.LANCZOS)
        return Photo(region, self.sha256, f"{self.source}#crop={b.x0},{b.y0},{b.x1},{b.y1}")


def load_photo(src: str | Path | bytes, max_edge: int = 2048) -> Photo:
    if isinstance(src, (str, Path)):
        raw = Path(src).read_bytes()
        name = str(src)
    else:
        raw = src
        name = "<bytes>"
    image = Image.open(io.BytesIO(raw))
    image = ImageOps.exif_transpose(image).convert("RGB")
    if max(image.size) > max_edge:
        image.thumbnail((max_edge, max_edge), Image.LANCZOS)
    return Photo(image, hashlib.sha256(raw).hexdigest(), name)
