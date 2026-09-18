"""Shared fixtures for Echo of the Inkwell tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from echo.core.config import clear_config_cache
from echo.core.paths import clear_path_cache
from echo.story.page_plan import PageEntry, PagePlan, save_page_plan


@pytest.fixture()
def tmp_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Isolated project root with config, story plan, and character stubs."""
    clear_path_cache()
    clear_config_cache()
    monkeypatch.setenv("ECHO_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("ECHO_MOCK_GENERATION", "1")

    for name in (
        "config",
        "story",
        "characters/hero/references",
        "characters/kaito/references",
        "locations/room",
        "objects/inkwell/references",
        "generations",
        "approved",
        "rejected",
        "prompts",
        "pages",
        "logs",
        "reports",
        "kdp/final",
        "kdp/interior",
        "kdp/previews",
        "colab/outbound",
        "colab/inbound",
    ):
        (tmp_path / name).mkdir(parents=True, exist_ok=True)

    (tmp_path / "config" / "project.json").write_text(
        json.dumps({"name": "Echo Test", "slug": "echo-test", "version": "0.1.0"}),
        encoding="utf-8",
    )
    (tmp_path / "config" / "generation.json").write_text(
        json.dumps(
            {
                "default_backend": "mock",
                "use_mock_backend": True,
                "width": 256,
                "height": 256,
                "guidance_scale": 7.5,
                "num_inference_steps": 30,
                "local_model_path": None,
                "huggingface_model": "black-forest-labs/FLUX.1-schnell",
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "config" / "kdp.json").write_text(
        json.dumps(
            {
                "trim_width_in": 8.5,
                "trim_height_in": 11.0,
                "bleed_in": 0.125,
                "margin_in": 0.5,
                "dpi": 300,
                "blank_reverse_pages": True,
                "output_pdf": "kdp/final/interior.pdf",
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "config" / "git.json").write_text(
        json.dumps({"auto_commit_approved": False, "auto_push": False}),
        encoding="utf-8",
    )
    (tmp_path / "characters" / "hero" / "bible.json").write_text(
        json.dumps(
            {
                "name": "Hero",
                "appearance": "a brave kid with neat hair",
                "prompt": "brave kid, neat hair, coloring-book line art",
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "characters" / "kaito" / "character-bible.json").write_text(
        json.dumps(
            {
                "character_id": "kaito",
                "name": "Kaito",
                "appearance": "14-year-old boy, messy spiky hair, hooded jacket",
                "must_remain_constant": ["messy spiky hair", "hooded jacket"],
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "characters" / "kaito" / "continuity.json").write_text(
        json.dumps(
            {
                "character_id": "kaito",
                "reference_slots": {
                    "front": {"filename": "kaito_front.png", "status": "MISSING"}
                },
                "production_gate": {"KAITO_REFERENCE_APPROVED": False},
                "master_design": {
                    "selected_id": None,
                    "KAITO_MASTER_DESIGN_SELECTED": False,
                    "candidates_dir": "characters/kaito/design-candidates",
                },
                "notes": ["References not yet approved."],
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "characters" / "kaito" / "design-candidates").mkdir(parents=True, exist_ok=True)
    (tmp_path / "config" / "design.json").write_text(
        json.dumps(
            {
                "master_design_workflow": True,
                "auto_select": False,
                "refuse_mock_for_selection": True,
                "candidate_count": 4,
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "locations" / "room" / "location-bible.json").write_text(
        json.dumps({"description": "a tidy bedroom desk"}),
        encoding="utf-8",
    )
    (tmp_path / "objects" / "inkwell" / "object-bible.json").write_text(
        json.dumps({"description": "ornate magical inkwell"}),
        encoding="utf-8",
    )

    plan = PagePlan(
        title="Pilot",
        front_matter_pages=2,
        blank_reverse_pages=True,
        pages=[
            PageEntry(
                id="p1",
                story_page=1,
                title="Start",
                summary="Hero begins",
                layout="1",
                characters=["hero"],
                location="room",
            ),
            PageEntry(
                id="p2",
                story_page=2,
                title="Next",
                summary="Hero continues",
                layout="2",
                characters=["hero"],
                location="room",
            ),
        ],
    )
    save_page_plan(plan, root=tmp_path)
    clear_path_cache()
    clear_config_cache()
    yield tmp_path
    clear_path_cache()
    clear_config_cache()
