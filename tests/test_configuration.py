"""Configuration loading and mock-generation flags."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from echo.core.config import (
    clear_config_cache,
    get_config,
    load_config,
    mock_generation_enabled,
    save_config,
)
from echo.core.errors import ValidationError


def test_load_generation_and_kdp(tmp_project: Path) -> None:
    gen = load_config("generation", root=tmp_project)
    assert gen["default_backend"] == "mock"
    assert gen["use_mock_backend"] is True
    kdp = get_config("kdp", root=tmp_project)
    assert kdp["trim_width_in"] == 8.5
    assert kdp["trim_height_in"] == 11.0


def test_mock_generation_env_override(tmp_project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ECHO_MOCK_GENERATION", "0")
    # Config still has use_mock_backend true, but env off wins.
    assert mock_generation_enabled(root=tmp_project) is False
    monkeypatch.setenv("ECHO_MOCK_GENERATION", "1")
    assert mock_generation_enabled(root=tmp_project) is True


def test_save_config_roundtrip(tmp_project: Path) -> None:
    save_config("project", {"name": "Updated", "slug": "u"}, root=tmp_project)
    clear_config_cache()
    data = load_config("project", root=tmp_project)
    assert data["name"] == "Updated"


def test_missing_config_raises(tmp_project: Path) -> None:
    with pytest.raises(ValidationError):
        load_config("does-not-exist", root=tmp_project)


def test_invalid_json_raises(tmp_project: Path) -> None:
    path = tmp_project / "config" / "broken.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(ValidationError):
        load_config("broken", root=tmp_project)
