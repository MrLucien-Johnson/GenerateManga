"""Story page vs physical page mapping."""

from __future__ import annotations

from pathlib import Path

import pytest

from echo.core.errors import ValidationError
from echo.story.page_plan import PageEntry, PagePlan, save_page_plan
from echo.story.physical_pages import PhysicalPageKind, PhysicalPageMapper


def test_story_not_equal_physical_with_front_matter(tmp_project: Path) -> None:
    mapper = PhysicalPageMapper(root=tmp_project)
    mapping = mapper.story_to_physical(1)
    assert mapping["illustrated"] == 3
    assert mapping["blank_reverse"] == 4
    assert mapping["illustrated"] != 1


def test_blank_reverse_pairs(tmp_project: Path) -> None:
    mapper = PhysicalPageMapper(root=tmp_project)
    pages = mapper.all_pages()
    kinds = [p.kind for p in pages]
    assert kinds.count(PhysicalPageKind.FRONT_MATTER) == 2
    assert kinds.count(PhysicalPageKind.ILLUSTRATED) == 2
    assert kinds.count(PhysicalPageKind.BLANK_REVERSE) == 2
    assert mapper.total_physical_pages() == 6


def test_physical_to_story_roundtrip(tmp_project: Path) -> None:
    mapper = PhysicalPageMapper(root=tmp_project)
    art = mapper.physical_to_story(3)
    assert art.kind == PhysicalPageKind.ILLUSTRATED
    assert art.story_page == 1
    blank = mapper.physical_to_story(4)
    assert blank.kind == PhysicalPageKind.BLANK_REVERSE
    assert blank.story_page == 1


def test_no_blank_reverse_double_sided(tmp_project: Path) -> None:
    plan = PagePlan(
        title="Double",
        front_matter_pages=0,
        blank_reverse_pages=False,
        pages=[
            PageEntry(id="p1", story_page=1, title="A"),
            PageEntry(id="p2", story_page=2, title="B"),
        ],
    )
    save_page_plan(plan, root=tmp_project)
    mapper = PhysicalPageMapper(root=tmp_project)
    assert mapper.story_to_physical(1) == {"illustrated": 1, "blank_reverse": None}
    assert mapper.story_to_physical(2) == {"illustrated": 2, "blank_reverse": None}
    assert mapper.total_physical_pages() == 2


def test_zero_front_matter_with_blanks(tmp_project: Path) -> None:
    plan = PagePlan(
        title="No FM",
        front_matter_pages=0,
        blank_reverse_pages=True,
        pages=[PageEntry(id="p1", story_page=1, title="A")],
    )
    save_page_plan(plan, root=tmp_project)
    mapper = PhysicalPageMapper(root=tmp_project)
    assert mapper.story_to_physical(1) == {"illustrated": 1, "blank_reverse": 2}


def test_missing_story_page_raises(tmp_project: Path) -> None:
    mapper = PhysicalPageMapper(root=tmp_project)
    with pytest.raises(ValidationError):
        mapper.story_to_physical(99)
