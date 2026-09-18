#!/usr/bin/env python3
"""Import packaged Colab Kaito design results into design-candidates/."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _cli_common import die, handle_cli_errors, root  # noqa: E402

from echo.characters.design_candidates import (  # noqa: E402
    DesignCandidate,
    DesignCandidateStatus,
    design_candidates_dir,
    save_candidate,
)
from echo.core.schemas import SourceType  # noqa: E402
from echo.generation.metadata import create_record  # noqa: E402


@handle_cli_errors
def main() -> None:
    parser = argparse.ArgumentParser(description="Import Colab Kaito design package into design-candidates/.")
    parser.add_argument(
        "package",
        type=Path,
        help="Directory or zip containing candidate_*.png + optional manifest.json",
    )
    parser.add_argument(
        "--mark-production-eligible",
        action="store_true",
        help="Mark imported candidates production_eligible=True (default False until review)",
    )
    args = parser.parse_args()

    project = root()
    package = args.package
    if not package.exists():
        die(f"Package not found: {package}")

    work = package
    tmp_extract = None
    if package.is_file() and package.suffix.lower() in {".zip"}:
        import zipfile
        import tempfile

        tmp_extract = Path(tempfile.mkdtemp(prefix="kaito_designs_"))
        with zipfile.ZipFile(package, "r") as zf:
            zf.extractall(tmp_extract)
        work = tmp_extract

    if not work.is_dir():
        die("Package must be a directory or .zip")

    manifest_path = work / "manifest.json"
    manifest: dict = {}
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    images = sorted(
        p
        for p in work.rglob("*")
        if p.is_file() and p.suffix.lower() in {".png", ".jpg", ".jpeg"}
    )
    if not images:
        die("No images found in package.")

    out_dir = design_candidates_dir(root=project, character_id="kaito")
    labels = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    entries = manifest.get("candidates") if isinstance(manifest.get("candidates"), list) else None

    imported = 0
    for idx, img in enumerate(images):
        label = labels[idx] if idx < len(labels) else f"X{idx}"
        meta = {}
        if entries and idx < len(entries) and isinstance(entries[idx], dict):
            meta = entries[idx]
            label = str(meta.get("label") or label)

        dest_name = f"imported_{label.lower()}_{uuid4().hex[:8]}{img.suffix.lower()}"
        dest = out_dir / dest_name
        shutil.copy2(img, dest)

        seed = meta.get("seed")
        model = meta.get("model") or manifest.get("model")
        backend = str(meta.get("backend") or manifest.get("backend") or "colab")
        if backend.lower() == "mock":
            die("Refusing to import mock-backed design candidates.")

        record = create_record(
            page_id=f"kaito_design_{label.lower()}",
            backend=backend,
            model=model,
            seed=seed,
            positive_prompt=str(meta.get("positive_prompt") or ""),
            negative_prompt=str(meta.get("negative_prompt") or ""),
            width=int(meta.get("width") or 1024),
            height=int(meta.get("height") or 1024),
            output_path=dest,
            settings={"kind": "kaito_master_design", "imported": True, "label": label},
            source_type=SourceType.REAL,
            production_eligible=bool(args.mark_production_eligible),
            model_revision=meta.get("model_revision"),
            license_notes=meta.get("license_notes") or manifest.get("license_notes"),
            root=project,
        )

        candidate = DesignCandidate(
            label=label,
            character_id="kaito",
            status=DesignCandidateStatus.AWAITING_DESIGN_SELECTION,
            backend=backend,
            model=model,
            seed=seed,
            source_type=SourceType.REAL,
            production_eligible=bool(args.mark_production_eligible),
            model_revision=meta.get("model_revision"),
            license_notes=meta.get("license_notes") or manifest.get("license_notes"),
            positive_prompt=str(meta.get("positive_prompt") or ""),
            negative_prompt=str(meta.get("negative_prompt") or ""),
            width=int(meta.get("width") or 1024),
            height=int(meta.get("height") or 1024),
            image_path=str(dest.relative_to(project)),
            generation_record_id=record.id,
            notes="Imported from Colab package",
        )
        save_candidate(candidate, root=project)
        print(f"Imported [{label}] -> {dest.relative_to(project)} (eligible={candidate.production_eligible})")
        imported += 1

    print(f"Imported {imported} candidate(s). No winner selected.")
    if tmp_extract and tmp_extract.exists():
        shutil.rmtree(tmp_extract, ignore_errors=True)


if __name__ == "__main__":
    main()
