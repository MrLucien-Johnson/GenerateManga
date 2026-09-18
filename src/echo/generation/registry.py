"""Backend registry."""

from __future__ import annotations

from typing import TYPE_CHECKING

from echo.core.errors import ValidationError

if TYPE_CHECKING:
    from echo.generation.backend import GenerationBackend

_REGISTRY: dict[str, type[GenerationBackend]] | None = None


def _build_registry() -> dict[str, type[GenerationBackend]]:
    from echo.generation.colab_backend import ColabBackend
    from echo.generation.huggingface_backend import HuggingFaceBackend
    from echo.generation.local_backend import LocalDiffusionBackend
    from echo.generation.mock_backend import MockGenerationBackend

    return {
        MockGenerationBackend.name: MockGenerationBackend,
        LocalDiffusionBackend.name: LocalDiffusionBackend,
        ColabBackend.name: ColabBackend,
        HuggingFaceBackend.name: HuggingFaceBackend,
    }


def list_backends() -> list[str]:
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = _build_registry()
    return sorted(_REGISTRY.keys())


def get_backend(name: str, **kwargs) -> GenerationBackend:
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = _build_registry()
    key = name.strip().lower()
    if key not in _REGISTRY:
        raise ValidationError(
            f"Unknown generation backend '{name}'.",
            hint=f"Available: {', '.join(list_backends())}",
        )
    return _REGISTRY[key](**kwargs)
