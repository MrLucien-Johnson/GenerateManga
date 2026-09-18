#!/usr/bin/env python3
"""Generate pilot pages 1–5 after KAITO_REFERENCE_APPROVED.

Writes reports/pilot-report.md template afterward.
Does NOT auto-approve the pilot or set PILOT_APPROVED.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _cli_common import (  # noqa: E402
    NON_PRODUCTION_LABEL,
    build_page_prompt,
    die,
    gate_open,
    handle_cli_errors,
    install_page_plan_compat,
    resolve_generation_backend,
    root,
)

from echo.core.paths import reports_dir  # noqa: E402
from echo.core.schemas import ArtStatus  # noqa: E402
from echo.generation.metadata import create_record  # noqa: E402
from echo.prompts import history as prompt_history  # noqa: E402

PILOT_PAGES = (1, 2, 3, 4, 5)


@handle_cli_errors
def main() -> None:
    parser = argparse.ArgumentParser(description="Generate pilot pages 1–5.")
    parser.add_argument(
        "--test",
        action="store_true",
        help="Allow pilot generation when KAITO_REFERENCE_APPROVED is false (NON-PRODUCTION)",
    )
    args = parser.parse_args()

    install_page_plan_compat()
    project = root()
    gate_ok = gate_open("KAITO_REFERENCE_APPROVED", project=project)
    if not gate_ok and not args.test:
        die(
            "KAITO_REFERENCE_APPROVED is false — refusing pilot generation.",
            hint="Approve Kaito references first, or pass --test for NON-PRODUCTION TEST.",
        )

    non_production = not gate_ok or args.test
    if non_production:
        print(f"*** {NON_PRODUCTION_LABEL} ***")
        print("Pilot outputs are test candidates only.\n")

    backend, backend_name, _ = resolve_generation_backend(
        project=project, prefer_mock=True if non_production else None
    )

    results: list[dict] = []
    for story_page in PILOT_PAGES:
        payload = build_page_prompt(
            story_page, project=project, non_production=non_production
        )
        page_id = payload["page_id"]
        width = int(payload["dimensions"]["width"])
        height = int(payload["dimensions"]["height"])
        if backend_name == "mock":
            width, height = min(width, 1024), min(height, 1320)

        out_dir = project / "generations" / "pages" / page_id
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{page_id}_pilot.png"

        prompt_history.save_prompt(payload, page_id=page_id, root=project)
        print(f"Pilot page {story_page} ({page_id}) via {backend_name} ...")
        result = backend.generate(
            prompt=payload["positive"],
            negative_prompt=payload["negative"],
            width=width,
            height=height,
            seed=payload.get("seed"),
            output_path=out_path,
            settings=payload.get("settings") or {},
        )
        if not result.success or not result.output_path:
            die(f"Pilot generation failed on page {story_page}: {result.error}")

        rel = str(Path(result.output_path).resolve().relative_to(project.resolve()))
        record = create_record(
            page_id=page_id,
            backend=backend_name,
            model=result.model,
            seed=result.seed,
            positive_prompt=payload["positive"],
            negative_prompt=payload["negative"],
            width=width,
            height=height,
            output_path=rel,
            settings={
                "pilot": True,
                "story_page": story_page,
                "non_production": non_production,
                "label": NON_PRODUCTION_LABEL if non_production else None,
            },
            status=ArtStatus.GENERATED,
            root=project,
        )
        results.append(
            {
                "story_page": story_page,
                "page_id": page_id,
                "record_id": record.id,
                "seed": result.seed,
                "path": rel,
            }
        )

    report_path = reports_dir(project) / "pilot-report.md"
    lines = [
        "# Pilot Report — Echo of the Inkwell",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        f"Non-production: {non_production}",
        f"Backend: {backend_name}",
        "",
        "## Status",
        "",
        "- PILOT_APPROVED: **false** (not auto-set — human review required)",
        "- KAITO_REFERENCE_APPROVED at run time: "
        f"**{gate_ok}**",
        "",
        "## Pages 1–5",
        "",
        "| Story page | Page id | Record id | Seed | Path | Review |",
        "|------------|---------|-----------|------|------|--------|",
    ]
    for row in results:
        lines.append(
            f"| {row['story_page']} | {row['page_id']} | `{row['record_id']}` | "
            f"{row['seed']} | `{row['path']}` | PENDING |"
        )
    lines.extend(
        [
            "",
            "## Review checklist (human)",
            "",
            "- [ ] Continuity vs Kaito locked references",
            "- [ ] Costume / jacket consistency",
            "- [ ] No baked-in dialogue text",
            "- [ ] Panel readability for coloring-book print",
            "- [ ] Approve or reject each page in Streamlit Review Studio",
            "",
            "## After approval",
            "",
            "Only after human sign-off, set `PILOT_APPROVED=true` via gates "
            "(do not trust this script to flip the gate).",
            "",
        ]
    )
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"\nWrote {report_path.relative_to(project)}")
    print("Pilot candidates are GENERATED only — PILOT_APPROVED remains false.")
    print("Review in Streamlit before promoting the pilot gate.")


if __name__ == "__main__":
    main()
