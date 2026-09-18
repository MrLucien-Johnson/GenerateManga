"""Preflight report for KDP print readiness."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from echo.continuity.gates import evaluate_pdf_ready
from echo.core.config import get_config
from echo.core.paths import approved_dir, ensure_dir, project_root, reports_dir
from echo.core.state import load_state
from echo.story.page_plan import load_page_plan
from echo.story.physical_pages import PhysicalPageMapper


def run_preflight(*, root: Path | None = None, write_report: bool = True) -> dict[str, Any]:
    """Produce a preflight report with counts and PDF READY YES/NO."""
    root = root or project_root()
    state = load_state(root=root)
    plan = load_page_plan(root=root)
    try:
        kdp = get_config("kdp", root=root)
    except Exception:
        kdp = {}

    approved = approved_dir(root)
    approved_files = sorted(
        p
        for p in approved.glob("**/*")
        if p.is_file() and p.suffix.lower() in {".png", ".jpg", ".jpeg"}
    )

    mapper = PhysicalPageMapper(plan, root=root)
    pdf_report = evaluate_pdf_ready(
        root=root,
        required_page_ids=[p.id for p in plan.pages] or None,
        min_approved=max(1, len(plan.pages) or 1),
    )

    ready = bool(pdf_report.get("pdf_ready"))
    report: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "PDF_READY": "YES" if ready else "NO",
        "pdf_ready": ready,
        "counts": {
            "story_pages": len(plan.pages),
            "physical_pages": mapper.total_physical_pages(),
            "approved_art": len(approved_files),
            "front_matter_pages": mapper.front_matter_pages,
            "blank_reverse_pages": mapper.blank_reverse_pages,
        },
        "gates": state.gates.model_dump(),
        "kdp": {
            "trim": f"{kdp.get('trim_width_in', 8.5)}x{kdp.get('trim_height_in', 11)}",
            "dpi": kdp.get("dpi", 300),
            "bleed_in": kdp.get("bleed_in", 0.125),
            "blank_reverse_pages": kdp.get("blank_reverse_pages", True),
            "output_pdf": kdp.get("output_pdf"),
        },
        "approved_files": [str(p.relative_to(root)) for p in approved_files],
        "missing_pages": pdf_report.get("missing_pages", []),
        "details": pdf_report,
    }

    if write_report:
        out = ensure_dir(reports_dir(root)) / "preflight.json"
        out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        report["report_path"] = str(out)

    return report
