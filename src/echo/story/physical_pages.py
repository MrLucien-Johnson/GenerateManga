"""Map story pages to physical print pages.

Critical rule
-------------
**Story Page N is NOT always Physical Page N.**

When front matter exists (title page, copyright, dedication, etc.), physical
page numbers shift forward. With ``blank_reverse_pages=True`` (default for
coloring-book / single-sided KDP interiors), each illustrated story page
consumes **two** physical pages: the illustrated front and a blank reverse.

Examples
~~~~~~~~
- ``front_matter_pages=0``, ``blank_reverse_pages=True``:
  Story 1 → Physical 1 (art), Physical 2 (blank)
  Story 2 → Physical 3 (art), Physical 4 (blank)

- ``front_matter_pages=2``, ``blank_reverse_pages=True``:
  Front matter occupies physical 1–2.
  Story 1 → Physical 3 (art), Physical 4 (blank)
  Story 2 → Physical 5 (art), Physical 6 (blank)

- ``blank_reverse_pages=False`` (double-sided art):
  Story N → Physical (front_matter_pages + N)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Iterator

from echo.core.errors import ValidationError
from echo.story.page_plan import PagePlan, load_page_plan


class PhysicalPageKind(str, Enum):
    FRONT_MATTER = "front_matter"
    ILLUSTRATED = "illustrated"
    BLANK_REVERSE = "blank_reverse"


@dataclass(frozen=True)
class PhysicalPage:
    physical_number: int  # 1-based print page number
    kind: PhysicalPageKind
    story_page: int | None = None  # story page number when applicable
    page_id: str | None = None
    label: str = ""


class PhysicalPageMapper:
    """Compute physical page layout from a :class:`PagePlan`."""

    def __init__(
        self,
        plan: PagePlan | None = None,
        *,
        front_matter_pages: int | None = None,
        blank_reverse_pages: bool | None = None,
        root: Path | None = None,
    ) -> None:
        self.plan = plan if plan is not None else load_page_plan(root=root)
        self.front_matter_pages = (
            front_matter_pages
            if front_matter_pages is not None
            else self.plan.front_matter_pages
        )
        self.blank_reverse_pages = (
            blank_reverse_pages
            if blank_reverse_pages is not None
            else self.plan.blank_reverse_pages
        )
        if self.front_matter_pages < 0:
            raise ValidationError("front_matter_pages must be >= 0")

    def iter_physical_pages(self) -> Iterator[PhysicalPage]:
        n = 1
        for i in range(self.front_matter_pages):
            yield PhysicalPage(
                physical_number=n,
                kind=PhysicalPageKind.FRONT_MATTER,
                label=f"Front matter {i + 1}",
            )
            n += 1

        for entry in sorted(self.plan.pages, key=lambda p: p.story_page):
            yield PhysicalPage(
                physical_number=n,
                kind=PhysicalPageKind.ILLUSTRATED,
                story_page=entry.story_page,
                page_id=entry.id,
                label=entry.title or entry.id,
            )
            n += 1
            if self.blank_reverse_pages:
                yield PhysicalPage(
                    physical_number=n,
                    kind=PhysicalPageKind.BLANK_REVERSE,
                    story_page=entry.story_page,
                    page_id=entry.id,
                    label=f"Blank reverse of {entry.id}",
                )
                n += 1

    def all_pages(self) -> list[PhysicalPage]:
        return list(self.iter_physical_pages())

    def story_to_physical(self, story_page: int) -> dict[str, int | None]:
        """Map a story page number to illustrated (+ optional blank) physical numbers.

        Returns ``{"illustrated": int, "blank_reverse": int | None}``.
        """
        for page in self.all_pages():
            if page.story_page == story_page and page.kind == PhysicalPageKind.ILLUSTRATED:
                blank = None
                if self.blank_reverse_pages:
                    blank = page.physical_number + 1
                return {"illustrated": page.physical_number, "blank_reverse": blank}
        raise ValidationError(
            f"Story page {story_page} not found.",
            hint="Add it to story/page-plan.json first.",
        )

    def physical_to_story(self, physical_number: int) -> PhysicalPage:
        for page in self.all_pages():
            if page.physical_number == physical_number:
                return page
        raise ValidationError(f"Physical page {physical_number} is out of range.")

    def total_physical_pages(self) -> int:
        return len(self.all_pages())

    def illustrated_physical_number(self, story_page: int) -> int:
        return int(self.story_to_physical(story_page)["illustrated"])  # type: ignore[arg-type]
