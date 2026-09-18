"""Phase 12: mock assets cannot enter production paths."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from echo.characters.design_candidates import (
    DesignCandidate,
    DesignCandidateStatus,
    canonicalize_reference_pack,
    save_candidate,
    select_master,
)
from echo.continuity.gates import (
    GateName,
    assert_no_mock_for_kaito_gate,
    evaluate_pdf_ready,
    set_gate,
)
from echo.core.errors import GateBlocked, ValidationError
from echo.core.schemas import ArtStatus, SourceType
from echo.core.state import load_state, save_state
from echo.generation.metadata import create_record
from echo.generation.mock_backend import MockGenerationBackend
from echo.publishing.kdp import build_kdp_pdf
from echo.review.approval import ApprovalWorkflow


def _write_mock_kaito_ref(tmp_project: Path) -> str:
    """Create a mock-backed Kaito reference slot + generation record."""
    backend = MockGenerationBackend(root=tmp_project)
    out = tmp_project / "characters" / "kaito" / "references" / "kaito_front.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    result = backend.generate(prompt="kaito front", width=64, height=64, seed=1, output_path=out)
    record = create_record(
        page_id="ref_kaito_front",
        panel_id="front",
        backend="mock",
        seed=result.seed,
        output_path=result.output_path,
        root=tmp_project,
    )
    cont = {
        "character_id": "kaito",
        "reference_slots": {
            "front": {
                "filename": "kaito_front.png",
                "status": "APPROVED",
                "path": "characters/kaito/references/kaito_front.png",
                "generation_record_id": record.id,
            }
        },
        "production_gate": {"KAITO_REFERENCE_APPROVED": False},
        "master_design": {
            "selected_id": None,
            "KAITO_MASTER_DESIGN_SELECTED": False,
            "candidates_dir": "characters/kaito/design-candidates",
        },
    }
    (tmp_project / "characters" / "kaito" / "continuity.json").write_text(
        __import__("json").dumps(cont, indent=2) + "\n",
        encoding="utf-8",
    )
    return record.id


def test_mock_cannot_open_kaito_reference_approved(tmp_project: Path) -> None:
    _write_mock_kaito_ref(tmp_project)
    with pytest.raises(GateBlocked):
        assert_no_mock_for_kaito_gate(root=tmp_project)
    with pytest.raises(GateBlocked):
        set_gate(GateName.KAITO_REFERENCE_APPROVED, True, root=tmp_project)


def test_mock_cannot_approve_into_production(tmp_project: Path) -> None:
    backend = MockGenerationBackend(root=tmp_project)
    out = tmp_project / "generations" / "mock_art.png"
    result = backend.generate(prompt="x", width=64, height=64, seed=2, output_path=out)
    record = create_record(
        page_id="p1",
        backend="mock",
        seed=result.seed,
        output_path=result.output_path,
        root=tmp_project,
    )
    assert record.is_mock()
    assert record.production_eligible is False
    with pytest.raises(ValidationError, match="MOCK|production_eligible"):
        ApprovalWorkflow(root=tmp_project).approve(record.id)


def test_mock_cannot_enter_production_pdf(tmp_project: Path) -> None:
    backend = MockGenerationBackend(root=tmp_project)
    out = tmp_project / "generations" / "page.png"
    result = backend.generate(prompt="page", width=64, height=64, seed=3, output_path=out)
    record = create_record(
        page_id="p1",
        backend="mock",
        seed=result.seed,
        output_path=result.output_path,
        root=tmp_project,
    )
    # Force-approve for tests only, then PDF must still refuse.
    ApprovalWorkflow(root=tmp_project).approve(
        record.id, dest_name="p1.png", force_non_production=True
    )
    state = load_state(root=tmp_project)
    state.gates.kaito_reference_approved = True
    state.gates.pilot_approved = True
    state.gates.kaito_master_design_selected = True
    save_state(state, root=tmp_project)

    report = evaluate_pdf_ready(root=tmp_project, min_approved=1)
    assert report["pdf_ready"] is False
    assert report["production_assets_ok"] is False

    with pytest.raises(GateBlocked):
        build_kdp_pdf(root=tmp_project, require_gates=True)


def test_no_master_selected_by_default(tmp_project: Path) -> None:
    state = load_state(root=tmp_project)
    assert state.gates.kaito_master_design_selected is False
    cont = __import__("json").loads(
        (tmp_project / "characters" / "kaito" / "continuity.json").read_text(encoding="utf-8")
    )
    master = cont.get("master_design") or {}
    assert not master.get("selected_id")
    assert not master.get("KAITO_MASTER_DESIGN_SELECTED", False)


def test_select_refuses_mock_candidate(tmp_project: Path) -> None:
    img = tmp_project / "characters" / "kaito" / "design-candidates" / "mock.png"
    img.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (32, 32), "white").save(img)
    cand = DesignCandidate(
        label="A",
        character_id="kaito",
        status=DesignCandidateStatus.AWAITING_DESIGN_SELECTION,
        backend="mock",
        source_type=SourceType.MOCK,
        production_eligible=False,
        image_path=str(img.relative_to(tmp_project)),
    )
    save_candidate(cand, root=tmp_project)
    with pytest.raises(ValidationError):
        select_master(cand.id, root=tmp_project)


def test_reference_pack_canonicalization_blocked_without_master(tmp_project: Path) -> None:
    with pytest.raises(GateBlocked):
        canonicalize_reference_pack(root=tmp_project, character_id="kaito")


def test_real_eligible_record_can_approve(tmp_project: Path) -> None:
    out = tmp_project / "generations" / "real.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (64, 64), "white").save(out)
    record = create_record(
        page_id="p1",
        backend="test",
        source_type=SourceType.REAL,
        production_eligible=True,
        output_path=out,
        root=tmp_project,
    )
    approved = ApprovalWorkflow(root=tmp_project).approve(record.id)
    assert approved.status == ArtStatus.APPROVED
