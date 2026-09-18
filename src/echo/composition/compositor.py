"""Compose illustrated pages from panel art, balloons, margins, and page numbers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from echo.composition.panels import get_layout
from echo.composition.text_overlay import Balloon, TextOverlay
from echo.core.config import get_config
from echo.core.errors import ValidationError
from echo.core.paths import ensure_dir, pages_dir, project_root


class PageCompositor:
    """Assemble a print-ready page image with Pillow."""

    def __init__(self, *, root: Path | None = None) -> None:
        self.root = root or project_root()
        self.kdp = self._load_kdp()

    def _load_kdp(self) -> dict[str, Any]:
        try:
            return get_config("kdp", root=self.root)
        except Exception:
            return {
                "trim_width_in": 8.5,
                "trim_height_in": 11.0,
                "dpi": 300,
                "bleed_in": 0.125,
                "margin_in": 0.5,
            }

    def page_pixel_size(self, *, include_bleed: bool = True) -> tuple[int, int]:
        dpi = int(self.kdp.get("dpi", 300))
        bleed = float(self.kdp.get("bleed_in", 0.125)) if include_bleed else 0.0
        w = (float(self.kdp.get("trim_width_in", 8.5)) + 2 * bleed) * dpi
        h = (float(self.kdp.get("trim_height_in", 11.0)) + 2 * bleed) * dpi
        return int(round(w)), int(round(h))

    def margin_px(self) -> int:
        dpi = int(self.kdp.get("dpi", 300))
        return int(round(float(self.kdp.get("margin_in", 0.5)) * dpi))

    def bleed_px(self) -> int:
        dpi = int(self.kdp.get("dpi", 300))
        return int(round(float(self.kdp.get("bleed_in", 0.125)) * dpi))

    def compose(
        self,
        *,
        panel_images: dict[str, str | Path] | list[str | Path],
        layout: str = "1",
        balloons: list[Balloon] | None = None,
        captions: list[Balloon] | None = None,
        page_number: int | None = None,
        output_path: str | Path | None = None,
        gutter: int = 12,
        background: str = "white",
    ) -> Path:
        """Compose panels into a full page and optionally overlay text."""
        width, height = self.page_pixel_size(include_bleed=True)
        page = Image.new("RGB", (width, height), background)
        draw = ImageDraw.Draw(page)

        margin = self.margin_px()
        bleed = self.bleed_px()
        content_left = bleed + margin
        content_top = bleed + margin
        content_right = width - bleed - margin
        content_bottom = height - bleed - margin
        content_w = content_right - content_left
        content_h = content_bottom - content_top

        layout_obj = get_layout(layout)
        boxes = layout_obj.scaled(content_w, content_h, gutter=gutter)

        if isinstance(panel_images, list):
            mapping = {
                (layout_obj.panels[i].id if i < len(layout_obj.panels) else f"p{i+1}"): path
                for i, path in enumerate(panel_images)
            }
        else:
            mapping = dict(panel_images)

        for panel_id, left, top, right, bottom in boxes:
            # Prefer exact id, then ordered fallbacks.
            src_path = mapping.get(panel_id)
            if src_path is None and mapping:
                src_path = next(iter(mapping.values()))
            if src_path is None:
                continue
            src = Path(src_path)
            if not src.is_file():
                candidate = self.root / src_path
                if candidate.is_file():
                    src = candidate
                else:
                    raise ValidationError(f"Panel image not found: {src_path}")
            img = Image.open(src).convert("RGB")
            target_w = max(1, right - left)
            target_h = max(1, bottom - top)
            img = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
            abs_left = content_left + left
            abs_top = content_top + top
            page.paste(img, (abs_left, abs_top))
            draw.rectangle(
                [abs_left, abs_top, abs_left + target_w - 1, abs_top + target_h - 1],
                outline="black",
                width=2,
            )

        overlay = TextOverlay()
        for balloon in balloons or []:
            overlay.draw_balloon(page, balloon)
        for caption in captions or []:
            cap = Balloon(
                text=caption.text,
                x=caption.x,
                y=caption.y,
                max_width=caption.max_width,
                kind="caption",
            )
            overlay.draw_balloon(page, cap)

        if page_number is not None:
            label = str(page_number)
            bbox = draw.textbbox((0, 0), label)
            tw = bbox[2] - bbox[0]
            draw.text(
                ((width - tw) // 2, height - bleed - margin // 2),
                label,
                fill="black",
            )

        if output_path is None:
            output_path = pages_dir(self.root) / f"page_{page_number or 'compose'}.png"
        else:
            output_path = Path(output_path)
        ensure_dir(output_path.parent)
        page.save(output_path, format="PNG")
        return Path(output_path)

    def blank_page(self, *, output_path: str | Path | None = None, page_number: int | None = None) -> Path:
        """Create a blank reverse page (white) at full trim+bleed size."""
        width, height = self.page_pixel_size(include_bleed=True)
        page = Image.new("RGB", (width, height), "white")
        if page_number is not None:
            draw = ImageDraw.Draw(page)
            # Optional subtle page number; keep nearly blank for coloring books.
            label = str(page_number)
            bbox = draw.textbbox((0, 0), label)
            tw = bbox[2] - bbox[0]
            bleed = self.bleed_px()
            margin = self.margin_px()
            draw.text(
                ((width - tw) // 2, height - bleed - margin // 2),
                label,
                fill="#CCCCCC",
            )
        if output_path is None:
            output_path = pages_dir(self.root) / f"blank_{page_number or 'reverse'}.png"
        else:
            output_path = Path(output_path)
        ensure_dir(output_path.parent)
        page.save(output_path, format="PNG")
        return Path(output_path)
