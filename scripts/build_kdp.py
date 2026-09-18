#!/usr/bin/env python3
"""Build KDP PDF — --preview vs --production.

Production refuses unless gates pass. Preview is never labelled production-ready.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _cli_common import (  # noqa: E402
    die,
    handle_cli_errors,
    install_page_plan_compat,
    root,
)

from echo.core.errors import GateBlocked  # noqa: E402
from echo.core.paths import ensure_dir  # noqa: E402
from echo.publishing.kdp import build_kdp_pdf  # noqa: E402


@handle_cli_errors
def main() -> None:
    parser = argparse.ArgumentParser(description="Build KDP interior PDF.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preview", action="store_true", help="Preview build (no production label)")
    mode.add_argument("--production", action="store_true", help="Production build (gates required)")
    args = parser.parse_args()

    install_page_plan_compat()
    project = root()

    if args.production:
        try:
            out = build_kdp_pdf(root=project, require_gates=True)
        except GateBlocked as exc:
            die(
                exc.message,
                hint="Use --preview for a non-production draft, or complete approvals first.",
            )
        print(f"Production PDF written: {out}")
        print("Gates passed. Suitable for KDP upload only if print validation also passes.")
        return

    # Preview: never require gates; write under kdp/previews with clear banner file.
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    preview_dir = ensure_dir(project / "kdp" / "previews")
    out_path = preview_dir / f"interior_preview_{stamp}.pdf"
    try:
        out = build_kdp_pdf(root=project, output_path=out_path, require_gates=False)
    except Exception as exc:
        die(
            f"Preview build failed: {exc}",
            hint="Approve at least one image into approved/ first.",
        )

    notice = preview_dir / f"interior_preview_{stamp}_NOTICE.txt"
    notice.write_text(
        "NOT PRODUCTION-READY\n"
        "This preview PDF was built with --preview.\n"
        "Do not upload to KDP as a final interior.\n"
        f"Generated: {stamp}\n",
        encoding="utf-8",
    )
    print(f"Preview PDF written: {out}")
    print(f"Notice: {notice.relative_to(project)}")
    print("NOT PRODUCTION-READY — preview only.")


if __name__ == "__main__":
    main()
