"""Load JSON configuration from ``config/*.json``."""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from echo.core.errors import ValidationError
from echo.core.paths import config_dir, project_root


def _load_json_file(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ValidationError(
            f"Config file not found: {path}",
            hint="Create the missing file under config/ or check ECHO_PROJECT_ROOT.",
        )
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValidationError(
            f"Invalid JSON in {path.name}: {exc.msg}",
            hint="Fix the JSON syntax and try again.",
        ) from exc
    if not isinstance(data, dict):
        raise ValidationError(
            f"Config {path.name} must be a JSON object.",
            hint="Wrap the contents in curly braces { }.",
        )
    return data


def load_config(name: str, *, root: Path | None = None) -> dict[str, Any]:
    """Load ``config/<name>.json`` (``.json`` suffix optional)."""
    stem = name if name.endswith(".json") else f"{name}.json"
    path = config_dir(root) / stem
    return _load_json_file(path)


def save_config(name: str, data: dict[str, Any], *, root: Path | None = None) -> Path:
    """Write ``data`` to ``config/<name>.json``."""
    stem = name if name.endswith(".json") else f"{name}.json"
    path = config_dir(root) / stem
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    _cached_config.cache_clear()
    return path


@lru_cache(maxsize=32)
def _cached_config(name: str, root_str: str) -> tuple[tuple[str, Any], ...]:
    """Internal cache returning a hashable snapshot."""
    data = load_config(name, root=Path(root_str) if root_str else None)
    return tuple(sorted(data.items(), key=lambda item: item[0]))


def get_config(name: str, *, root: Path | None = None, use_cache: bool = True) -> dict[str, Any]:
    """Load config with optional caching keyed by project root."""
    if not use_cache:
        return load_config(name, root=root)
    root_str = str((root or project_root()).resolve())
    return dict(_cached_config(name, root_str))


def mock_generation_enabled(root: Path | None = None) -> bool:
    """True when mock/test generation is explicitly enabled.

    Checks ``ECHO_MOCK_GENERATION=1`` first, then ``generation.json``
    ``use_mock_backend``.
    """
    env = os.environ.get("ECHO_MOCK_GENERATION", "").strip().lower()
    if env in {"1", "true", "yes", "on"}:
        return True
    if env in {"0", "false", "no", "off"}:
        return False
    try:
        gen = get_config("generation", root=root)
    except ValidationError:
        return False
    return bool(gen.get("use_mock_backend", False))


def clear_config_cache() -> None:
    _cached_config.cache_clear()
