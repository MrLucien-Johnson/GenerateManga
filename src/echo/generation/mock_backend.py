"""Mock generation backend for tests — produces valid PNGs with Pillow."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from echo.core.paths import ensure_dir, generations_dir, project_root
from echo.generation.backend import GenerationBackend, GenerationResult


class MockGenerationBackend(GenerationBackend):
    """Deterministic placeholder line-art PNG generator for tests."""

    name = "mock"

    def __init__(self, *, root: Path | None = None) -> None:
        self.root = root or project_root()
        self.seeds_used: list[int] = []

    def available(self) -> tuple[bool, str]:
        return True, "Mock backend always available (Pillow PNG placeholders)."

    def supports_reference_images(self) -> bool:
        return True

    def model_information(self) -> dict[str, Any]:
        return {"name": "mock-lineart", "backend": self.name, "production": False}

    def _resolve_seed(self, seed: int | None, prompt: str) -> int:
        if seed is not None:
            return int(seed)
        digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        return int(digest[:8], 16)

    def generate(
        self,
        *,
        prompt: str,
        negative_prompt: str = "",
        width: int = 1024,
        height: int = 1024,
        seed: int | None = None,
        reference_images: list[str | Path] | None = None,
        output_path: str | Path | None = None,
        settings: dict[str, Any] | None = None,
    ) -> GenerationResult:
        resolved_seed = self._resolve_seed(seed, prompt)
        self.seeds_used.append(resolved_seed)

        width = max(64, int(width))
        height = max(64, int(height))

        if output_path is None:
            out_dir = ensure_dir(generations_dir(self.root) / "mock")
            output_path = out_dir / f"mock_{resolved_seed}_{width}x{height}.png"
        else:
            output_path = Path(output_path)
            ensure_dir(output_path.parent)

        image = Image.new("RGB", (width, height), "white")
        draw = ImageDraw.Draw(image)

        # Simple deterministic line-art-like shapes from seed.
        margin = max(8, min(width, height) // 20)
        draw.rectangle([margin, margin, width - margin, height - margin], outline="black", width=3)
        cx, cy = width // 2, height // 2
        r = min(width, height) // 5
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline="black", width=3)
        draw.line([margin * 2, height - margin * 2, width - margin * 2, margin * 2], fill="black", width=2)
        draw.polygon(
            [
                (cx, margin * 3),
                (cx + r, cy + r // 2),
                (cx - r, cy + r // 2),
            ],
            outline="black",
        )

        settings = settings or {}
        label = "NON-PRODUCTION TEST"
        slot = str(settings.get("slot") or settings.get("kind") or "")
        character = str(settings.get("character") or "")
        try:
            font = ImageFont.load_default()
        except Exception:
            font = None
        draw.text((margin + 4, margin + 4), label, fill="black", font=font)
        draw.text((margin + 4, margin + 20), f"seed={resolved_seed}", fill="black", font=font)
        if character or slot:
            draw.text(
                (margin + 4, margin + 36),
                f"{character} / {slot}".strip(" /"),
                fill="black",
                font=font,
            )

        # Tiny mark from negative prompt length so tests can assert influence without baking text.
        if negative_prompt:
            draw.rectangle(
                [width - margin - 20, height - margin - 20, width - margin, height - margin],
                outline="black",
                width=2,
            )

        if reference_images:
            draw.line(
                [margin, height // 2, width - margin, height // 2],
                fill="black",
                width=1,
            )

        image.save(output_path, format="PNG")

        return GenerationResult(
            success=True,
            output_path=Path(output_path),
            seed=resolved_seed,
            backend=self.name,
            model="mock-lineart",
            metadata={
                "prompt_chars": len(prompt),
                "negative_chars": len(negative_prompt),
                "references": [str(r) for r in (reference_images or [])],
                "settings": settings or {},
                "source_type": "MOCK",
                "production_eligible": False,
            },
        )
