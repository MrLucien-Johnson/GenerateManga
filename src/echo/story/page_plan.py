"""Load/save page-plan.json and update page fields."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from echo.core.errors import ValidationError
from echo.core.paths import ensure_dir, project_root, story_dir

_PAGE_ENTRY_KNOWN = {
    "id",
    "story_page",
    "title",
    "summary",
    "layout",
    "panels",
    "characters",
    "location",
    "objects",
    "emotion",
    "camera",
    "notes",
    "extra",
}


class PanelPlan(BaseModel):
    id: str
    description: str = ""
    dialogue: list[str] = Field(default_factory=list)
    captions: list[str] = Field(default_factory=list)
    camera: str = ""
    emotion: str = ""
    characters: list[str] = Field(default_factory=list)
    location: str | None = None
    objects: list[str] = Field(default_factory=list)


class PageEntry(BaseModel):
    """One story page entry in the page plan."""

    id: str
    story_page: int
    title: str = ""
    summary: str = ""
    layout: str = "1"  # splash | 1 | 2 | 3 | 4
    panels: list[PanelPlan] = Field(default_factory=list)
    characters: list[str] = Field(default_factory=list)
    location: str | None = None
    objects: list[str] = Field(default_factory=list)
    emotion: str = ""
    camera: str = ""
    notes: str = ""
    extra: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def normalize_story_fields(cls, data: Any) -> Any:
        """Accept production story page-plan entries that omit ``id`` / use scene labels."""
        if not isinstance(data, dict):
            return data
        raw = dict(data)
        story_page = raw.get("story_page")
        if "id" not in raw and story_page is not None:
            raw["id"] = f"p{story_page}"
        if not raw.get("title") and raw.get("scene"):
            raw["title"] = str(raw["scene"])
        if not raw.get("summary") and raw.get("action"):
            raw["summary"] = str(raw["action"])
        if not raw.get("camera") and raw.get("camera_notes"):
            raw["camera"] = str(raw["camera_notes"])
        if "layout" not in raw and raw.get("suggested_panel_count") is not None:
            raw["layout"] = str(raw["suggested_panel_count"])
        extra = dict(raw.get("extra") or {})
        for key in list(raw.keys()):
            if key not in _PAGE_ENTRY_KNOWN:
                extra[key] = raw.pop(key)
        if extra:
            raw["extra"] = extra
        return raw


class PagePlan(BaseModel):
    version: int = 1
    title: str = ""
    front_matter_pages: int = 0
    blank_reverse_pages: bool = True
    pages: list[PageEntry] = Field(default_factory=list)
    extra: dict[str, Any] = Field(default_factory=dict)

    @field_validator("version", mode="before")
    @classmethod
    def coerce_version(cls, value: Any) -> int:
        if value is None:
            return 1
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            # Accept semver strings from story packs (e.g. "0.1.0") as major=0 → treat as 1.
            head = value.split(".", 1)[0]
            try:
                parsed = int(head)
            except ValueError as exc:
                raise ValueError(f"Invalid version: {value}") from exc
            return parsed if parsed > 0 else 1
        return int(value)

    @model_validator(mode="before")
    @classmethod
    def stash_unknown_plan_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        raw = dict(data)
        known = {
            "version",
            "title",
            "front_matter_pages",
            "blank_reverse_pages",
            "pages",
            "extra",
        }
        extra = dict(raw.get("extra") or {})
        for key in list(raw.keys()):
            if key not in known:
                extra[key] = raw.pop(key)
        if extra:
            raw["extra"] = extra
        return raw

    def get_page(self, page_id: str | int) -> PageEntry:
        if isinstance(page_id, int):
            for page in self.pages:
                if page.story_page == page_id:
                    return page
            raise ValidationError(f"Story page {page_id} not found in page plan.")
        for page in self.pages:
            if page.id == page_id:
                return page
        raise ValidationError(f"Page id '{page_id}' not found in page plan.")

    def update_page(self, page_id: str | int, **fields: Any) -> PageEntry:
        page = self.get_page(page_id)
        data = page.model_dump()
        for key, value in fields.items():
            if key == "extra" and isinstance(value, dict):
                data.setdefault("extra", {}).update(value)
            elif key in data:
                data[key] = value
            else:
                data.setdefault("extra", {})[key] = value
        updated = PageEntry.model_validate(data)
        for idx, existing in enumerate(self.pages):
            if existing.id == updated.id:
                self.pages[idx] = updated
                break
        return updated


def page_plan_path(root: Path | None = None) -> Path:
    return story_dir(root) / "page-plan.json"


def load_page_plan(*, root: Path | None = None) -> PagePlan:
    path = page_plan_path(root)
    if not path.is_file():
        return PagePlan()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValidationError(f"Invalid page-plan.json: {exc.msg}") from exc
    return PagePlan.model_validate(raw)


def save_page_plan(plan: PagePlan, *, root: Path | None = None) -> Path:
    root = root or project_root()
    path = page_plan_path(root)
    ensure_dir(path.parent)
    path.write_text(
        json.dumps(plan.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return path


def get_page(page_id: str | int, *, root: Path | None = None) -> PageEntry:
    return load_page_plan(root=root).get_page(page_id)


def update_page(page_id: str | int, *, root: Path | None = None, **fields: Any) -> PageEntry:
    plan = load_page_plan(root=root)
    updated = plan.update_page(page_id, **fields)
    save_page_plan(plan, root=root)
    return updated
