"""Load and save project state (gates, progress)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from echo.core.paths import ensure_dir, state_path
from echo.core.schemas import ProductionGates, ProjectState


def load_state(*, root: Path | None = None) -> ProjectState:
    """Load ``config/state.json``, or return a fresh default state."""
    path = state_path(root)
    if not path.is_file():
        return ProjectState()
    raw = json.loads(path.read_text(encoding="utf-8"))
    return ProjectState.model_validate(raw)


def save_state(state: ProjectState, *, root: Path | None = None) -> Path:
    """Persist project state to ``config/state.json``."""
    state.touch()
    path = state_path(root)
    ensure_dir(path.parent)
    path.write_text(
        json.dumps(state.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return path


def update_gates(
    *,
    root: Path | None = None,
    **gate_flags: bool,
) -> ProjectState:
    """Update named gate flags on the persisted state.

    Accepts kwargs matching ``ProductionGates`` field names, e.g.
    ``kaito_reference_approved=True``.
    """
    state = load_state(root=root)
    gates_data = state.gates.model_dump()
    for key, value in gate_flags.items():
        if key not in gates_data:
            raise KeyError(f"Unknown gate field: {key}")
        gates_data[key] = value
    state.gates = ProductionGates.model_validate(gates_data)
    save_state(state, root=root)
    return state


def set_progress(key: str, value: Any, *, root: Path | None = None) -> ProjectState:
    """Set a progress key and persist."""
    state = load_state(root=root)
    state.progress[key] = value
    save_state(state, root=root)
    return state
