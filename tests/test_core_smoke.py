"""Smoke tests for Echo of the Inkwell core package."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from echo import __version__
from echo.core.paths import project_root
from echo.core.schemas import ArtStatus, ReferenceStatus
from echo.generation.metadata import create_record
from echo.generation.mock_backend import MockGenerationBackend
from echo.prompts.builder import PromptBuilder
from echo.review.approval import ApprovalWorkflow
from echo.story.physical_pages import PhysicalPageKind, PhysicalPageMapper
from echo.story.page_plan import load_page_plan


def test_version() -> None:
    assert __version__ == "0.1.0"


def test_physical_page_mapping_with_front_matter(tmp_project: Path) -> None:
    mapper = PhysicalPageMapper(root=tmp_project)
    # Story page != physical page when front matter exists.
    mapping = mapper.story_to_physical(1)
    assert mapping["illustrated"] == 3  # after 2 front-matter pages
    assert mapping["blank_reverse"] == 4
    mapping2 = mapper.story_to_physical(2)
    assert mapping2["illustrated"] == 5
    assert mapping2["blank_reverse"] == 6

    phys = mapper.physical_to_story(3)
    assert phys.kind == PhysicalPageKind.ILLUSTRATED
    assert phys.story_page == 1
    blank = mapper.physical_to_story(4)
    assert blank.kind == PhysicalPageKind.BLANK_REVERSE
    assert mapper.total_physical_pages() == 6


def test_mock_backend_produces_valid_png(tmp_project: Path) -> None:
    backend = MockGenerationBackend(root=tmp_project)
    ok, _ = backend.available()
    assert ok
    out = tmp_project / "generations" / "test.png"
    result = backend.generate(prompt="test hero", width=128, height=128, seed=42, output_path=out)
    assert result.success
    assert result.output_path is not None
    assert result.output_path.is_file()
    assert result.seed == 42

    with Image.open(result.output_path) as img:
        assert img.size == (128, 128)
        assert img.format == "PNG"


def test_approval_copies_file(tmp_project: Path) -> None:
    backend = MockGenerationBackend(root=tmp_project)
    out = tmp_project / "generations" / "art.png"
    result = backend.generate(prompt="approve me", width=64, height=64, seed=7, output_path=out)
    record = create_record(
        page_id="p1",
        backend="mock",
        seed=result.seed,
        output_path=result.output_path,
        status=ArtStatus.GENERATED,
        root=tmp_project,
    )
    approved = ApprovalWorkflow(root=tmp_project).approve(record.id)
    assert approved.status == ArtStatus.APPROVED
    assert approved.approved_path is not None
    assert Path(approved.approved_path).is_file()
    # Silent overwrite blocked
    with pytest.raises(Exception):
        ApprovalWorkflow(root=tmp_project).approve(record.id)


def test_prompt_builder(tmp_project: Path) -> None:
    payload = PromptBuilder(root=tmp_project).build("p1", seed=1, save=True)
    assert "positive" in payload and "negative" in payload
    assert payload["dimensions"]["width"] == 256
    assert (tmp_project / "prompts" / "p1" / "latest.json").is_file()


def test_reference_status_enum() -> None:
    assert ReferenceStatus.MISSING.value == "MISSING"
    assert ReferenceStatus.LOCKED.value == "LOCKED"


def test_project_root_env(tmp_project: Path) -> None:
    assert project_root() == tmp_project.resolve()


def test_real_repo_page_plan_loads() -> None:
    """Production story pack must load after schema normalization."""
    # Use the real repository root (not tmp_project).
    from echo.core.paths import clear_path_cache
    import os

    clear_path_cache()
    # Unset fixture env if somehow present; pytest isolates fixtures per test.
    root = Path(__file__).resolve().parents[1]
    plan = load_page_plan(root=root)
    assert plan.title == "Echo of the Inkwell"
    assert len(plan.pages) == 50
    assert plan.pages[0].id == "p1"
    assert plan.pages[0].story_page == 1
