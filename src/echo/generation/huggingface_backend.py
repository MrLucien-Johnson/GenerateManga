"""Hugging Face Inference backend — credentials from env only."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from echo.core.errors import BackendUnavailable
from echo.core.paths import ensure_dir, generations_dir, project_root
from echo.generation.backend import GenerationBackend, GenerationResult


class HuggingFaceBackend(GenerationBackend):
    """Hugging Face Inference API backend.

    Reads ``HF_TOKEN`` from the environment only — never from config files.
    Gracefully reports unavailable when credentials or optional deps are missing.
    """

    name = "huggingface"

    def __init__(self, *, root: Path | None = None, model: str | None = None) -> None:
        self.root = root or project_root()
        self.model = model or self._default_model()

    def _default_model(self) -> str:
        from echo.core.config import get_config
        from echo.core.errors import ValidationError

        try:
            cfg = get_config("generation", root=self.root)
            return str(cfg.get("huggingface_model") or "black-forest-labs/FLUX.1-schnell")
        except ValidationError:
            return "black-forest-labs/FLUX.1-schnell"

    def _token(self) -> str | None:
        token = os.environ.get("HF_TOKEN", "").strip()
        return token or None

    def available(self) -> tuple[bool, str]:
        if not self._token():
            return (
                False,
                "HF_TOKEN is not set. Export HF_TOKEN in the environment "
                "(see .env.example). Tokens are never read from config files.",
            )
        try:
            import huggingface_hub  # noqa: F401
        except ImportError:
            return (
                False,
                "huggingface_hub is not installed. "
                "Install with: pip install 'echo-of-the-inkwell[hf]'",
            )
        return True, f"HF_TOKEN present; model={self.model}"

    def supports_reference_images(self) -> bool:
        return False

    def model_information(self) -> dict[str, Any]:
        return {
            "name": self.model,
            "backend": self.name,
            "token_source": "env:HF_TOKEN",
            "has_token": bool(self._token()),
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
        ok, reason = self.available()
        if not ok:
            raise BackendUnavailable(self.name, reason)

        try:
            from huggingface_hub import InferenceClient
        except ImportError as exc:
            raise BackendUnavailable(
                self.name,
                "huggingface_hub is not installed.",
                hint="pip install 'echo-of-the-inkwell[hf]'",
            ) from exc

        client = InferenceClient(token=self._token())
        try:
            image = client.text_to_image(
                prompt,
                model=self.model,
                negative_prompt=negative_prompt or None,
                width=width,
                height=height,
                seed=seed,
            )
        except Exception as exc:
            raise BackendUnavailable(
                self.name,
                f"Hugging Face inference failed: {exc}",
                hint="Check HF_TOKEN permissions and model access.",
            ) from exc

        if output_path is None:
            out_dir = ensure_dir(generations_dir(self.root) / "huggingface")
            output_path = out_dir / f"hf_{seed or 'noseed'}.png"
        else:
            output_path = Path(output_path)
            ensure_dir(output_path.parent)

        image.save(output_path, format="PNG")
        return GenerationResult(
            success=True,
            output_path=Path(output_path),
            seed=seed,
            backend=self.name,
            model=self.model,
            metadata={
                "settings": settings or {},
                "source_type": "REAL",
                "production_eligible": False,
            },
        )
