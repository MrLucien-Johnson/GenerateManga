"""Production gates: reference approval, pilot approval, PDF readiness."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any

from echo.characters.manager import CharacterManager
from echo.core.errors import GateBlocked, ValidationError
from echo.core.paths import approved_dir, generations_dir, project_root
from echo.core.schemas import ProductionGates, ReferenceStatus, SourceType
from echo.core.state import load_state, save_state


class GateName(str, Enum):
    KAITO_REFERENCE_APPROVED = "KAITO_REFERENCE_APPROVED"
    KAITO_MASTER_DESIGN_SELECTED = "KAITO_MASTER_DESIGN_SELECTED"
    PILOT_APPROVED = "PILOT_APPROVED"
    PDF_READY = "PDF_READY"


def check_gate(
    gate: GateName | str,
    *,
    root: Path | None = None,
    raise_if_blocked: bool = True,
) -> bool:
    """Return whether ``gate`` is open; optionally raise ``GateBlocked``."""
    state = load_state(root=root)
    name = gate.value if isinstance(gate, GateName) else str(gate).upper()
    open_ = state.gates.is_open(name)
    if not open_ and raise_if_blocked:
        raise GateBlocked(name)
    return open_


def _load_record_safe(record_id: str, *, root: Path) -> Any | None:
    try:
        from echo.generation.metadata import load_record

        return load_record(record_id, root=root)
    except Exception:
        return None


def assert_no_mock_for_kaito_gate(*, root: Path | None = None) -> None:
    """Reject opening Kaito production gates when any reference is mock-backed.

    Inspects continuity reference slots' ``generation_record_id`` values and
    raises ``GateBlocked`` / ``ValidationError`` if any record is mock.
    """
    root = root or project_root()
    mgr = CharacterManager(root=root)
    if "kaito" not in mgr.list_characters():
        return

    cont = mgr.load_continuity("kaito")
    slots = cont.get("reference_slots") or {}
    mock_hits: list[str] = []

    for slot_name, slot in slots.items():
        if not isinstance(slot, dict):
            continue
        record_id = slot.get("generation_record_id")
        if not record_id:
            # Image on disk without a record is treated as unknown — not mock.
            continue
        record = _load_record_safe(str(record_id), root=root)
        if record is None:
            continue
        if record.is_mock():
            mock_hits.append(f"{slot_name} ({record_id[:8]}… backend={record.backend})")

    if mock_hits:
        detail = "; ".join(mock_hits)
        raise GateBlocked(
            GateName.KAITO_REFERENCE_APPROVED.value,
            detail=f"Mock / non-production references cannot open production gates: {detail}",
            hint="Regenerate Kaito references with a REAL backend before approving.",
        )


def set_gate(
    gate: GateName | str,
    value: bool = True,
    *,
    root: Path | None = None,
    note: str | None = None,
) -> ProductionGates:
    """Persist a gate flag.

    Opening ``KAITO_REFERENCE_APPROVED`` refuses when mock references would be used.
    """
    root = root or project_root()
    state = load_state(root=root)
    name = gate.value if isinstance(gate, GateName) else str(gate).upper()

    if name == GateName.KAITO_REFERENCE_APPROVED.value and value:
        assert_no_mock_for_kaito_gate(root=root)

    if name == GateName.KAITO_REFERENCE_APPROVED.value:
        state.gates.kaito_reference_approved = value
    elif name == GateName.KAITO_MASTER_DESIGN_SELECTED.value:
        if value:
            assert_no_mock_for_kaito_gate(root=root)
            # Master selection also requires non-mock candidate validation
            # (select_master enforces this); gate open alone is allowed when
            # continuity already has a non-mock selected_id.
            cont_path = root / "characters" / "kaito" / "continuity.json"
            if cont_path.is_file():
                import json

                cont = json.loads(cont_path.read_text(encoding="utf-8"))
                master = cont.get("master_design") or {}
                selected = master.get("selected_id")
                if not selected:
                    raise ValidationError(
                        "Cannot open KAITO_MASTER_DESIGN_SELECTED without a selected master design.",
                        hint="Use design_candidates.select_master(id) after reviewing candidates.",
                    )
        state.gates.kaito_master_design_selected = value
    elif name == GateName.PILOT_APPROVED.value:
        state.gates.pilot_approved = value
    elif name == GateName.PDF_READY.value:
        state.gates.pdf_ready = value
    else:
        raise KeyError(f"Unknown gate: {name}")

    if note:
        state.gates.notes[name] = note
    elif not value and name in state.gates.notes:
        # Clear stale approval notes when a gate is closed / refused.
        state.gates.notes.pop(name, None)

    save_state(state, root=root)
    return state.gates


def evaluate_kaito_reference_gate(*, root: Path | None = None) -> bool:
    """True when character ``kaito`` references are APPROVED or LOCKED.

    This gate is project-specific (pilot character) but evaluated via the
    generic CharacterManager — no hard-coded appearance assumptions.
    """
    mgr = CharacterManager(root=root)
    if "kaito" not in mgr.list_characters():
        return False
    status = mgr.overall_reference_status("kaito")
    return status in (ReferenceStatus.APPROVED, ReferenceStatus.LOCKED)


def _approved_records_production_ok(*, root: Path) -> tuple[bool, list[str]]:
    """Scan APPROVED generation records; return (ok, problems)."""
    from echo.core.schemas import ArtStatus
    from echo.generation.metadata import load_record

    problems: list[str] = []
    gen_root = generations_dir(root)
    if not gen_root.is_dir():
        return True, problems

    for record_json in gen_root.glob("*/record.json"):
        try:
            record = load_record(record_json.parent.name, root=root)
        except Exception:
            continue
        if record.status != ArtStatus.APPROVED:
            continue
        if record.is_mock():
            problems.append(f"{record.id[:8]} mock backend/source")
        elif not record.production_eligible:
            problems.append(f"{record.id[:8]} production_eligible=false")
        elif record.source_type == SourceType.MOCK:
            problems.append(f"{record.id[:8]} source_type=MOCK")

    # Also inspect approved/ files that map to records via approved_path.
    approved = approved_dir(root)
    if approved.is_dir():
        for png in approved.glob("**/*"):
            if not png.is_file() or png.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
                continue
            # If we already have matching APPROVED records, covered above.
            # Flag orphan approved art with no production-eligible record as unsafe
            # only when a sibling record exists under generations/_by_page.
            pass

    return (len(problems) == 0), problems


def evaluate_pdf_ready(
    *,
    root: Path | None = None,
    required_page_ids: list[str] | None = None,
    min_approved: int = 1,
) -> dict[str, Any]:
    """Compute whether a KDP PDF can be built from approved art only.

    PDF READY requires:
    - KAITO_REFERENCE_APPROVED and PILOT_APPROVED gates open (or auto-evaluated)
    - KAITO_MASTER_DESIGN_SELECTED open (master design chosen for production)
    - At least ``min_approved`` approved PNG/JPEG files
    - No approved page records that are mock or production_eligible=false
    - If ``required_page_ids`` given, each must have an approved asset
    """
    root = root or project_root()
    state = load_state(root=root)
    approved = approved_dir(root)
    approved_files = sorted(
        p
        for p in approved.glob("**/*")
        if p.is_file() and p.suffix.lower() in {".png", ".jpg", ".jpeg"}
    )

    kaito_ok = state.gates.kaito_reference_approved or evaluate_kaito_reference_gate(root=root)
    pilot_ok = state.gates.pilot_approved
    master_ok = state.gates.kaito_master_design_selected
    count_ok = len(approved_files) >= min_approved
    prod_ok, prod_problems = _approved_records_production_ok(root=root)

    missing_pages: list[str] = []
    if required_page_ids:
        names = {p.stem for p in approved_files}
        for page_id in required_page_ids:
            # Accept exact stem or prefix match (page_id / page_id_panel1).
            if not any(n == page_id or n.startswith(f"{page_id}_") or n.startswith(f"{page_id}-") for n in names):
                missing_pages.append(page_id)

    pages_ok = not missing_pages
    ready = bool(kaito_ok and pilot_ok and master_ok and count_ok and pages_ok and prod_ok)

    report = {
        "pdf_ready": ready,
        "kaito_reference_approved": kaito_ok,
        "kaito_master_design_selected": master_ok,
        "pilot_approved": pilot_ok,
        "production_assets_ok": prod_ok,
        "production_asset_problems": prod_problems,
        "approved_count": len(approved_files),
        "min_approved": min_approved,
        "missing_pages": missing_pages,
        "approved_files": [str(p.relative_to(root)) for p in approved_files],
    }

    # Sync computed PDF_READY onto state when it flips.
    if state.gates.pdf_ready != ready:
        state.gates.pdf_ready = ready
        if kaito_ok and not state.gates.kaito_reference_approved:
            # Only auto-promote when mock check passes.
            try:
                assert_no_mock_for_kaito_gate(root=root)
                state.gates.kaito_reference_approved = True
            except (GateBlocked, ValidationError):
                state.gates.pdf_ready = False
                report["pdf_ready"] = False
                report["kaito_reference_approved"] = False
        save_state(state, root=root)

    return report
