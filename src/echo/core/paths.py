"""Project root discovery and path helpers for Echo of the Inkwell."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

# Markers that identify the project root when walking upward.
_ROOT_MARKERS = (
    "pyproject.toml",
    "config/project.json",
    ".git",
)


def _looks_like_root(path: Path) -> bool:
    return any((path / marker).exists() for marker in _ROOT_MARKERS)


@lru_cache(maxsize=1)
def project_root() -> Path:
    """Locate the Echo project root.

    Resolution order:
    1. ``ECHO_PROJECT_ROOT`` environment variable
    2. Walk upward from this file / cwd looking for known markers
    3. Fall back to the current working directory
    """
    env = os.environ.get("ECHO_PROJECT_ROOT")
    if env:
        root = Path(env).expanduser().resolve()
        if root.is_dir():
            return root

    start = Path(__file__).resolve().parent
    for candidate in (start, *start.parents):
        if _looks_like_root(candidate):
            return candidate

    cwd = Path.cwd().resolve()
    for candidate in (cwd, *cwd.parents):
        if _looks_like_root(candidate):
            return candidate

    return cwd


def resolve_path(*parts: str | Path, root: Path | None = None) -> Path:
    """Join ``parts`` under the project root and return an absolute path."""
    base = root or project_root()
    return (base.joinpath(*[str(p) for p in parts])).resolve()


def ensure_dir(path: Path) -> Path:
    """Create ``path`` (and parents) if missing; return the path."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def config_dir(root: Path | None = None) -> Path:
    return resolve_path("config", root=root)


def logs_dir(root: Path | None = None) -> Path:
    return ensure_dir(resolve_path("logs", root=root))


def generations_dir(root: Path | None = None) -> Path:
    return ensure_dir(resolve_path("generations", root=root))


def approved_dir(root: Path | None = None) -> Path:
    return ensure_dir(resolve_path("approved", root=root))


def rejected_dir(root: Path | None = None) -> Path:
    return ensure_dir(resolve_path("rejected", root=root))


def prompts_dir(root: Path | None = None) -> Path:
    return ensure_dir(resolve_path("prompts", root=root))


def story_dir(root: Path | None = None) -> Path:
    return resolve_path("story", root=root)


def characters_dir(root: Path | None = None) -> Path:
    return resolve_path("characters", root=root)


def pages_dir(root: Path | None = None) -> Path:
    return ensure_dir(resolve_path("pages", root=root))


def reports_dir(root: Path | None = None) -> Path:
    return ensure_dir(resolve_path("reports", root=root))


def kdp_dir(root: Path | None = None) -> Path:
    return ensure_dir(resolve_path("kdp", root=root))


def state_path(root: Path | None = None) -> Path:
    return resolve_path("config", "state.json", root=root)


def clear_path_cache() -> None:
    """Clear cached project root (useful in tests)."""
    project_root.cache_clear()
