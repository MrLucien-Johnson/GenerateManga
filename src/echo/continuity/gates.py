"""Production gates: reference approval, pilot approval, PDF readiness."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any

from echo.characters.manager import CharacterManager
from echo.core.errors import GateBlocked
from echo.core.paths import approved_dir, project_root
from echo.core.schemas import ProductionGates, ReferenceStatus
from echo.core.state import load_state, save_state


class GateName(str, Enum):
    KAITO_REFERENCE_APPROVED = "KAITO_REFERENCE_APPROVED"
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


def set_gate(
    gate: GateName | str,
    value: bool = True,
    *,
    root: Path | None = None,
    note: str | None = None,
) -> ProductionGates:
    """Persist a gate flag."""
    state = load_state(root=root)
    name = gate.value if isinstance(gate, GateName) else str(gate).upper()
    if name == GateName.KAITO_REFERENCE_APPROVED.value:
        state.gates.kaito_reference_approved = value
    elif name == GateName.PILOT_APPROVED.value:
        state.gates.pilot_approved = value
    elif name == GateName.PDF_READY.value:
        state.gates.pdf_ready = value
    else:
        raise KeyError(f"Unknown gate: {name}")
    if note:
        state.gates.notes[name] = note
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


def evaluate_pdf_ready(
    *,
    root: Path | None = None,
    required_page_ids: list[str] | None = None,
    min_approved: int = 1,
) -> dict[str, Any]:
    """Compute whether a KDP PDF can be built from approved art only.

    PDF READY requires:
    - KAITO_REFERENCE_APPROVED and PILOT_APPROVED gates open (or auto-evaluated)
    - At least ``min_approved`` approved PNG/JPEG files
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
    count_ok = len(approved_files) >= min_approved

    missing_pages: list[str] = []
    if required_page_ids:
        names = {p.stem for p in approved_files}
        for page_id in required_page_ids:
            # Accept exact stem or prefix match (page_id / page_id_panel1).
            if not any(n == page_id or n.startswith(f"{page_id}_") or n.startswith(f"{page_id}-") for n in names):
                missing_pages.append(page_id)

    pages_ok = not missing_pages
    ready = bool(kaito_ok and pilot_ok and count_ok and pages_ok)

    report = {
        "pdf_ready": ready,
        "kaito_reference_approved": kaito_ok,
        "pilot_approved": pilot_ok,
        "approved_count": len(approved_files),
        "min_approved": min_approved,
        "missing_pages": missing_pages,
        "approved_files": [str(p.relative_to(root)) for p in approved_files],
    }

    # Sync computed PDF_READY onto state when it flips.
    if state.gates.pdf_ready != ready:
        state.gates.pdf_ready = ready
        if kaito_ok and not state.gates.kaito_reference_approved:
            state.gates.kaito_reference_approved = True
        save_state(state, root=root)

    return report
