"""Colab workflow backend — prepares manifests / imports results."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from echo.core.errors import ValidationError
from echo.core.paths import ensure_dir, project_root, resolve_path
from echo.generation.backend import GenerationBackend, GenerationResult


class ColabBackend(GenerationBackend):
    """Optional Google Colab workflow helper.

    ``available()`` is True whenever the local Colab exchange directory exists
    or can be created — Colab does **not** need to be online for the backend
    to explain the optional workflow.
    """

    name = "colab"

    def __init__(self, *, root: Path | None = None) -> None:
        self.root = root or project_root()
        self.exchange_dir = ensure_dir(resolve_path("colab", root=self.root))

    def available(self) -> tuple[bool, str]:
        return (
            True,
            (
                "Colab backend is an optional offline/online workflow. "
                f"Write jobs to {self.exchange_dir / 'outbound'} and import "
                f"results from {self.exchange_dir / 'inbound'}. "
                "Colab does not need to be connected for availability checks."
            ),
        )

    def supports_seed(self) -> bool:
        return True

    def supports_reference_images(self) -> bool:
        return True

    def model_information(self) -> dict[str, Any]:
        return {
            "name": "colab-remote",
            "backend": self.name,
            "exchange_dir": str(self.exchange_dir),
            "requires_online_colab_for_generate": True,
        }

    def prepare_manifest(
        self,
        *,
        prompt: str,
        negative_prompt: str = "",
        width: int = 1024,
        height: int = 1024,
        seed: int | None = None,
        reference_images: list[str | Path] | None = None,
        settings: dict[str, Any] | None = None,
        page_id: str | None = None,
    ) -> Path:
        """Write a job manifest for a Colab notebook to consume."""
        outbound = ensure_dir(self.exchange_dir / "outbound")
        job_id = uuid4().hex[:12]
        manifest = {
            "job_id": job_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "page_id": page_id,
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "width": width,
            "height": height,
            "seed": seed,
            "reference_images": [str(p) for p in (reference_images or [])],
            "settings": settings or {},
        }
        path = outbound / f"job_{job_id}.json"
        path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        return path

    def import_result(self, job_id: str, *, dest: Path | None = None) -> GenerationResult:
        """Import a completed job from ``colab/inbound/``."""
        inbound = self.exchange_dir / "inbound"
        meta_path = inbound / f"job_{job_id}.json"
        image_candidates = list(inbound.glob(f"job_{job_id}.*"))
        image_path = next(
            (p for p in image_candidates if p.suffix.lower() in {".png", ".jpg", ".jpeg"}),
            None,
        )
        if image_path is None:
            raise ValidationError(
                f"No inbound Colab image for job '{job_id}'.",
                hint=f"Place the PNG at {inbound / f'job_{job_id}.png'}",
            )
        if dest is None:
            dest = (
                ensure_dir(resolve_path("generations", "colab", root=self.root))
                / f"{job_id}.png"
            )
        else:
            dest = Path(dest)
            ensure_dir(dest.parent)
        dest.write_bytes(image_path.read_bytes())
        meta: dict[str, Any] = {}
        if meta_path.is_file():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        return GenerationResult(
            success=True,
            output_path=dest,
            seed=meta.get("seed"),
            backend=self.name,
            model=meta.get("model"),
            metadata=meta,
        )

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
        """Prepare a Colab manifest; does not wait for remote execution."""
        settings = dict(settings or {})
        page_id = settings.pop("page_id", None)
        existing_job = settings.pop("job_id", None)
        manifest = self.prepare_manifest(
            prompt=prompt,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            seed=seed,
            reference_images=reference_images,
            settings=settings,
            page_id=page_id,
        )
        job_id = existing_job or json.loads(manifest.read_text(encoding="utf-8"))["job_id"]
        inbound_img = self.exchange_dir / "inbound" / f"job_{job_id}.png"
        if inbound_img.is_file():
            return self.import_result(job_id, dest=Path(output_path) if output_path else None)

        return GenerationResult(
            success=False,
            output_path=None,
            seed=seed,
            backend=self.name,
            error=(
                f"Colab job manifest written to {manifest}. "
                "Run the Colab notebook, place results in colab/inbound/, "
                "then call import_result(job_id)."
            ),
            metadata={"manifest": str(manifest), "job_id": job_id},
        )
