"""Missing asset / reference handling."""

from __future__ import annotations

from pathlib import Path

import pytest

from echo.characters.manager import CharacterManager
from echo.core.errors import ValidationError
from echo.core.schemas import ReferenceStatus
from echo.prompts.builder import PromptBuilder
from echo.review.approval import ApprovalWorkflow
from echo.generation.metadata import create_record
from echo.core.schemas import ArtStatus


def test_missing_character_raises(tmp_project: Path) -> None:
    mgr = CharacterManager(root=tmp_project)
    with pytest.raises(ValidationError):
        mgr.character_dir("does-not-exist")


def test_kaito_references_missing_by_default(tmp_project: Path) -> None:
    mgr = CharacterManager(root=tmp_project)
    assert mgr.overall_reference_status("kaito") == ReferenceStatus.MISSING
    statuses = mgr.load_reference_statuses("kaito")
    assert any(s == ReferenceStatus.MISSING for s in statuses.values())


def test_approve_missing_output_raises(tmp_project: Path) -> None:
    from echo.core.schemas import SourceType

    record = create_record(
        page_id="p1",
        backend="test",
        source_type=SourceType.REAL,
        production_eligible=True,
        output_path=str(tmp_project / "generations" / "gone.png"),
        status=ArtStatus.GENERATED,
        root=tmp_project,
    )
    with pytest.raises(ValidationError):
        ApprovalWorkflow(root=tmp_project).approve(record.id)


def test_prompt_builder_tolerates_missing_optional_assets(tmp_project: Path) -> None:
    # Character without bible still builds a prompt (slug fallback).
    (tmp_project / "characters" / "ghost").mkdir(parents=True)
    from echo.story.page_plan import load_page_plan, save_page_plan

    plan = load_page_plan(root=tmp_project)
    plan.pages[0].characters = ["ghost"]
    save_page_plan(plan, root=tmp_project)
    payload = PromptBuilder(root=tmp_project).build("p1", save=False)
    assert "ghost" in payload["positive"].lower()
