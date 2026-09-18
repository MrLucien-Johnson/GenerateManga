"""Programmatic dialogue and caption overlays (never baked into generation)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


@dataclass
class Balloon:
    text: str
    x: int
    y: int
    max_width: int = 280
    kind: str = "speech"  # speech | thought | caption


class TextOverlay:
    """Draw speech balloons and captions onto a composed page image."""

    def __init__(self, font_path: str | Path | None = None, font_size: int = 28) -> None:
        self.font_size = font_size
        self.font = self._load_font(font_path, font_size)

    def _load_font(self, font_path: str | Path | None, size: int) -> ImageFont.ImageFont:
        if font_path:
            path = Path(font_path)
            if path.is_file():
                return ImageFont.truetype(str(path), size=size)
        try:
            return ImageFont.load_default()
        except Exception:
            return ImageFont.load_default()

    def wrap_text(self, text: str, max_width: int, draw: ImageDraw.ImageDraw) -> list[str]:
        words = text.split()
        if not words:
            return [""]
        lines: list[str] = []
        current = words[0]
        for word in words[1:]:
            trial = f"{current} {word}"
            bbox = draw.textbbox((0, 0), trial, font=self.font)
            if bbox[2] - bbox[0] <= max_width:
                current = trial
            else:
                lines.append(current)
                current = word
        lines.append(current)
        return lines

    def draw_balloon(self, image: Image.Image, balloon: Balloon) -> Image.Image:
        draw = ImageDraw.Draw(image)
        lines = self.wrap_text(balloon.text, balloon.max_width, draw)
        line_heights = []
        max_line_w = 0
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=self.font)
            w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
            line_heights.append(h)
            max_line_w = max(max_line_w, w)
        pad = 12
        box_w = max_line_w + pad * 2
        box_h = sum(line_heights) + pad * 2 + 4 * (len(lines) - 1)
        x0, y0 = balloon.x, balloon.y
        x1, y1 = x0 + box_w, y0 + box_h

        if balloon.kind == "caption":
            draw.rectangle([x0, y0, x1, y1], fill="white", outline="black", width=2)
        elif balloon.kind == "thought":
            draw.ellipse([x0, y0, x1, y1], fill="white", outline="black", width=2)
        else:
            draw.rounded_rectangle([x0, y0, x1, y1], radius=16, fill="white", outline="black", width=2)
            # Tail
            draw.polygon(
                [(x0 + 24, y1), (x0 + 40, y1), (x0 + 20, y1 + 18)],
                fill="white",
                outline="black",
            )

        ty = y0 + pad
        for line, lh in zip(lines, line_heights):
            draw.text((x0 + pad, ty), line, fill="black", font=self.font)
            ty += lh + 4
        return image

    def apply(self, image: Image.Image, balloons: list[Balloon]) -> Image.Image:
        out = image.copy()
        for balloon in balloons:
            self.draw_balloon(out, balloon)
        return out
