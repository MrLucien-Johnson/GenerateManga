"""Domain schemas for Echo of the Inkwell production pipeline."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ReferenceStatus(str, Enum):
    """Lifecycle of a character/object/location reference asset."""

    MISSING = "MISSING"
    GENERATED = "GENERATED"
    APPROVED = "APPROVED"
    LOCKED = "LOCKED"


class ArtStatus(str, Enum):
    """Lifecycle of a generated art asset."""

    PENDING = "PENDING"
    GENERATED = "GENERATED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    LOCKED = "LOCKED"


class ProductionGates(BaseModel):
    """Hard gates that must pass before later pipeline stages."""

    kaito_reference_approved: bool = False
    pilot_approved: bool = False
    pdf_ready: bool = False
    notes: dict[str, str] = Field(default_factory=dict)

    def is_open(self, gate: str) -> bool:
        mapping = {
            "KAITO_REFERENCE_APPROVED": self.kaito_reference_approved,
            "PILOT_APPROVED": self.pilot_approved,
            "PDF_READY": self.pdf_ready,
        }
        key = gate.upper()
        if key not in mapping:
            raise KeyError(f"Unknown gate: {gate}")
        return mapping[key]


class GenerationRecord(BaseModel):
    """Metadata for a single generation attempt."""

    id: str = Field(default_factory=lambda: uuid4().hex)
    page_id: str
    panel_id: str | None = None
    backend: str = "mock"
    model: str | None = None
    seed: int | None = None
    positive_prompt: str = ""
    negative_prompt: str = ""
    width: int = 1024
    height: int = 1024
    status: ArtStatus = ArtStatus.GENERATED
    output_path: str | None = None
    approved_path: str | None = None
    reference_assets: list[str] = Field(default_factory=list)
    settings: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
    parent_id: str | None = None  # set when regenerating from a prior record

    def touch(self) -> None:
        self.updated_at = _utcnow()

    def to_json_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class ProjectState(BaseModel):
    """Persisted project progress and gate status."""

    gates: ProductionGates = Field(default_factory=ProductionGates)
    current_page_id: str | None = None
    progress: dict[str, Any] = Field(default_factory=dict)
    updated_at: datetime = Field(default_factory=_utcnow)

    def touch(self) -> None:
        self.updated_at = _utcnow()
