"""Approval workflow state transitions."""

from __future__ import annotations

from pathlib import Path

import pytest

from echo.core.errors import ValidationError
from echo.core.schemas import ArtStatus
from echo.generation.metadata import create_record
from echo.generation.mock_backend import MockGenerationBackend
from echo.review.approval import ApprovalWorkflow


def _generate_record(tmp_project: Path, name: str = "art.png") -> str:
    backend = MockGenerationBackend(root=tmp_project)
    out = tmp_project / "generations" / name
    result = backend.generate(prompt="scene", width=64, height=64, seed=3, output_path=out)
    record = create_record(
        page_id="p1",
        backend="mock",
        seed=result.seed,
        output_path=result.output_path,
        status=ArtStatus.GENERATED,
        root=tmp_project,
    )
    return record.id


def test_approve_sets_status_and_copies(tmp_project: Path) -> None:
    record_id = _generate_record(tmp_project)
    approved = ApprovalWorkflow(root=tmp_project).approve(record_id)
    assert approved.status == ArtStatus.APPROVED
    assert approved.approved_path is not None
    assert Path(approved.approved_path).is_file()


def test_approve_twice_blocked_without_force(tmp_project: Path) -> None:
    record_id = _generate_record(tmp_project)
    workflow = ApprovalWorkflow(root=tmp_project)
    workflow.approve(record_id)
    with pytest.raises(ValidationError):
        workflow.approve(record_id)


def test_reject_from_generated(tmp_project: Path) -> None:
    record_id = _generate_record(tmp_project, name="rej.png")
    rejected = ApprovalWorkflow(root=tmp_project).reject(record_id, reason="off-model")
    assert rejected.status == ArtStatus.REJECTED
    assert rejected.error == "off-model"
    assert (tmp_project / "rejected" / "rej.png").is_file()


def test_cannot_reject_approved(tmp_project: Path) -> None:
    record_id = _generate_record(tmp_project, name="keep.png")
    workflow = ApprovalWorkflow(root=tmp_project)
    workflow.approve(record_id)
    with pytest.raises(ValidationError):
        workflow.reject(record_id)


def test_unapprove_returns_to_generated(tmp_project: Path) -> None:
    record_id = _generate_record(tmp_project, name="un.png")
    workflow = ApprovalWorkflow(root=tmp_project)
    workflow.approve(record_id)
    restored = workflow.unapprove(record_id)
    assert restored.status == ArtStatus.GENERATED
