#!/usr/bin/env python3
"""Approve or reject pilot pages 1–5 and optionally open PILOT_APPROVED.

Examples:
  python scripts/approve_pilot.py --approve-all
  python scripts/approve_pilot.py --open-gate --confirm-pilot
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _cli_common import (  # noqa: E402
    die,
    handle_cli_errors,
    load_story_plan,
    page_id_for,
    root,
    save_story_plan,
)

from echo.continuity.gates import GateName, set_gate  # noqa: E402
from echo.core.schemas import ArtStatus  # noqa: E402
from echo.generation.metadata import list_records_for_page  # noqa: E402
from echo.review.approval import ApprovalWorkflow  # noqa: E402

PILOT_PAGES = (1, 2, 3, 4, 5)


@handle_cli_errors
def main() -> None:
    parser = argparse.ArgumentParser(description="Approve pilot pages 1–5 / open PILOT gate.")
    parser.add_argument(
        "--approve-all",
        action="store_true",
        help="Approve latest GENERATED candidate for each pilot page into approved/",
    )
    parser.add_argument(
        "--open-gate",
        action="store_true",
        help="Set PILOT_APPROVED=true after review",
    )
    parser.add_argument(
        "--confirm-pilot",
        action="store_true",
        help="Required with --open-gate: conscious pilot sign-off",
    )
    args = parser.parse_args()

    project = root()
    if not args.approve_all and not args.open_gate:
        die("Provide --approve-all and/or --open-gate.")

    if args.approve_all:
        workflow = ApprovalWorkflow(root=project)
        plan = load_story_plan(project=project)
        for story_page in PILOT_PAGES:
            page_id = page_id_for(story_page)
            records = list_records_for_page(page_id, root=project)
            candidates = [
                r
                for r in records
                if r.status in (ArtStatus.GENERATED, ArtStatus.APPROVED)
            ]
            if not candidates:
                die(f"No generation record for {page_id}. Run generate_pilot.py first.")
            record = sorted(candidates, key=lambda r: r.created_at)[-1]
            if record.status != ArtStatus.APPROVED:
                approved = workflow.approve(record.id, dest_name=f"{page_id}.png")
                print(f"Approved {page_id} -> {approved.approved_path}")
            else:
                print(f"{page_id} already APPROVED")
            for page in plan.get("pages", []):
                if int(page.get("story_page", -1)) == story_page:
                    page["art_status"] = "APPROVED"
        save_story_plan(plan, project=project)

    if args.open_gate:
        if not args.confirm_pilot:
            die(
                "Refusing to open PILOT_APPROVED without --confirm-pilot.",
                hint="Review pages 1–5, then re-run with --confirm-pilot.",
            )
        missing = []
        for story_page in PILOT_PAGES:
            path = project / "approved" / f"{page_id_for(story_page)}.png"
            if not path.is_file():
                # allow alternate approved names
                matches = list((project / "approved").glob(f"{page_id_for(story_page)}*"))
                if not matches:
                    missing.append(page_id_for(story_page))
        if missing:
            die(
                f"Cannot open pilot gate — missing approved art: {', '.join(missing)}",
                hint="Run with --approve-all first, or approve in Streamlit.",
            )
        set_gate(
            GateName.PILOT_APPROVED,
            True,
            root=project,
            note=f"Human pilot approval at {datetime.now(timezone.utc).isoformat()}",
        )
        gates_path = project / "config" / "production_gates.json"
        if gates_path.is_file():
            data = json.loads(gates_path.read_text(encoding="utf-8"))
            data["PILOT_APPROVED"] = True
            gates_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        print("PILOT_APPROVED = true")
        print("Bulk generation is now permitted by gate policy (still uses configured backend).")


if __name__ == "__main__":
    main()
