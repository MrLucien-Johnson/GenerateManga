"""Panel layout templates: splash and 1–4 panel grids."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PanelRect:
    """Normalized panel rectangle (0–1 fractions of content area)."""

    x: float
    y: float
    w: float
    h: float
    id: str = ""


@dataclass
class PanelLayout:
    name: str
    panels: list[PanelRect]

    def scaled(self, width: int, height: int, gutter: int = 0) -> list[tuple[str, int, int, int, int]]:
        """Return absolute pixel boxes ``(id, left, top, right, bottom)``."""
        boxes: list[tuple[str, int, int, int, int]] = []
        for i, panel in enumerate(self.panels):
            left = int(panel.x * width) + (gutter if panel.x > 0 else 0)
            top = int(panel.y * height) + (gutter if panel.y > 0 else 0)
            right = int((panel.x + panel.w) * width) - (gutter if panel.x + panel.w < 1 else 0)
            bottom = int((panel.y + panel.h) * height) - (gutter if panel.y + panel.h < 1 else 0)
            boxes.append((panel.id or f"p{i+1}", left, top, max(left + 1, right), max(top + 1, bottom)))
        return boxes


_LAYOUTS: dict[str, PanelLayout] = {
    "splash": PanelLayout(
        name="splash",
        panels=[PanelRect(0, 0, 1, 1, "splash")],
    ),
    "1": PanelLayout(
        name="1",
        panels=[PanelRect(0, 0, 1, 1, "p1")],
    ),
    "2": PanelLayout(
        name="2",
        panels=[
            PanelRect(0, 0, 1, 0.5, "p1"),
            PanelRect(0, 0.5, 1, 0.5, "p2"),
        ],
    ),
    "3": PanelLayout(
        name="3",
        panels=[
            PanelRect(0, 0, 1, 0.4, "p1"),
            PanelRect(0, 0.4, 0.5, 0.6, "p2"),
            PanelRect(0.5, 0.4, 0.5, 0.6, "p3"),
        ],
    ),
    "4": PanelLayout(
        name="4",
        panels=[
            PanelRect(0, 0, 0.5, 0.5, "p1"),
            PanelRect(0.5, 0, 0.5, 0.5, "p2"),
            PanelRect(0, 0.5, 0.5, 0.5, "p3"),
            PanelRect(0.5, 0.5, 0.5, 0.5, "p4"),
        ],
    ),
}


def get_layout(name: str) -> PanelLayout:
    key = str(name).strip().lower()
    if key in {"splash", "full"}:
        return _LAYOUTS["splash"]
    if key not in _LAYOUTS:
        # Allow aliases like "2-panel"
        digit = "".join(ch for ch in key if ch.isdigit())
        if digit in _LAYOUTS:
            return _LAYOUTS[digit]
        return _LAYOUTS["1"]
    return _LAYOUTS[key]


def list_layouts() -> list[str]:
    return sorted(_LAYOUTS.keys())


def register_layout(layout: PanelLayout) -> None:
    """Register or override a configurable layout template."""
    _LAYOUTS[layout.name] = layout
