#!/usr/bin/env python3
"""Print validation -> reports/print-validation.json + human-readable markdown."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _cli_common import handle_cli_errors, install_page_plan_compat, root  # noqa: E402

from echo.core.paths import reports_dir  # noqa: E402
from echo.qa.print_validator import validate_print_readiness  # noqa: E402


@handle_cli_errors
def main() -> None:
    install_page_plan_compat()
    project = root()
    report = validate_print_readiness(root=project)
    report["generated_at"] = datetime.now(timezone.utc).isoformat()

    out_dir = reports_dir(project)
    json_path = out_dir / "print-validation.json"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    md_lines = [
        "# Print Validation Report",
        "",
        f"Generated: {report['generated_at']}",
        f"Print ready: **{'YES' if report.get('print_ready') else 'NO'}**",
        f"PDF_READY: **{report.get('PDF_READY', 'NO')}**",
        "",
        "## Expected page pixels",
        f"- {report.get('expected_page_px')}",
        "",
        "## Dimension issues",
    ]
    issues = report.get("dimension_issues") or []
    if issues:
        md_lines.extend(f"- {i}" for i in issues)
    else:
        md_lines.append("- None")
    md_lines.extend(
        [
            "",
            "## Image QA summary",
            f"- Failed: {(report.get('image_qa') or {}).get('failed', 0)}",
            f"- Passed: {(report.get('image_qa') or {}).get('passed', 0)}",
            "",
            "## Preflight gates",
            f"- `{json.dumps((report.get('preflight') or {}).get('gates', {}), indent=2)}`",
            "",
        ]
    )
    md_path = out_dir / "print-validation.md"
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    print(f"Wrote {json_path.relative_to(project)}")
    print(f"Wrote {md_path.relative_to(project)}")
    print(f"print_ready={report.get('print_ready')} PDF_READY={report.get('PDF_READY')}")
    if not report.get("print_ready"):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
