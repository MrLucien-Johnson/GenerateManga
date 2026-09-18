#!/usr/bin/env python3
"""Generate art for a single story page.

Blocks bulk/production generation when KAITO_REFERENCE_APPROVED is false,
unless --test is passed (labels NON-PRODUCTION TEST).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _cli_common import (  # noqa: E402
    NON_PRODUCTION_LABEL,
    build_page_prompt,
    die,
    gate_open,
    handle_cli_errors,
    install_page_plan_compat,
    page_id_for,
    resolve_generation_backend,
    root,
)

from echo.core.schemas import ArtStatus  # noqa: E402
from echo.core.state import load_state, save_state  # noqa: E402
from echo.generation.metadata import create_record  # noqa: E402
from echo.prompts import history as prompt_history  # noqa: E402


@handle_cli_errors
def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a story page candidate.")
    parser.add_argument("story_page", type=int, help="Story page number (1–50)")
    parser.add_argument(
        "--test",
        action="store_true",
        help="Allow generation when KAITO_REFERENCE_APPROVED is false (NON-PRODUCTION TEST)",
    )
    parser.add_argument("--force-mock", action="store_true", help="Force mock backend")
    parser.add_argument("--seed", type=int, default=None, help="Optional seed override")
    args = parser.parse_args()

    install_page_plan_compat()
    project = root()
    story_page = int(args.story_page)
    if story_page < 1 or story_page > 50:
        die(f"story_page must be 1–50, got {story_page}")

    gate_ok = gate_open("KAITO_REFERENCE_APPROVED", project=project)
    if not gate_ok and not args.test:
        die(
            "KAITO_REFERENCE_APPROVED is false — refusing page generation.",
            hint="Approve Kaito references first, or pass --test for NON-PRODUCTION TEST output.",
        )

    non_production = not gate_ok or args.test
    if non_production:
        print(f"*** {NON_PRODUCTION_LABEL} ***")
        if not gate_ok:
            print("Gate closed; generating test candidate only (--test).")
        print()

    backend, backend_name, _is_mock = resolve_generation_backend(
        project=project,
        prefer_mock=True if args.force_mock else None,
    )
    # Prefer mock whenever mock is configured OR we are in test/non-production mode.
    if non_production:
        backend, backend_name, _is_mock = resolve_generation_backend(
            project=project, prefer_mock=True
        )

    prompt_payload = build_page_prompt(
        story_page, project=project, non_production=non_production
    )
    page_id = prompt_payload["page_id"]
    width = int(prompt_payload["dimensions"]["width"])
    height = int(prompt_payload["dimensions"]["height"])
    # Mock at full KDP size is slow-ish but fine; shrink mock for speed in test mode.
    if backend_name == "mock" and non_production:
        width, height = min(width, 1024), min(height, 1320)

    seed = args.seed if args.seed is not None else prompt_payload.get("seed")
    out_dir = project / "generations" / "pages" / page_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{page_id}_candidate.png"

    prompt_history.save_prompt(prompt_payload, page_id=page_id, root=project)

    print(f"Generating {page_id} via backend={backend_name} ...")
    result = backend.generate(
        prompt=prompt_payload["positive"],
        negative_prompt=prompt_payload["negative"],
        width=width,
        height=height,
        seed=seed,
        output_path=out_path,
        settings=prompt_payload.get("settings") or {},
    )
    if not result.success or not result.output_path:
        die(f"Generation failed: {result.error}")

    rel = str(Path(result.output_path).resolve().relative_to(project.resolve()))
    record = create_record(
        page_id=page_id,
        panel_id=None,
        backend=backend_name,
        model=result.model,
        seed=result.seed,
        positive_prompt=prompt_payload["positive"],
        negative_prompt=prompt_payload["negative"],
        width=width,
        height=height,
        output_path=rel,
        reference_assets=list(prompt_payload.get("reference_assets") or []),
        settings={
            **(prompt_payload.get("settings") or {}),
            "story_page": story_page,
            "non_production": non_production,
            "label": NON_PRODUCTION_LABEL if non_production else None,
            "story_context": prompt_payload.get("story_context"),
        },
        status=ArtStatus.GENERATED,
        root=project,
    )

    state = load_state(root=project)
    state.current_page_id = page_id
    save_state(state, root=project)

    print(f"Saved: {rel}")
    print(f"Record id: {record.id}")
    print(f"Seed: {result.seed}")
    print("Status: GENERATED (not auto-approved). Review in Streamlit.")
    if non_production:
        print(f"Labeled: {NON_PRODUCTION_LABEL}")


if __name__ == "__main__":
    main()
