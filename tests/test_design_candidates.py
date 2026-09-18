"""Design candidate list / select / canonicalize."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from echo.characters.design_candidates import (
    DesignCandidate,
    DesignCandidateStatus,
    canonicalize_reference_pack,
    list_candidates,
    load_candidate,
    master_design_selected,
    reject_candidate,
    save_candidate,
    select_master,
)
from echo.core.errors import GateBlocked, ValidationError
from echo.core.schemas import SourceType
from echo.core.state import load_state


def _real_candidate(tmp_project: Path, label: str = "A") -> DesignCandidate:
    d = tmp_project / "characters" / "kaito" / "design-candidates"
    d.mkdir(parents=True, exist_ok=True)
    img = d / f"cand_{label}.png"
    Image.new("RGB", (64, 64), "white").save(img)
    cand = DesignCandidate(
        label=label,
        character_id="kaito",
        status=DesignCandidateStatus.AWAITING_DESIGN_SELECTION,
        backend="local",
        model="test-model",
        seed=42,
        source_type=SourceType.REAL,
        production_eligible=True,
        image_path=str(img.relative_to(tmp_project)),
    )
    save_candidate(cand, root=tmp_project)
    return cand


def test_list_save_load_roundtrip(tmp_project: Path) -> None:
    cand = _real_candidate(tmp_project, "B")
    loaded = load_candidate(cand.id, root=tmp_project)
    assert loaded.label == "B"
    assert loaded.status == DesignCandidateStatus.AWAITING_DESIGN_SELECTION
    listed = list_candidates(root=tmp_project)
    assert any(c.id == cand.id for c in listed)


def test_select_master_sets_gate(tmp_project: Path) -> None:
    cand = _real_candidate(tmp_project, "C")
    assert master_design_selected(root=tmp_project) is False
    selected = select_master(cand.id, root=tmp_project)
    assert selected.status == DesignCandidateStatus.SELECTED
    assert master_design_selected(root=tmp_project) is True
    state = load_state(root=tmp_project)
    assert state.gates.kaito_master_design_selected is True


def test_select_refuses_non_eligible(tmp_project: Path) -> None:
    cand = _real_candidate(tmp_project, "D")
    cand.production_eligible = False
    save_candidate(cand, root=tmp_project)
    with pytest.raises(ValidationError):
        select_master(cand.id, root=tmp_project)


def test_canonicalize_after_select(tmp_project: Path) -> None:
    cand = _real_candidate(tmp_project, "A")
    with pytest.raises(GateBlocked):
        canonicalize_reference_pack(root=tmp_project)
    select_master(cand.id, root=tmp_project)
    report = canonicalize_reference_pack(root=tmp_project)
    assert report["canonicalized"] is True
    assert report["selected_id"] == cand.id
    assert (tmp_project / "characters" / "kaito" / "references" / "kaito_master_design.png").is_file()


def test_reject_candidate(tmp_project: Path) -> None:
    cand = _real_candidate(tmp_project, "A")
    rejected = reject_candidate(cand.id, root=tmp_project, reason="off model")
    assert rejected.status == DesignCandidateStatus.REJECTED
    with pytest.raises(ValidationError):
        select_master(cand.id, root=tmp_project)
