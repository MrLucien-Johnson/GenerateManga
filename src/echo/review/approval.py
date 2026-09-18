"""Approval state machine: GENERATED -> APPROVED / REJECTED.

Never silently overwrites an already-approved asset.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from echo.core.errors import ValidationError
from echo.core.paths import approved_dir, project_root, rejected_dir
from echo.core.schemas import ArtStatus, GenerationRecord
from echo.generation.metadata import load_record, save_record


class ApprovalWorkflow:
    """Manage approval / rejection of generation records."""

    def __init__(self, *, root: Path | None = None) -> None:
        self.root = root or project_root()

    def approve(
        self,
        record_id: str,
        *,
        force: bool = False,
        dest_name: str | None = None,
    ) -> GenerationRecord:
        record = load_record(record_id, root=self.root)
        if record.status == ArtStatus.APPROVED and not force:
            raise ValidationError(
                f"Record '{record_id}' is already APPROVED.",
                hint="Pass force=True to replace the approved copy deliberately.",
            )
        if record.status == ArtStatus.LOCKED and not force:
            raise ValidationError(
                f"Record '{record_id}' is LOCKED and cannot be re-approved.",
                hint="Unlock the asset first if a deliberate replacement is required.",
            )
        if not record.output_path:
            raise ValidationError(f"Record '{record_id}' has no output_path to approve.")
        src = Path(record.output_path)
        if not src.is_file():
            # Allow relative paths from project root.
            candidate = self.root / record.output_path
            if candidate.is_file():
                src = candidate
            else:
                raise ValidationError(f"Generated file missing: {record.output_path}")

        dest_dir = approved_dir(self.root)
        filename = dest_name or src.name
        dest = dest_dir / filename
        if dest.exists() and not force:
            # Never overwrite approved silently — require a distinct name or force.
            if record.approved_path and Path(record.approved_path).resolve() == dest.resolve():
                raise ValidationError(
                    f"Approved file already exists: {dest}",
                    hint="Use force=True to overwrite deliberately.",
                )
            stem, suffix = dest.stem, dest.suffix
            dest = dest_dir / f"{stem}_{record.id[:8]}{suffix}"

        shutil.copy2(src, dest)
        record.status = ArtStatus.APPROVED
        record.approved_path = str(dest)
        save_record(record, root=self.root)
        return record

    def reject(
        self,
        record_id: str,
        *,
        reason: str = "",
        copy_file: bool = True,
    ) -> GenerationRecord:
        record = load_record(record_id, root=self.root)
        if record.status == ArtStatus.APPROVED:
            raise ValidationError(
                f"Record '{record_id}' is APPROVED; refuse to reject without unapprove.",
                hint="Move/replace the approved asset deliberately first.",
            )
        if record.status == ArtStatus.LOCKED:
            raise ValidationError(f"Record '{record_id}' is LOCKED.")

        if copy_file and record.output_path:
            src = Path(record.output_path)
            if not src.is_file():
                src = self.root / record.output_path
            if src.is_file():
                dest = rejected_dir(self.root) / src.name
                shutil.copy2(src, dest)

        record.status = ArtStatus.REJECTED
        if reason:
            record.error = reason
        save_record(record, root=self.root)
        return record

    def unapprove(self, record_id: str) -> GenerationRecord:
        """Move APPROVED back to GENERATED without deleting the approved file."""
        record = load_record(record_id, root=self.root)
        if record.status != ArtStatus.APPROVED:
            raise ValidationError(f"Record '{record_id}' is not APPROVED.")
        record.status = ArtStatus.GENERATED
        save_record(record, root=self.root)
        return record


def approve(record_id: str, *, root: Path | None = None, **kwargs) -> GenerationRecord:
    return ApprovalWorkflow(root=root).approve(record_id, **kwargs)


def reject(record_id: str, *, root: Path | None = None, **kwargs) -> GenerationRecord:
    return ApprovalWorkflow(root=root).reject(record_id, **kwargs)
