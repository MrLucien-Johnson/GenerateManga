"""Compose generation prompts from style, character, page, and continuity layers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from echo.characters.manager import CharacterManager
from echo.core.config import get_config
from echo.core.paths import project_root, resolve_path
from echo.prompts import history as prompt_history
from echo.prompts.style import COLORING_BOOK_RULES, MASTER_VISUAL_STYLE, NEGATIVE_CONSTRAINTS
from echo.story.page_plan import PageEntry, PanelPlan, load_page_plan


class PromptBuilder:
    """Build layered prompts for a story page (and optional panel)."""

    def __init__(self, *, root: Path | None = None) -> None:
        self.root = root or project_root()
        self.characters = CharacterManager(root=self.root)

    def build(
        self,
        page_id: str,
        *,
        panel_id: str | None = None,
        seed: int | None = None,
        backend: str | None = None,
        save: bool = True,
        extra_positive: str = "",
        extra_negative: str = "",
    ) -> dict[str, Any]:
        plan = load_page_plan(root=self.root)
        page = plan.get_page(page_id)
        panel = self._find_panel(page, panel_id)

        gen_cfg = {}
        try:
            gen_cfg = get_config("generation", root=self.root)
        except Exception:
            gen_cfg = {}

        width = int(gen_cfg.get("width", 2550))
        height = int(gen_cfg.get("height", 3300))
        model = gen_cfg.get("model")
        chosen_backend = backend or gen_cfg.get("default_backend", "mock")
        if seed is None:
            seed = gen_cfg.get("seed")

        char_slugs = panel.characters if panel and panel.characters else page.characters
        location = (panel.location if panel and panel.location else page.location) or ""
        objects = list(panel.objects if panel and panel.objects else page.objects)
        emotion = (panel.emotion if panel and panel.emotion else page.emotion) or ""
        camera = (panel.camera if panel and panel.camera else page.camera) or ""
        description = (panel.description if panel else page.summary) or page.title

        positive_parts = [
            MASTER_VISUAL_STYLE.strip(),
            COLORING_BOOK_RULES.strip(),
            self._character_block(char_slugs),
            self._object_block(objects),
            self._location_block(location),
            f"PAGE: {page.id} (story page {page.story_page}). {page.title}".strip(),
            f"SCENE: {description}".strip(),
        ]
        if panel:
            positive_parts.append(f"PANEL {panel.id}: layout={page.layout}")
        if emotion:
            positive_parts.append(f"EMOTION: {emotion}")
        if camera:
            positive_parts.append(f"CAMERA: {camera}")
        positive_parts.append(self._continuity_block(char_slugs))
        if extra_positive:
            positive_parts.append(extra_positive.strip())

        positive = "\n\n".join(p for p in positive_parts if p)
        negative = NEGATIVE_CONSTRAINTS.strip()
        if extra_negative:
            negative = f"{negative}, {extra_negative.strip()}"

        reference_assets = self._collect_references(char_slugs, objects, location)

        payload: dict[str, Any] = {
            "page_id": page.id,
            "panel_id": panel.id if panel else None,
            "story_page": page.story_page,
            "positive": positive,
            "negative": negative,
            "reference_assets": reference_assets,
            "dimensions": {"width": width, "height": height},
            "model": model,
            "backend": chosen_backend,
            "seed": seed,
            "settings": {
                "layout": page.layout,
                "guidance_scale": gen_cfg.get("guidance_scale", 7.5),
                "num_inference_steps": gen_cfg.get("num_inference_steps", 30),
                "coloring_book": True,
            },
        }
        if save:
            prompt_history.save_prompt(payload, page_id=page.id, root=self.root)
        return payload

    def _find_panel(self, page: PageEntry, panel_id: str | None) -> PanelPlan | None:
        if not panel_id:
            return page.panels[0] if len(page.panels) == 1 else None
        for panel in page.panels:
            if panel.id == panel_id:
                return panel
        return None

    def _character_block(self, slugs: list[str]) -> str:
        if not slugs:
            return ""
        chunks: list[str] = ["CHARACTERS:"]
        for slug in slugs:
            try:
                bible = self.characters.load_bible(slug)
            except Exception:
                chunks.append(f"- {slug}")
                continue
            text = bible.get("prompt") or bible.get("appearance") or bible.get("text") or ""
            name = bible.get("name") or slug
            continuity = ""
            try:
                cont = self.characters.load_continuity(slug)
                rules = cont.get("rules") or []
                if rules:
                    continuity = " Continuity: " + "; ".join(str(r) for r in rules)
            except Exception:
                pass
            chunks.append(f"- {name}: {str(text).strip()}{continuity}".strip())
        return "\n".join(chunks)

    def _load_asset_bible(self, directory: Path, names: tuple[str, ...]) -> dict[str, Any]:
        import json

        for name in names:
            path = directory / name
            if path.is_file():
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return data
        return {}

    def _object_block(self, objects: list[str]) -> str:
        if not objects:
            return ""
        lines = ["OBJECTS:"]
        for obj in objects:
            obj_dir = resolve_path("objects", obj, root=self.root)
            data = self._load_asset_bible(obj_dir, ("bible.json", "object-bible.json"))
            desc = data.get("prompt") or data.get("description") or data.get("summary") or obj
            lines.append(f"- {obj}: {desc}")
        return "\n".join(lines)

    def _location_block(self, location: str) -> str:
        if not location:
            return ""
        loc_dir = resolve_path("locations", location, root=self.root)
        data = self._load_asset_bible(loc_dir, ("bible.json", "location-bible.json"))
        desc = data.get("prompt") or data.get("description") or data.get("summary") or location
        return f"LOCATION: {location} — {desc}"

    def _continuity_block(self, slugs: list[str]) -> str:
        lines = [
            "CONTINUITY: Match locked references exactly. Keep costume, proportions, "
            "and key props consistent with prior approved pages."
        ]
        for slug in slugs:
            try:
                status = self.characters.overall_reference_status(slug)
                lines.append(f"- {slug} reference status: {status.value}")
            except Exception:
                continue
        return "\n".join(lines)

    def _collect_references(
        self,
        characters: list[str],
        objects: list[str],
        location: str,
    ) -> list[str]:
        assets: list[str] = []
        for slug in characters:
            try:
                for path in self.characters.list_reference_files(slug):
                    assets.append(str(path.relative_to(self.root)))
            except Exception:
                continue
        for obj in objects:
            ref = resolve_path("objects", obj, "references", root=self.root)
            if ref.is_dir():
                for path in sorted(ref.glob("*.*")):
                    if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
                        assets.append(str(path.relative_to(self.root)))
        if location:
            ref = resolve_path("locations", location, "references", root=self.root)
            if ref.is_dir():
                for path in sorted(ref.glob("*.*")):
                    if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
                        assets.append(str(path.relative_to(self.root)))
        return assets
