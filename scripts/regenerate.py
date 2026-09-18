#!/usr/bin/env python3
"""Regenerate a page candidate from an existing generation record or story page."""

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
from echo.generation.metadata import create_record, list_records_for_page, load_record  # noqa: E402
from echo.prompts import history as prompt_history  # noqa: E402


@handle_cli_errors
def main() -> None:
    parser = argparse.ArgumentParser(description="Regenerate a page art candidate.")
    parser.add_argument(
        "target",
        help="Story page number (e.g. 3) or generation record id",
    )
    parser.add_argument("--test", action="store_true", help="Allow when gate closed")
    parser.add_argument("--seed", type=int, default=None, help="New seed (default: vary)")
    parser.add_argument("--extra-prompt", default="", help="Append to positive prompt")
    args = parser.parse_args()

    install_page_plan_compat()
    project = root()

    parent_id: str | None = None
    story_page: int | None = None
    page_id: str | None = None
    base_positive = ""
    base_negative = ""
    width, height = 1024, 1320

    target = args.target.strip()
    if target.isdigit():
        story_page = int(target)
        page_id = page_id_for(story_page)
        records = list_records_for_page(page_id, root=project)
        if records:
            parent = sorted(records, key=lambda r: r.created_at)[-1]
            parent_id = parent.id
            base_positive = parent.positive_prompt
            base_negative = parent.negative_prompt
            width, height = parent.width, parent.height
    else:
        parent = load_record(target, root=project)
        parent_id = parent.id
        page_id = parent.page_id
        base_positive = parent.positive_prompt
        base_negative = parent.negative_prompt
        width, height = parent.width, parent.height
        # Extract story page from page_id page_NN
        if page_id.startswith("page_"):
            try:
                story_page = int(page_id.split("_", 1)[1])
            except ValueError:
                story_page = None

    if story_page is None or page_id is None:
        die("Could not resolve story page / page_id from target.")

    gate_ok = gate_open("KAITO_REFERENCE_APPROVED", project=project)
    if not gate_ok and not args.test:
        die(
            "KAITO_REFERENCE_APPROVED is false — refusing regenerate.",
            hint="Pass --test for NON-PRODUCTION TEST regeneration.",
        )
    non_production = not gate_ok or args.test

    if non_production:
        print(f"*** {NON_PRODUCTION_LABEL} ***\n")

    if not base_positive:
        payload = build_page_prompt(
            story_page,
            project=project,
            extra_positive=args.extra_prompt,
            non_production=non_production,
        )
        base_positive = payload["positive"]
        base_negative = payload["negative"]
        width = int(payload["dimensions"]["width"])
        height = int(payload["dimensions"]["height"])
    elif args.extra_prompt:
        base_positive = f"{base_positive}\n\n{args.extra_prompt.strip()}"

    backend, backend_name, _ = resolve_generation_backend(
        project=project, prefer_mock=True if non_production else None
    )
    if backend_name == "mock" and non_production:
        width, height = min(width, 1024), min(height, 1320)

    out_dir = project / "generations" / "pages" / page_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{page_id}_regen.png"

    print(f"Regenerating {page_id} (parent={parent_id}) via {backend_name} ...")
    result = backend.regenerate(
        prompt=base_positive,
        negative_prompt=base_negative,
        width=width,
        height=height,
        seed=args.seed,
        output_path=out_path,
        settings={"parent_id": parent_id, "non_production": non_production},
    )
    if not result.success or not result.output_path:
        die(f"Regeneration failed: {result.error}")

    rel = str(Path(result.output_path).resolve().relative_to(project.resolve()))
    prompt_history.save_prompt(
        {
            "page_id": page_id,
            "positive": base_positive,
            "negative": base_negative,
            "parent_id": parent_id,
            "seed": result.seed,
        },
        page_id=page_id,
        root=project,
    )
    record = create_record(
        page_id=page_id,
        backend=backend_name,
        model=result.model,
        seed=result.seed,
        positive_prompt=base_positive,
        negative_prompt=base_negative,
        width=width,
        height=height,
        output_path=rel,
        settings={
            "story_page": story_page,
            "non_production": non_production,
            "label": NON_PRODUCTION_LABEL if non_production else None,
        },
        status=ArtStatus.GENERATED,
        parent_id=parent_id,
        root=project,
    )
    print(f"Saved: {rel}")
    print(f"New record: {record.id} seed={result.seed}")


if __name__ == "__main__":
    main()
