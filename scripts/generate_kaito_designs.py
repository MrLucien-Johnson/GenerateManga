#!/usr/bin/env python3
"""Generate N=4 Kaito master design candidates (does NOT select a winner).

Refuses the mock backend — dies if only mock is available.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _cli_common import (  # noqa: E402
    die,
    handle_cli_errors,
    load_character_bible,
    root,
)

from echo.characters.design_candidates import (  # noqa: E402
    DesignCandidate,
    DesignCandidateStatus,
    design_candidates_dir,
    save_candidate,
)
from echo.core.config import get_config, mock_generation_enabled  # noqa: E402
from echo.core.schemas import SourceType  # noqa: E402
from echo.generation.metadata import create_record  # noqa: E402
from echo.generation.registry import get_backend  # noqa: E402
from echo.prompts.style import COLORING_BOOK_RULES, MASTER_VISUAL_STYLE, NEGATIVE_CONSTRAINTS  # noqa: E402


LABELS = ("A", "B", "C", "D")


def _build_design_prompt(bible: dict, label: str) -> tuple[str, str]:
    appearance = (
        bible.get("prompt")
        or bible.get("appearance")
        or ""
    )
    parts = [
        MASTER_VISUAL_STYLE.strip(),
        COLORING_BOOK_RULES.strip(),
        "KAITO MASTER DESIGN CANDIDATE — full-body character design sheet, front three-quarter view.",
        f"Candidate label: {label}",
        f"Name: {bible.get('name', 'Kaito')}",
        f"Age: {bible.get('age', 14)}",
        str(appearance),
    ]
    for key in (
        "face_shape",
        "eye_shape",
        "hairstyle",
        "hair_silhouette",
        "approximate_height",
    ):
        if bible.get(key):
            parts.append(f"{key}: {bible[key]}")
    clothing = bible.get("clothing") or {}
    if isinstance(clothing, dict) and clothing.get("default_outfit"):
        parts.append(f"outfit: {clothing['default_outfit']}")
    jacket = bible.get("jacket_design") or {}
    if isinstance(jacket, dict):
        parts.append(f"jacket: {json.dumps(jacket)}")
    constants = bible.get("must_remain_constant") or []
    if constants:
        parts.append("Must remain constant: " + "; ".join(str(c) for c in constants))
    parts.append(
        "Clean black-and-white manga line art, coloring-book friendly, "
        "consistent proportions, white background, no text, no watermark."
    )
    return "\n\n".join(p for p in parts if p), NEGATIVE_CONSTRAINTS.strip()


def _resolve_real_backend(project: Path):
    """Resolve a non-mock backend or die."""
    if mock_generation_enabled(root=project):
        die(
            "Mock generation is enabled — generate_kaito_designs refuses mock.",
            hint="Unset ECHO_MOCK_GENERATION and set generation.json use_mock_backend=false.",
        )
    try:
        gen = get_config("generation", root=project, use_cache=False)
    except Exception:
        gen = {}
    if gen.get("use_mock_backend"):
        die("generation.json use_mock_backend is true — refusing mock for design candidates.")

    default = str(gen.get("default_backend") or "local").lower()
    if default == "mock":
        die(
            "default_backend is mock — design candidates require a REAL backend.",
            hint="Set default_backend to local|huggingface|colab with credentials/model configured.",
        )

    backend = get_backend(default, root=project)
    ok, reason = backend.available()
    if not ok:
        die(
            f"Backend '{default}' unavailable: {reason}",
            hint="Configure a local model path or HF_TOKEN. This script will not fall back to mock.",
        )
    if backend.name == "mock":
        die("Resolved backend is mock — refusing.")
    return backend, default


@handle_cli_errors
def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Kaito master design candidates (no auto-select).")
    parser.add_argument("--count", type=int, default=None, help="Number of candidates (default 4)")
    parser.add_argument("--seed-base", type=int, default=None, help="Base seed (default from prompt hash)")
    args = parser.parse_args()

    project = root()
    try:
        gen = get_config("generation", root=project, use_cache=False)
    except Exception:
        gen = {}
    design_cfg = gen.get("design_candidates") or {}
    try:
        design = get_config("design", root=project, use_cache=False)
    except Exception:
        design = {}

    count = int(args.count or design_cfg.get("count") or design.get("candidate_count") or 4)
    width = int(design_cfg.get("width") or design.get("candidate_width") or 1024)
    height = int(design_cfg.get("height") or design.get("candidate_height") or 1024)
    labels = list(design_cfg.get("labels") or LABELS)[:count]
    while len(labels) < count:
        labels.append(chr(ord("A") + len(labels)))

    backend, backend_name = _resolve_real_backend(project)
    bible = load_character_bible("kaito", project=project)
    out_dir = design_candidates_dir(root=project, character_id="kaito")

    seed_base = args.seed_base
    if seed_base is None:
        digest = hashlib.sha256(b"kaito-master-design").hexdigest()
        seed_base = int(digest[:8], 16)

    print(f"Backend: {backend_name} (REAL required)")
    print(f"Generating {count} candidates at {width}x{height} into {out_dir}")
    print("NOTE: This script does NOT select a winner.")

    for i, label in enumerate(labels):
        positive, negative = _build_design_prompt(bible, label)
        seed = seed_base + i * 97
        image_path = out_dir / f"candidate_{label.lower()}_{seed}.png"
        result = backend.generate(
            prompt=positive,
            negative_prompt=negative,
            width=width,
            height=height,
            seed=seed,
            output_path=image_path,
            settings={"kind": "kaito_master_design", "label": label},
        )
        if not result.success or not result.output_path:
            die(f"Candidate {label} failed: {result.error or 'no output'}")

        meta = result.metadata or {}
        source = str(meta.get("source_type") or "REAL").upper()
        if source == "MOCK" or backend_name == "mock":
            die(f"Candidate {label} came back as MOCK — aborting.")

        record = create_record(
            page_id=f"kaito_design_{label.lower()}",
            backend=backend_name,
            model=result.model,
            seed=result.seed,
            positive_prompt=positive,
            negative_prompt=negative,
            width=width,
            height=height,
            output_path=result.output_path,
            settings={"kind": "kaito_master_design", "label": label},
            source_type=SourceType.REAL,
            production_eligible=True,
            root=project,
        )

        candidate = DesignCandidate(
            label=label,
            character_id="kaito",
            status=DesignCandidateStatus.AWAITING_DESIGN_SELECTION,
            backend=backend_name,
            model=result.model,
            seed=result.seed,
            source_type=SourceType.REAL,
            production_eligible=True,
            positive_prompt=positive,
            negative_prompt=negative,
            width=width,
            height=height,
            image_path=str(Path(result.output_path).relative_to(project))
            if Path(result.output_path).is_relative_to(project)
            else str(result.output_path),
            generation_record_id=record.id,
        )
        path = save_candidate(candidate, root=project)
        print(f"  [{label}] seed={result.seed} -> {path.name} + {image_path.name}")

    print("Done. Review candidates in Streamlit 'Kaito Master Design' — do not auto-select.")


if __name__ == "__main__":
    main()
