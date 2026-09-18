"""Image generation backends and metadata."""

from echo.generation.backend import GenerationBackend, GenerationResult
from echo.generation.registry import get_backend, list_backends

__all__ = [
    "GenerationBackend",
    "GenerationResult",
    "get_backend",
    "list_backends",
]
