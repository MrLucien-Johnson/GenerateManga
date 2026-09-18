"""Domain schemas for Echo of the Inkwell production pipeline."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


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


class SourceType(str, Enum):
    """Provenance of a generation — mock placeholders vs real model output."""

    MOCK = "MOCK"
    REAL = "REAL"
    UNKNOWN = "UNKNOWN"


class ProductionGates(BaseModel):
    """Hard gates that must pass before later pipeline stages."""

    kaito_reference_approved: bool = False
    kaito_master_design_selected: bool = False
    pilot_approved: bool = False
    pdf_ready: bool = False
    notes: dict[str, str] = Field(default_factory=dict)

    def is_open(self, gate: str) -> bool:
        mapping = {
            "KAITO_REFERENCE_APPROVED": self.kaito_reference_approved,
            "KAITO_MASTER_DESIGN_SELECTED": self.kaito_master_design_selected,
            "PILOT_APPROVED": self.pilot_approved,
            "PDF_READY": self.pdf_ready,
        }
        key = gate.upper()
        if key not in mapping:
            raise KeyError(f"Unknown gate: {gate}")
        return mapping[key]


class GenerationRecord(BaseModel):
    """Metadata for a single generation attempt."""

    model_config = ConfigDict(protected_namespaces=())

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
    source_type: SourceType = SourceType.UNKNOWN
    production_eligible: bool = False
    model_revision: str | None = None
    license_notes: str | None = None

    def touch(self) -> None:
        self.updated_at = _utcnow()

    def is_mock(self) -> bool:
        """True when provenance is mock placeholders (never production)."""
        if self.source_type == SourceType.MOCK:
            return True
        if str(self.backend).strip().lower() == "mock":
            return True
        return False

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
