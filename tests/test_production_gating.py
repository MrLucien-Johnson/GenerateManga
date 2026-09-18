"""Production gate evaluation and PDF readiness gating."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from echo.continuity.gates import (
    GateName,
    check_gate,
    evaluate_pdf_ready,
    set_gate,
)
from echo.core.errors import GateBlocked
from echo.core.state import load_state


def test_gates_default_closed(tmp_project: Path) -> None:
    state = load_state(root=tmp_project)
    assert state.gates.kaito_reference_approved is False
    assert state.gates.pilot_approved is False
    assert state.gates.pdf_ready is False
    with pytest.raises(GateBlocked):
        check_gate(GateName.PILOT_APPROVED, root=tmp_project)


def test_set_gate_persists(tmp_project: Path) -> None:
    set_gate(GateName.PILOT_APPROVED, True, root=tmp_project, note="pilot ok")
    assert check_gate(GateName.PILOT_APPROVED, root=tmp_project, raise_if_blocked=False)
    state = load_state(root=tmp_project)
    assert state.gates.notes["PILOT_APPROVED"] == "pilot ok"


def test_pdf_ready_requires_pilot_and_approved_art(tmp_project: Path) -> None:
    report = evaluate_pdf_ready(root=tmp_project, required_page_ids=["p1", "p2"], min_approved=2)
    assert report["pdf_ready"] is False
    assert report["pilot_approved"] is False

    Image.new("RGB", (64, 64), "white").save(tmp_project / "approved" / "p1.png")
    Image.new("RGB", (64, 64), "white").save(tmp_project / "approved" / "p2.png")
    set_gate(GateName.KAITO_REFERENCE_APPROVED, True, root=tmp_project)
    set_gate(GateName.PILOT_APPROVED, True, root=tmp_project)

    report = evaluate_pdf_ready(root=tmp_project, required_page_ids=["p1", "p2"], min_approved=2)
    assert report["pdf_ready"] is True
    assert report["missing_pages"] == []


def test_pdf_ready_reports_missing_pages(tmp_project: Path) -> None:
    Image.new("RGB", (64, 64), "white").save(tmp_project / "approved" / "p1.png")
    set_gate(GateName.KAITO_REFERENCE_APPROVED, True, root=tmp_project)
    set_gate(GateName.PILOT_APPROVED, True, root=tmp_project)
    report = evaluate_pdf_ready(root=tmp_project, required_page_ids=["p1", "p2"], min_approved=1)
    assert report["pdf_ready"] is False
    assert "p2" in report["missing_pages"]
