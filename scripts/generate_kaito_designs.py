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

# Distinct exploration angles — same character bible, different presentation cues.
DESIGN_VARIATIONS = {
    "A": (
        "Design exploration A: confident curious expression, front three-quarter full-body, "
        "hood down, messy spiky hair fully visible, jacket unzipped slightly, hands free at sides."
    ),
    "B": (
        "Design exploration B: softer thoughtful expression, clear face close-up inset plus full-body, "
        "slightly different spiky hair clumps but same silhouette family, hood down, standing relaxed."
    ),
    "C": (
        "Design exploration C: adventurous grin, three-quarter view, hood half-up showing hair spikes, "
        "same hooded jacket design, dynamic but readable silhouette for coloring book."
    ),
    "D": (
        "Design exploration D: focused creative expression, full-body holding a sketchbook under one arm, "
        "same trainers and trousers, unmistakable teenage proportions, clean white background."
    ),
}


def _build_design_prompt(bible: dict, label: str) -> tuple[str, str]:
    appearance = (
        bible.get("prompt")
        or bible.get("appearance")
        or ""
    )
    variation = DESIGN_VARIATIONS.get(label.upper(), DESIGN_VARIATIONS["A"])
    parts = [
        MASTER_VISUAL_STYLE.strip(),
        COLORING_BOOK_RULES.strip(),
        (
            "Professional Japanese manga protagonist CHARACTER DESIGN SHEET. "
            "Black and white clean ink line art only. Pure white background. "
            "No grayscale, no gradients, no color, no screentones, no painted shading. "
            "Coloring-book compatible. Single character: Kaito."
        ),
        variation,
        (
            "Include readable full-body figure plus a larger face/head detail in the same sheet "
            "composition without written labels or text of any kind."
        ),
        f"Name: {bible.get('name', 'Kaito')}",
        f"Age: {bible.get('age', 14)} — unmistakably a 14-year-old boy, NOT an adult.",
        str(appearance),
    ]
    for key in (
        "face_shape",
        "eye_shape",
        "hairstyle",
        "hair_silhouette",
        "approximate_height",
        "body_proportions",
    ):
        if bible.get(key):
            parts.append(f"{key}: {bible[key]}")
    clothing = bible.get("clothing") or {}
    if isinstance(clothing, dict) and clothing.get("default_outfit"):
        parts.append(f"outfit: {clothing['default_outfit']}")
    jacket = bible.get("jacket_design") or {}
    if isinstance(jacket, dict):
        parts.append(f"jacket: {json.dumps(jacket)}")
    personality = bible.get("personality")
    if personality:
        parts.append(f"personality cues in posing: {personality}")
    constants = bible.get("must_remain_constant") or []
    if constants:
        parts.append("Must remain constant: " + "; ".join(str(c) for c in constants))
    parts.append(
        "Distinctive recognizable silhouette. Relatable creative teen, not a superhero. "
        "No speech bubbles, no captions, no watermarks, no logos, no gibberish text."
    )
    return "\n\n".join(p for p in parts if p), NEGATIVE_CONSTRAINTS.strip()


def _resolve_real_backend(project: Path):
    """Resolve a non-mock backend or die. Prefer local → hf → free_remote → colab note."""
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

    preferred = str(gen.get("default_backend") or "local").lower()
    if preferred == "mock":
        die(
            "default_backend is mock — design candidates require a REAL backend.",
            hint="Set default_backend to local|huggingface|free_remote|colab.",
        )

    # Try preferred first, then fallbacks that can actually produce images here.
    candidates = [preferred]
    for name in ("local", "huggingface", "free_remote"):
        if name not in candidates:
            candidates.append(name)

    last_reason = ""
    for name in candidates:
        if name == "mock":
            continue
        backend = get_backend(name, root=project)
        ok, reason = backend.available()
        if ok and backend.name != "mock":
            if name != preferred:
                print(f"Note: preferred backend '{preferred}' unavailable; using '{name}'.")
                print(f"  ({last_reason or reason})")
            return backend, name
        last_reason = reason

    die(
        f"No REAL image backend available. Last error: {last_reason}",
        hint=(
            "Install local GPU stack, set HF_TOKEN, ensure network for free_remote, "
            "or use colab/echo_of_the_inkwell_generator.ipynb then "
            "scripts/import_colab_kaito_designs.py"
        ),
    )
    raise AssertionError  # unreachable


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
