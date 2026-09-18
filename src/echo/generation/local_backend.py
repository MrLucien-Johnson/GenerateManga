"""Local Diffusers backend — never auto-downloads huge models."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from echo.core.config import mock_generation_enabled
from echo.core.errors import BackendUnavailable
from echo.core.paths import project_root
from echo.generation.backend import GenerationBackend, GenerationResult


class LocalDiffusionBackend(GenerationBackend):
    """Local Stable-Diffusion-style backend via ``diffusers``.

    Requirements for real generation
    --------------------------------
    - ``pip install echo-of-the-inkwell[local]`` (diffusers, torch)
    - A **pre-downloaded** model directory or Hugging Face cache already present
    - Config ``generation.json`` keys: ``local_model_path`` or ``local_model_id``
    - Explicit mock mode (``use_mock_backend`` / ``ECHO_MOCK_GENERATION=1``) if
      you only want placeholder PNGs without a model

    This backend will **not** download multi-GB weights automatically.
    """

    name = "local"

    def __init__(self, *, root: Path | None = None) -> None:
        self.root = root or project_root()
        self._unavailable_reason = self._probe()

    def _probe(self) -> str | None:
        try:
            import diffusers  # noqa: F401
        except ImportError:
            return (
                "diffusers is not installed. Install with: "
                "pip install 'echo-of-the-inkwell[local]'"
            )
        try:
            import torch  # noqa: F401
        except ImportError:
            return "torch is not installed. Install with: pip install 'echo-of-the-inkwell[local]'"

        model_path = self._configured_model_path()
        if model_path is None:
            return (
                "No local model configured. Set generation.json "
                "'local_model_path' to an existing directory (no auto-download)."
            )
        if not Path(model_path).exists():
            return f"Configured local model path does not exist: {model_path}"
        return None

    def _configured_model_path(self) -> str | None:
        from echo.core.config import get_config
        from echo.core.errors import ValidationError

        try:
            cfg = get_config("generation", root=self.root)
        except ValidationError:
            cfg = {}
        path = cfg.get("local_model_path") or os.environ.get("ECHO_LOCAL_MODEL_PATH")
        if path:
            return str(path)
        # local_model_id alone is not enough — we refuse to download.
        if cfg.get("local_model_id"):
            return None
        return None

    def available(self) -> tuple[bool, str]:
        if mock_generation_enabled(root=self.root):
            return True, "Mock/test mode enabled — local backend will use Pillow placeholders."
        if self._unavailable_reason:
            return False, self._unavailable_reason
        return True, f"Local model ready at {self._configured_model_path()}"

    def supports_reference_images(self) -> bool:
        return True

    def model_information(self) -> dict[str, Any]:
        return {
            "name": self._configured_model_path(),
            "backend": self.name,
            "auto_download": False,
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

        if mock_generation_enabled(root=self.root) or self._unavailable_reason:
            # Explicit mock path only — never silently fake production output.
            if not mock_generation_enabled(root=self.root):
                raise BackendUnavailable(self.name, self._unavailable_reason or reason)
            from echo.generation.mock_backend import MockGenerationBackend

            mock = MockGenerationBackend(root=self.root)
            result = mock.generate(
                prompt=prompt,
                negative_prompt=negative_prompt,
                width=width,
                height=height,
                seed=seed,
                reference_images=reference_images,
                output_path=output_path,
                settings={**(settings or {}), "via": "local_mock"},
            )
            result.backend = self.name
            result.metadata["mock"] = True
            result.metadata["label"] = "NON-PRODUCTION TEST"
            result.metadata["source_type"] = "MOCK"
            result.metadata["production_eligible"] = False
            return result

        # Real path: document-only stub that fails clearly until pipeline is wired
        # with a user-provided local model (no downloads).
        # When real generation is enabled, callers must set source_type=REAL.
        raise BackendUnavailable(
            self.name,
            (
                "Local Diffusers pipeline is configured but the production "
                "inference entrypoint is not enabled in this foundation build. "
                f"Model path: {self._configured_model_path()}. "
                "Use backend 'mock' or enable ECHO_MOCK_GENERATION=1 for tests."
            ),
            hint="Provide a local runner script or extend LocalDiffusionBackend.generate.",
        )
