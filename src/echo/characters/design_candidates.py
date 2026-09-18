"""Kaito master design candidates — list / save / select (never auto-select)."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from echo.core.errors import GateBlocked, ValidationError
from echo.core.paths import ensure_dir, project_root
from echo.core.schemas import SourceType
from echo.core.state import load_state, save_state


class DesignCandidateStatus(str, Enum):
    AWAITING_DESIGN_SELECTION = "AWAITING_DESIGN_SELECTION"
    SELECTED = "SELECTED"
    REJECTED = "REJECTED"


class DesignCandidate(BaseModel):
    """One master-design candidate for Kaito (A–D style)."""

    model_config = ConfigDict(protected_namespaces=())

    id: str = Field(default_factory=lambda: uuid4().hex)
    label: str = ""  # A, B, C, D
    character_id: str = "kaito"
    status: DesignCandidateStatus = DesignCandidateStatus.AWAITING_DESIGN_SELECTION
    backend: str = ""
    model: str | None = None
    seed: int | None = None
    source_type: SourceType = SourceType.UNKNOWN
    production_eligible: bool = False
    model_revision: str | None = None
    license_notes: str | None = None
    positive_prompt: str = ""
    negative_prompt: str = ""
    width: int = 1024
    height: int = 1024
    image_path: str | None = None
    generation_record_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    notes: str = ""

    def is_mock(self) -> bool:
        if self.source_type == SourceType.MOCK:
            return True
        if str(self.backend).strip().lower() == "mock":
            return True
        return False

    def to_json_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


def design_candidates_dir(*, root: Path | None = None, character_id: str = "kaito") -> Path:
    root = root or project_root()
    return ensure_dir(root / "characters" / character_id / "design-candidates")


def candidate_path(candidate_id: str, *, root: Path | None = None, character_id: str = "kaito") -> Path:
    return design_candidates_dir(root=root, character_id=character_id) / f"{candidate_id}.json"


def save_candidate(
    candidate: DesignCandidate,
    *,
    root: Path | None = None,
) -> Path:
    path = candidate_path(candidate.id, root=root, character_id=candidate.character_id)
    path.write_text(
        json.dumps(candidate.to_json_dict(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return path


def load_candidate(
    candidate_id: str,
    *,
    root: Path | None = None,
    character_id: str = "kaito",
) -> DesignCandidate:
    path = candidate_path(candidate_id, root=root, character_id=character_id)
    if not path.is_file():
        raise ValidationError(
            f"Design candidate '{candidate_id}' not found.",
            hint=f"Expected {path}",
        )
    return DesignCandidate.model_validate(json.loads(path.read_text(encoding="utf-8")))


def list_candidates(
    *,
    root: Path | None = None,
    character_id: str = "kaito",
) -> list[DesignCandidate]:
    d = design_candidates_dir(root=root, character_id=character_id)
    out: list[DesignCandidate] = []
    for path in sorted(d.glob("*.json")):
        try:
            out.append(DesignCandidate.model_validate(json.loads(path.read_text(encoding="utf-8"))))
        except Exception:
            continue
    return out


def _update_continuity_master(
    *,
    root: Path,
    character_id: str,
    selected_id: str | None,
    selected: bool,
) -> None:
    cont_path = root / "characters" / character_id / "continuity.json"
    if cont_path.is_file():
        cont = json.loads(cont_path.read_text(encoding="utf-8"))
    else:
        cont = {"character_id": character_id}
    master = cont.get("master_design") or {}
    master["selected_id"] = selected_id
    master["KAITO_MASTER_DESIGN_SELECTED"] = bool(selected)
    master.setdefault(
        "candidates_dir",
        f"characters/{character_id}/design-candidates",
    )
    cont["master_design"] = master
    cont_path.parent.mkdir(parents=True, exist_ok=True)
    cont_path.write_text(json.dumps(cont, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def select_master(
    candidate_id: str,
    *,
    root: Path | None = None,
    character_id: str = "kaito",
) -> DesignCandidate:
    """Select a master design after validation — refuses mock candidates."""
    root = root or project_root()
    candidate = load_candidate(candidate_id, root=root, character_id=character_id)

    if candidate.is_mock() or not candidate.production_eligible:
        raise ValidationError(
            f"Cannot select mock / non-production design candidate '{candidate_id}'.",
            hint="Generate REAL design candidates and mark production_eligible before selecting.",
        )
    if candidate.source_type != SourceType.REAL:
        raise ValidationError(
            f"Design candidate '{candidate_id}' source_type must be REAL (got {candidate.source_type}).",
        )
    if candidate.status == DesignCandidateStatus.REJECTED:
        raise ValidationError(f"Candidate '{candidate_id}' was rejected.")

    # Demote any previously selected candidates.
    for other in list_candidates(root=root, character_id=character_id):
        if other.id == candidate.id:
            continue
        if other.status == DesignCandidateStatus.SELECTED:
            other.status = DesignCandidateStatus.AWAITING_DESIGN_SELECTION
            save_candidate(other, root=root)

    candidate.status = DesignCandidateStatus.SELECTED
    save_candidate(candidate, root=root)
    _update_continuity_master(
        root=root,
        character_id=character_id,
        selected_id=candidate.id,
        selected=True,
    )

    state = load_state(root=root)
    state.gates.kaito_master_design_selected = True
    state.gates.notes["KAITO_MASTER_DESIGN_SELECTED"] = (
        f"Selected candidate {candidate.id} ({candidate.label}) at "
        f"{datetime.now(timezone.utc).isoformat()}"
    )
    save_state(state, root=root)

    # Sync production_gates.json when present.
    gates_path = root / "config" / "production_gates.json"
    if gates_path.is_file():
        data = json.loads(gates_path.read_text(encoding="utf-8"))
        data["KAITO_MASTER_DESIGN_SELECTED"] = True
        gates_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    return candidate


def reject_candidate(
    candidate_id: str,
    *,
    root: Path | None = None,
    character_id: str = "kaito",
    reason: str = "",
) -> DesignCandidate:
    root = root or project_root()
    candidate = load_candidate(candidate_id, root=root, character_id=character_id)
    if candidate.status == DesignCandidateStatus.SELECTED:
        raise ValidationError(
            "Cannot reject the currently selected master — select another first or clear selection.",
        )
    candidate.status = DesignCandidateStatus.REJECTED
    if reason:
        candidate.notes = reason
    save_candidate(candidate, root=root)
    return candidate


def master_design_selected(*, root: Path | None = None, character_id: str = "kaito") -> bool:
    root = root or project_root()
    state = load_state(root=root)
    if state.gates.kaito_master_design_selected:
        return True
    cont_path = root / "characters" / character_id / "continuity.json"
    if cont_path.is_file():
        cont = json.loads(cont_path.read_text(encoding="utf-8"))
        master = cont.get("master_design") or {}
        return bool(master.get("KAITO_MASTER_DESIGN_SELECTED") and master.get("selected_id"))
    return False


def canonicalize_reference_pack(
    *,
    root: Path | None = None,
    character_id: str = "kaito",
) -> dict[str, Any]:
    """Promote the selected master into the canonical reference workflow.

    Blocked until a non-mock master design is selected.
    """
    root = root or project_root()
    if not master_design_selected(root=root, character_id=character_id):
        raise GateBlocked(
            "KAITO_MASTER_DESIGN_SELECTED",
            detail="Reference pack canonicalization requires a selected master design.",
            hint="Generate design candidates and use select_master(id) after human review.",
        )

    cont_path = root / "characters" / character_id / "continuity.json"
    cont = json.loads(cont_path.read_text(encoding="utf-8")) if cont_path.is_file() else {}
    master = cont.get("master_design") or {}
    selected_id = master.get("selected_id")
    if not selected_id:
        raise GateBlocked(
            "KAITO_MASTER_DESIGN_SELECTED",
            detail="master_design.selected_id is missing.",
        )

    candidate = load_candidate(str(selected_id), root=root, character_id=character_id)
    if candidate.is_mock():
        raise ValidationError("Selected master is mock — cannot canonicalize reference pack.")

    # Copy master image into references as design-anchor if present.
    refs = ensure_dir(root / "characters" / character_id / "references")
    copied = None
    if candidate.image_path:
        src = Path(candidate.image_path)
        if not src.is_file():
            src = root / candidate.image_path
        if src.is_file():
            dest = refs / f"{character_id}_master_design.png"
            shutil.copy2(src, dest)
            copied = str(dest.relative_to(root))

    return {
        "canonicalized": True,
        "selected_id": selected_id,
        "master_image": copied,
        "character_id": character_id,
    }
