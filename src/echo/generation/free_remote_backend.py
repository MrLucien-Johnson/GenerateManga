"""Free remote image backend (Pollinations) — zero-cost, no API key.

Used when local GPU and HF credentials are unavailable. Outputs genuine
AI-generated images (not mock placeholders). License/commercial suitability
must be reviewed by the owner before publication.
"""

from __future__ import annotations

import io
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from echo.core.errors import BackendUnavailable
from echo.core.paths import ensure_dir, generations_dir, project_root
from echo.core.schemas import SourceType
from echo.generation.backend import GenerationBackend, GenerationResult


class FreeRemoteBackend(GenerationBackend):
    """Pollinations text-to-image (no paid API key required)."""

    name = "free_remote"
    MODEL_ID = "pollinations-flux"
    MODEL_SOURCE = "https://pollinations.ai/"
    LICENSE_NOTES = (
        "Third-party free image service (Pollinations). "
        "Owner must review terms of use and commercial rights before KDP publication. "
        "Not claimed commercially safe by this studio."
    )

    def __init__(self, *, root: Path | None = None, model: str | None = None) -> None:
        self.root = root or project_root()
        self.model = model or self.MODEL_ID

    def available(self) -> tuple[bool, str]:
        return True, (
            "Free remote Pollinations API (no HF_TOKEN). "
            "Requires outbound network. Review license before production."
        )

    def supports_seed(self) -> bool:
        return True

    def supports_negative_prompt(self) -> bool:
        return False  # folded into positive prompt when needed

    def supports_reference_images(self) -> bool:
        return False

    def model_information(self) -> dict[str, Any]:
        return {
            "name": self.model,
            "backend": self.name,
            "source": self.MODEL_SOURCE,
            "license_notes": self.LICENSE_NOTES,
            "production": True,
            "source_type": SourceType.REAL.value,
        }

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
        width = max(256, min(1280, int(width)))
        height = max(256, min(1280, int(height)))
        resolved_seed = int(seed) if seed is not None else 42

        # Emphasize B&W line art; append negatives as soft constraints.
        full_prompt = prompt.strip()
        if negative_prompt:
            full_prompt = (
                f"{full_prompt}. Avoid: {negative_prompt[:400]}"
            )
        encoded = urllib.parse.quote(full_prompt[:1800], safe="")
        url = (
            f"https://image.pollinations.ai/prompt/{encoded}"
            f"?width={width}&height={height}&seed={resolved_seed}"
            f"&nologo=true&model=flux&enhance=false"
        )

        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "EchoOfTheInkwell/0.1 (local manga studio)"},
            )
            with urllib.request.urlopen(req, timeout=180) as resp:
                data = resp.read()
                content_type = resp.headers.get("Content-Type", "")
        except Exception as exc:
            raise BackendUnavailable(
                self.name,
                f"Free remote generation failed: {exc}",
                hint="Check network egress or retry; Colab/local remain preferred for production.",
            ) from exc

        if not data or len(data) < 1000:
            raise BackendUnavailable(
                self.name,
                "Free remote returned empty/too-small payload.",
                hint="Retry or use Colab notebook.",
            )
        if b"{" in data[:20] and b"error" in data[:200].lower():
            raise BackendUnavailable(
                self.name,
                f"Free remote error payload: {data[:200]!r}",
            )

        try:
            from PIL import Image
        except ImportError as exc:
            raise BackendUnavailable(self.name, "Pillow required.") from exc

        try:
            image = Image.open(io.BytesIO(data))
            image.load()
            if image.mode not in ("RGB", "L"):
                image = image.convert("RGB")
            else:
                image = image.convert("RGB")
        except Exception as exc:
            raise BackendUnavailable(
                self.name,
                f"Returned data is not a readable image ({content_type}): {exc}",
            ) from exc

        if output_path is None:
            out_dir = ensure_dir(generations_dir(self.root) / "free_remote")
            output_path = out_dir / f"fr_{resolved_seed}_{width}x{height}.png"
        else:
            output_path = Path(output_path)
            ensure_dir(output_path.parent)

        image.save(output_path, format="PNG")
        return GenerationResult(
            success=True,
            output_path=Path(output_path),
            seed=resolved_seed,
            backend=self.name,
            model=self.model,
            metadata={
                "settings": settings or {},
                "source_type": SourceType.REAL.value,
                "production_eligible": True,
                "model_revision": None,
                "license_notes": self.LICENSE_NOTES,
                "model_source": self.MODEL_SOURCE,
                "content_type": content_type,
            },
        )
