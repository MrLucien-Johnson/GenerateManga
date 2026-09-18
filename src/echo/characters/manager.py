"""Generic character manager — no character-specific assumptions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from echo.core.errors import ValidationError
from echo.core.paths import characters_dir, project_root
from echo.core.schemas import ReferenceStatus


class CharacterManager:
    """Load character bibles, continuity notes, and reference statuses.

    Characters live under ``characters/<slug>/`` with optional files:
    - ``bible.json`` / ``bible.md`` — identity and appearance
    - ``continuity.json`` — continuity constraints
    - ``references/`` — reference images
    - ``references/status.json`` — per-asset ReferenceStatus map
    """

    def __init__(self, *, root: Path | None = None) -> None:
        self.root = root or project_root()
        self.base = characters_dir(self.root)

    def list_characters(self) -> list[str]:
        if not self.base.is_dir():
            return []
        return sorted(
            p.name
            for p in self.base.iterdir()
            if p.is_dir() and not p.name.startswith(".")
        )

    def character_dir(self, slug: str) -> Path:
        path = self.base / slug
        if not path.is_dir():
            raise ValidationError(
                f"Character '{slug}' not found.",
                hint=f"Expected directory at {path}",
            )
        return path

    def load_bible(self, slug: str) -> dict[str, Any]:
        """Load character bible as a dict (JSON preferred, MD as text body)."""
        cdir = self.character_dir(slug)
        json_path = cdir / "bible.json"
        if json_path.is_file():
            data = json.loads(json_path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValidationError(f"bible.json for '{slug}' must be an object.")
            return data
        md_path = cdir / "bible.md"
        if md_path.is_file():
            return {"slug": slug, "text": md_path.read_text(encoding="utf-8")}
        return {"slug": slug, "text": "", "notes": "No bible file present."}

    def load_continuity(self, slug: str) -> dict[str, Any]:
        cdir = self.character_dir(slug)
        path = cdir / "continuity.json"
        if not path.is_file():
            return {"slug": slug, "rules": [], "notes": ""}
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValidationError(f"continuity.json for '{slug}' must be an object.")
        return data

    def references_dir(self, slug: str) -> Path:
        return self.character_dir(slug) / "references"

    def list_reference_files(self, slug: str) -> list[Path]:
        ref_dir = self.references_dir(slug)
        if not ref_dir.is_dir():
            return []
        return sorted(
            p
            for p in ref_dir.iterdir()
            if p.is_file()
            and p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
            and p.name != "status.json"
        )

    def load_reference_statuses(self, slug: str) -> dict[str, ReferenceStatus]:
        """Return map of reference filename -> ReferenceStatus."""
        ref_dir = self.references_dir(slug)
        status_path = ref_dir / "status.json"
        statuses: dict[str, ReferenceStatus] = {}
        if status_path.is_file():
            raw = json.loads(status_path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                for name, value in raw.items():
                    try:
                        statuses[name] = ReferenceStatus(value)
                    except ValueError:
                        statuses[name] = ReferenceStatus.MISSING

        # Ensure every image file has an entry.
        for path in self.list_reference_files(slug):
            statuses.setdefault(path.name, ReferenceStatus.GENERATED)

        if not statuses and not self.list_reference_files(slug):
            # No references at all.
            statuses["__character__"] = ReferenceStatus.MISSING
        return statuses

    def save_reference_statuses(
        self,
        slug: str,
        statuses: dict[str, ReferenceStatus | str],
    ) -> Path:
        ref_dir = self.references_dir(slug)
        ref_dir.mkdir(parents=True, exist_ok=True)
        path = ref_dir / "status.json"
        serializable = {
            name: (value.value if isinstance(value, ReferenceStatus) else str(value))
            for name, value in statuses.items()
        }
        path.write_text(json.dumps(serializable, indent=2) + "\n", encoding="utf-8")
        return path

    def set_reference_status(
        self,
        slug: str,
        filename: str,
        status: ReferenceStatus,
    ) -> dict[str, ReferenceStatus]:
        statuses = self.load_reference_statuses(slug)
        statuses.pop("__character__", None)
        statuses[filename] = status
        self.save_reference_statuses(slug, statuses)
        return statuses

    def overall_reference_status(self, slug: str) -> ReferenceStatus:
        """Aggregate status: LOCKED if all locked; else worst status wins."""
        statuses = self.load_reference_statuses(slug)
        if not statuses or set(statuses) == {"__character__"}:
            return ReferenceStatus.MISSING
        values = [s for name, s in statuses.items() if name != "__character__"]
        if not values:
            return ReferenceStatus.MISSING
        if all(s == ReferenceStatus.LOCKED for s in values):
            return ReferenceStatus.LOCKED
        if all(s in (ReferenceStatus.APPROVED, ReferenceStatus.LOCKED) for s in values):
            return ReferenceStatus.APPROVED
        if any(s == ReferenceStatus.MISSING for s in values):
            return ReferenceStatus.MISSING
        return ReferenceStatus.GENERATED

    def summary(self, slug: str) -> dict[str, Any]:
        return {
            "slug": slug,
            "bible": self.load_bible(slug),
            "continuity": self.load_continuity(slug),
            "reference_status": self.overall_reference_status(slug).value,
            "references": {
                name: status.value
                for name, status in self.load_reference_statuses(slug).items()
            },
        }
