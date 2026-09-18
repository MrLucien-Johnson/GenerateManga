"""Continuity checklist items for production review."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable


class ContinuityCategory(str, Enum):
    CHARACTER = "character"
    COSTUME = "costume"
    PROP = "prop"
    LOCATION = "location"
    LIGHTING = "lighting"
    PANEL = "panel"
    TEXT = "text"
    PRINT = "print"


@dataclass
class ContinuityItem:
    id: str
    category: ContinuityCategory
    description: str
    required: bool = True
    checked: bool = False
    notes: str = ""

    def mark(self, checked: bool = True, notes: str = "") -> None:
        self.checked = checked
        if notes:
            self.notes = notes


def default_items() -> list[ContinuityItem]:
    """Canonical continuity checklist from the Echo production spec."""
    specs: list[tuple[str, ContinuityCategory, str]] = [
        ("char_identity", ContinuityCategory.CHARACTER, "Character identity matches locked bible/references"),
        ("char_proportions", ContinuityCategory.CHARACTER, "Proportions and silhouette consistent across pages"),
        ("costume_consistency", ContinuityCategory.COSTUME, "Outfit matches prior approved pages for the scene"),
        ("prop_inkwell", ContinuityCategory.PROP, "Key props (e.g. inkwell) match approved object references"),
        ("location_match", ContinuityCategory.LOCATION, "Background/location matches established setting"),
        ("lighting_mood", ContinuityCategory.LIGHTING, "Lighting/mood consistent with page plan emotion"),
        ("panel_flow", ContinuityCategory.PANEL, "Panel reading order and gutters are clear"),
        ("camera_angles", ContinuityCategory.PANEL, "Camera angles match page plan without conflicting cuts"),
        ("no_baked_text", ContinuityCategory.TEXT, "No dialogue/captions baked into generated art"),
        ("speech_clearance", ContinuityCategory.TEXT, "Speech balloon space left clear in composition"),
        ("line_art_clean", ContinuityCategory.PRINT, "Clean line art suitable for coloring-book / KDP print"),
        ("bleed_safe", ContinuityCategory.PRINT, "Critical content inside safe margins / bleed accounted for"),
        ("page_number", ContinuityCategory.PRINT, "Physical page numbering correct vs story page mapping"),
        ("blank_reverse", ContinuityCategory.PRINT, "Blank reverse pages present when required by KDP config"),
    ]
    return [
        ContinuityItem(id=item_id, category=cat, description=desc)
        for item_id, cat, desc in specs
    ]


@dataclass
class ContinuityChecklist:
    """Mutable checklist used during review / QA."""

    items: list[ContinuityItem] = field(default_factory=default_items)

    def get(self, item_id: str) -> ContinuityItem:
        for item in self.items:
            if item.id == item_id:
                return item
        raise KeyError(f"Unknown continuity item: {item_id}")

    def mark(self, item_id: str, checked: bool = True, notes: str = "") -> ContinuityItem:
        item = self.get(item_id)
        item.mark(checked=checked, notes=notes)
        return item

    def required_incomplete(self) -> list[ContinuityItem]:
        return [i for i in self.items if i.required and not i.checked]

    def is_complete(self) -> bool:
        return not self.required_incomplete()

    def summary(self) -> dict:
        return {
            "total": len(self.items),
            "checked": sum(1 for i in self.items if i.checked),
            "required_incomplete": [i.id for i in self.required_incomplete()],
            "complete": self.is_complete(),
            "items": [
                {
                    "id": i.id,
                    "category": i.category.value,
                    "description": i.description,
                    "required": i.required,
                    "checked": i.checked,
                    "notes": i.notes,
                }
                for i in self.items
            ],
        }

    @classmethod
    def from_checked_ids(cls, checked_ids: Iterable[str]) -> ContinuityChecklist:
        checklist = cls()
        checked = set(checked_ids)
        for item in checklist.items:
            if item.id in checked:
                item.checked = True
        return checklist
