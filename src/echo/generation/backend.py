"""Abstract generation backend interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class GenerationResult:
    success: bool
    output_path: Path | None = None
    seed: int | None = None
    backend: str = ""
    model: str | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class GenerationBackend(ABC):
    """Abstract image generation backend."""

    name: str = "base"

    @abstractmethod
    def available(self) -> tuple[bool, str]:
        """Return ``(ok, reason)``. Reason explains availability or failure."""

    def health_check(self) -> dict[str, Any]:
        ok, reason = self.available()
        return {
            "backend": self.name,
            "available": ok,
            "reason": reason,
            "supports_seed": self.supports_seed(),
            "supports_negative_prompt": self.supports_negative_prompt(),
            "supports_reference_images": self.supports_reference_images(),
            "model": self.model_information(),
        }

    @abstractmethod
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
        """Generate an image and return a :class:`GenerationResult`."""

    def regenerate(
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
        previous: GenerationResult | None = None,
    ) -> GenerationResult:
        """Default regenerate delegates to :meth:`generate` with a new seed hint."""
        regen_settings = dict(settings or {})
        if previous and previous.seed is not None and seed is None:
            regen_settings["previous_seed"] = previous.seed
        return self.generate(
            prompt=prompt,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            seed=seed,
            reference_images=reference_images,
            output_path=output_path,
            settings=regen_settings,
        )

    def supports_seed(self) -> bool:
        return True

    def supports_negative_prompt(self) -> bool:
        return True

    def supports_reference_images(self) -> bool:
        return False

    def model_information(self) -> dict[str, Any]:
        return {"name": None, "backend": self.name}
