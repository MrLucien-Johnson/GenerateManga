"""Prompt assembly from style, character, and page layers."""

from __future__ import annotations

from pathlib import Path

from echo.prompts.builder import PromptBuilder
from echo.prompts.history import load_latest_prompt
from echo.prompts.style import COLORING_BOOK_RULES, MASTER_VISUAL_STYLE, NEGATIVE_CONSTRAINTS


def test_prompt_contains_style_and_character(tmp_project: Path) -> None:
    payload = PromptBuilder(root=tmp_project).build("p1", seed=42, save=True)
    assert "positive" in payload and "negative" in payload
    assert MASTER_VISUAL_STYLE.strip().splitlines()[0] in payload["positive"]
    assert "COLORING BOOK RULES" in payload["positive"] or COLORING_BOOK_RULES[:20] in payload["positive"]
    assert "Hero" in payload["positive"] or "hero" in payload["positive"].lower()
    assert NEGATIVE_CONSTRAINTS.split(",")[0].strip() in payload["negative"]
    assert payload["dimensions"]["width"] == 256
    assert payload["dimensions"]["height"] == 256
    assert payload["seed"] == 42
    assert payload["backend"] == "mock"
    assert (tmp_project / "prompts" / "p1" / "latest.json").is_file()
    latest = load_latest_prompt("p1", root=tmp_project)
    assert latest is not None
    assert latest["page_id"] == "p1"


def test_prompt_includes_location_bible(tmp_project: Path) -> None:
    payload = PromptBuilder(root=tmp_project).build("p1", save=False)
    assert "LOCATION: room" in payload["positive"]
    assert "tidy bedroom" in payload["positive"]


def test_extra_positive_appended(tmp_project: Path) -> None:
    payload = PromptBuilder(root=tmp_project).build(
        "p1",
        save=False,
        extra_positive="EXTRA DETAIL MARKER",
        extra_negative="fog",
    )
    assert "EXTRA DETAIL MARKER" in payload["positive"]
    assert "fog" in payload["negative"]
