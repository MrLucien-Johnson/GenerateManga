"""Validate print readiness for KDP output."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from echo.core.config import get_config
from echo.core.paths import approved_dir, project_root
from echo.publishing.preflight import run_preflight
from echo.qa.image_qa import check_images


def validate_print_readiness(*, root: Path | None = None) -> dict[str, Any]:
    """Combine preflight gates with per-image dimension/DPI-oriented checks."""
    root = root or project_root()
    try:
        kdp = get_config("kdp", root=root)
    except Exception:
        kdp = {}

    dpi = int(kdp.get("dpi", 300))
    bleed = float(kdp.get("bleed_in", 0.125))
    trim_w = float(kdp.get("trim_width_in", 8.5))
    trim_h = float(kdp.get("trim_height_in", 11.0))
    expect_w = int(round((trim_w + 2 * bleed) * dpi))
    expect_h = int(round((trim_h + 2 * bleed) * dpi))
    expect_aspect = expect_w / expect_h

    approved = approved_dir(root)
    files = sorted(
        p
        for p in approved.glob("**/*")
        if p.is_file() and p.suffix.lower() in {".png", ".jpg", ".jpeg"}
    )

    # Approved art may be panel-sized; warn on dimension mismatch rather than hard-fail
    # unless files look like full pages (near expected size).
    qa = check_images(files, detect_duplicates=True, allow_alpha=False)
    preflight = run_preflight(root=root, write_report=False)

    dimension_issues: list[str] = []
    for rep in qa["reports"]:
        w, h = rep.get("width"), rep.get("height")
        if not w or not h:
            continue
        # Soft check: if within 5% of full page, enforce exact-ish size.
        if abs(w - expect_w) / expect_w < 0.05 or abs(h - expect_h) / expect_h < 0.05:
            if w != expect_w or h != expect_h:
                dimension_issues.append(
                    f"{rep['path']}: {w}x{h} close to page size but != {expect_w}x{expect_h}"
                )

    ready = bool(preflight.get("pdf_ready")) and qa["failed"] == 0 and not dimension_issues
    return {
        "print_ready": ready,
        "PDF_READY": "YES" if preflight.get("pdf_ready") else "NO",
        "expected_page_px": {"width": expect_w, "height": expect_h, "aspect": expect_aspect},
        "image_qa": qa,
        "dimension_issues": dimension_issues,
        "preflight": preflight,
    }
