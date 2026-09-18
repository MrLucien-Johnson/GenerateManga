#!/usr/bin/env python3
"""Run image QA + continuity/schema checks; write reports/."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _cli_common import (  # noqa: E402
    handle_cli_errors,
    install_page_plan_compat,
    load_story_plan,
    root,
)

from echo.continuity.checklist import ContinuityChecklist  # noqa: E402
from echo.core.paths import reports_dir  # noqa: E402
from echo.core.state import load_state  # noqa: E402
from echo.qa.image_qa import check_images  # noqa: E402


@handle_cli_errors
def main() -> None:
    install_page_plan_compat()
    project = root()
    out_dir = reports_dir(project)

    image_paths: list[Path] = []
    for folder in ("approved", "generations", "characters"):
        base = project / folder
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
                image_paths.append(path)

    qa = check_images(image_paths, detect_duplicates=True, allow_alpha=True)

    # Schema / continuity soft checks against editorial page plan.
    plan = load_story_plan(project=project)
    pages = plan.get("pages") or []
    schema_errors: list[str] = []
    schema_warnings: list[str] = []
    required_fields = ("story_page", "action", "emotion", "location", "characters")
    for page in pages:
        sp = page.get("story_page")
        for field in required_fields:
            if field not in page or page[field] in (None, "", []):
                schema_errors.append(f"page {sp}: missing or empty '{field}'")
        if not isinstance(page.get("dialogue", []), list):
            schema_errors.append(f"page {sp}: dialogue must be a list")
        if page.get("art_status") == "APPROVED" and not list(
            (project / "approved").glob(f"*page_{int(sp):02d}*")
        ):
            schema_warnings.append(
                f"page {sp}: art_status APPROVED but no matching file under approved/"
            )

    checklist = ContinuityChecklist()
    state = load_state(root=project)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ok": bool(qa.get("ok")) and not schema_errors,
        "image_qa": qa,
        "schema": {
            "page_count": len(pages),
            "errors": schema_errors,
            "warnings": schema_warnings,
        },
        "continuity_checklist_template": checklist.summary(),
        "gates": state.gates.model_dump(mode="json"),
    }

    json_path = out_dir / "validation.json"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    md_lines = [
        "# Validation Report",
        "",
        f"Generated: {report['generated_at']}",
        f"Overall OK: **{'YES' if report['ok'] else 'NO'}**",
        "",
        "## Image QA",
        f"- Checked: {qa.get('count', 0)}",
        f"- Passed: {qa.get('passed', 0)}",
        f"- Failed: {qa.get('failed', 0)}",
        f"- Duplicate groups: {len(qa.get('duplicates') or [])}",
        "",
        "## Schema",
        f"- Pages: {len(pages)}",
        f"- Errors: {len(schema_errors)}",
        f"- Warnings: {len(schema_warnings)}",
        "",
    ]
    if schema_errors:
        md_lines.append("### Schema errors")
        md_lines.extend(f"- {e}" for e in schema_errors[:50])
        md_lines.append("")
    md_path = out_dir / "validation.md"
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    print(f"Wrote {json_path.relative_to(project)}")
    print(f"Wrote {md_path.relative_to(project)}")
    print(f"OK={report['ok']} images_failed={qa.get('failed')} schema_errors={len(schema_errors)}")
    if not report["ok"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
