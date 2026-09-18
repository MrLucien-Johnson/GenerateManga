"""Schema and enum coverage for Echo domain models."""

from __future__ import annotations

from echo.core.schemas import ArtStatus, GenerationRecord, ProductionGates, ReferenceStatus


def test_reference_status_values() -> None:
    assert ReferenceStatus.MISSING.value == "MISSING"
    assert ReferenceStatus.GENERATED.value == "GENERATED"
    assert ReferenceStatus.APPROVED.value == "APPROVED"
    assert ReferenceStatus.LOCKED.value == "LOCKED"


def test_art_status_values() -> None:
    assert {s.value for s in ArtStatus} == {
        "PENDING",
        "GENERATED",
        "APPROVED",
        "REJECTED",
        "LOCKED",
    }


def test_generation_record_defaults() -> None:
    record = GenerationRecord(page_id="p1")
    assert record.backend == "mock"
    assert record.status == ArtStatus.GENERATED
    assert record.id
    dumped = record.to_json_dict()
    assert dumped["page_id"] == "p1"
    assert "created_at" in dumped


def test_production_gates_is_open() -> None:
    gates = ProductionGates()
    assert gates.is_open("KAITO_REFERENCE_APPROVED") is False
    assert gates.is_open("PILOT_APPROVED") is False
    assert gates.is_open("PDF_READY") is False
    gates.kaito_reference_approved = True
    assert gates.is_open("kaito_reference_approved") is True


def test_production_gates_unknown_raises() -> None:
    gates = ProductionGates()
    try:
        gates.is_open("NOT_A_GATE")
        raised = False
    except KeyError:
        raised = True
    assert raised
