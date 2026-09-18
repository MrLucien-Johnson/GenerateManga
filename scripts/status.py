#!/usr/bin/env python3
"""Print a preflight / production status summary."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _cli_common import (  # noqa: E402
    count_generation_stats,
    handle_cli_errors,
    install_page_plan_compat,
    progress_stage_status,
    root,
)

from echo.core.config import mock_generation_enabled  # noqa: E402
from echo.core.state import load_state  # noqa: E402
from echo.publishing.preflight import run_preflight  # noqa: E402


@handle_cli_errors
def main() -> None:
    install_page_plan_compat()
    project = root()
    state = load_state(root=project)
    stats = count_generation_stats(project=project)
    stages = progress_stage_status(project=project)
    preflight = run_preflight(root=project, write_report=True)

    print("Echo of the Inkwell — Status")
    print("=" * 40)
    print(f"PDF_READY: {preflight.get('PDF_READY')}")
    print(
        "Gates: "
        f"KAITO_REFERENCE_APPROVED={state.gates.kaito_reference_approved}  "
        f"PILOT_APPROVED={state.gates.pilot_approved}  "
        f"PDF_READY={state.gates.pdf_ready}"
    )
    print(
        f"Pages: approved {stats['approved']}/{stats['target_pages']}  "
        f"generated_records={stats['generated']}  "
        f"remaining={stats['remaining']}  "
        f"rejected={stats['rejected']}"
    )
    print(f"Current page: {state.current_page_id or '(none)'}")
    print(f"Mock generation enabled: {mock_generation_enabled(project)}")
    print("\nPipeline stages:")
    for name, status in stages.items():
        mark = {"complete": "[x]", "in_progress": "[~]", "not_started": "[ ]"}.get(status, "[?]")
        print(f"  {mark} {name}: {status}")

    print(f"\nPreflight report: reports/preflight.json")
    print(json.dumps(preflight.get("counts", {}), indent=2))


if __name__ == "__main__":
    main()
