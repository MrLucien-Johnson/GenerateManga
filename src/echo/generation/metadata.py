"""GenerationRecord create/save/load under ``generations/``."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from echo.core.paths import ensure_dir, generations_dir, project_root
from echo.core.schemas import ArtStatus, GenerationRecord


def _record_dir(record_id: str, *, root: Path | None = None) -> Path:
    return ensure_dir(generations_dir(root) / record_id)


def record_path(record_id: str, *, root: Path | None = None) -> Path:
    return _record_dir(record_id, root=root) / "record.json"


def create_record(
    *,
    page_id: str,
    panel_id: str | None = None,
    backend: str = "mock",
    model: str | None = None,
    seed: int | None = None,
    positive_prompt: str = "",
    negative_prompt: str = "",
    width: int = 1024,
    height: int = 1024,
    output_path: str | Path | None = None,
    reference_assets: list[str] | None = None,
    settings: dict[str, Any] | None = None,
    status: ArtStatus = ArtStatus.GENERATED,
    parent_id: str | None = None,
    root: Path | None = None,
) -> GenerationRecord:
    record = GenerationRecord(
        page_id=page_id,
        panel_id=panel_id,
        backend=backend,
        model=model,
        seed=seed,
        positive_prompt=positive_prompt,
        negative_prompt=negative_prompt,
        width=width,
        height=height,
        status=status,
        output_path=str(output_path) if output_path else None,
        reference_assets=list(reference_assets or []),
        settings=dict(settings or {}),
        parent_id=parent_id,
    )
    save_record(record, root=root)
    return record


def save_record(record: GenerationRecord, *, root: Path | None = None) -> Path:
    record.touch()
    path = record_path(record.id, root=root)
    path.write_text(
        json.dumps(record.to_json_dict(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    # Index by page for quick lookup.
    root = root or project_root()
    index_dir = ensure_dir(generations_dir(root) / "_by_page" / record.page_id)
    (index_dir / f"{record.id}.json").write_text(
        json.dumps({"id": record.id, "status": record.status.value}, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def load_record(record_id: str, *, root: Path | None = None) -> GenerationRecord:
    path = record_path(record_id, root=root)
    if not path.is_file():
        from echo.core.errors import ValidationError

        raise ValidationError(f"Generation record '{record_id}' not found.")
    return GenerationRecord.model_validate(json.loads(path.read_text(encoding="utf-8")))


def list_records_for_page(page_id: str, *, root: Path | None = None) -> list[GenerationRecord]:
    index_dir = generations_dir(root) / "_by_page" / page_id
    if not index_dir.is_dir():
        return []
    records: list[GenerationRecord] = []
    for pointer in sorted(index_dir.glob("*.json")):
        data = json.loads(pointer.read_text(encoding="utf-8"))
        try:
            records.append(load_record(data["id"], root=root))
        except Exception:
            continue
    return records
