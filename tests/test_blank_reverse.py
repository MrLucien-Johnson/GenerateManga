"""Blank reverse page behavior for KDP interiors."""

from __future__ import annotations

from pathlib import Path

from echo.story.page_plan import PageEntry, PagePlan, save_page_plan
from echo.story.physical_pages import PhysicalPageKind, PhysicalPageMapper


def test_each_illustrated_page_has_blank_reverse(tmp_project: Path) -> None:
    mapper = PhysicalPageMapper(root=tmp_project)
    illustrated = [p for p in mapper.all_pages() if p.kind == PhysicalPageKind.ILLUSTRATED]
    for art in illustrated:
        blank = mapper.physical_to_story(art.physical_number + 1)
        assert blank.kind == PhysicalPageKind.BLANK_REVERSE
        assert blank.story_page == art.story_page
        assert blank.page_id == art.page_id


def test_blank_reverse_disabled(tmp_project: Path) -> None:
    plan = PagePlan(
        title="No blanks",
        front_matter_pages=1,
        blank_reverse_pages=False,
        pages=[
            PageEntry(id="p1", story_page=1, title="A"),
            PageEntry(id="p2", story_page=2, title="B"),
        ],
    )
    save_page_plan(plan, root=tmp_project)
    mapper = PhysicalPageMapper(root=tmp_project)
    kinds = [p.kind for p in mapper.all_pages()]
    assert PhysicalPageKind.BLANK_REVERSE not in kinds
    assert mapper.total_physical_pages() == 3  # 1 front + 2 art


def test_kdp_config_blank_flag_aligned(tmp_project: Path) -> None:
    from echo.core.config import get_config

    kdp = get_config("kdp", root=tmp_project)
    assert kdp["blank_reverse_pages"] is True
    mapper = PhysicalPageMapper(root=tmp_project)
    assert mapper.blank_reverse_pages is True
