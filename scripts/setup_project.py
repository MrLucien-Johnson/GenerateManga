#!/usr/bin/env python3
"""Verify project directories, create missing .gitkeeps, init state, print next steps."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _cli_common import handle_cli_errors, root  # noqa: E402

from echo.core.schemas import ProductionGates, ProjectState  # noqa: E402
from echo.core.state import load_state, save_state  # noqa: E402

REQUIRED_DIRS = [
    "config",
    "story",
    "characters/kaito/references",
    "locations/drawing_space/references",
    "locations/kaito_bedroom/references",
    "locations/mysterious_shop/references",
    "locations/neighbourhood_street/references",
    "locations/school/references",
    "objects/inkwell/references",
    "generations",
    "approved",
    "rejected",
    "prompts",
    "pages",
    "reports",
    "logs",
    "fonts",
    "assets",
    "kdp/interior",
    "kdp/previews",
    "kdp/final",
    "colab",
    "scripts",
]


@handle_cli_errors
def main() -> None:
    project = root()
    print(f"Echo of the Inkwell — project root: {project}")
    created_dirs: list[str] = []
    created_keeps: list[str] = []

    for rel in REQUIRED_DIRS:
        path = project / rel
        if not path.is_dir():
            path.mkdir(parents=True, exist_ok=True)
            created_dirs.append(rel)
        keep = path / ".gitkeep"
        if not keep.exists() and not any(path.iterdir()):
            keep.touch()
            created_keeps.append(str(keep.relative_to(project)))
        elif not keep.exists() and rel.endswith("/references"):
            keep.touch()
            created_keeps.append(str(keep.relative_to(project)))

    # Hydrate KAITO gate from committed continuity.json (state.json is gitignored).
    kaito_gate = False
    continuity_path = project / "characters" / "kaito" / "continuity.json"
    if continuity_path.is_file():
        try:
            cont = json.loads(continuity_path.read_text(encoding="utf-8"))
            kaito_gate = bool((cont.get("production_gate") or {}).get("KAITO_REFERENCE_APPROVED"))
        except json.JSONDecodeError:
            kaito_gate = False

    state_path = project / "config" / "state.json"
    if not state_path.is_file():
        state = ProjectState(
            gates=ProductionGates(
                kaito_reference_approved=kaito_gate,
                pilot_approved=False,
                pdf_ready=False,
                notes={
                    "KAITO_REFERENCE_APPROVED": (
                        "Hydrated from continuity.json" if kaito_gate else "Initial — false"
                    ),
                    "PILOT_APPROVED": "Initial — false",
                },
            )
        )
        save_state(state, root=project)
        print(f"Created {state_path.relative_to(project)}")
    else:
        state = load_state(root=project)
        if kaito_gate and not state.gates.kaito_reference_approved:
            state.gates.kaito_reference_approved = True
            state.gates.notes["KAITO_REFERENCE_APPROVED"] = "Synced from continuity.json"
            save_state(state, root=project)
        print(
            "State gates: "
            f"KAITO_REFERENCE_APPROVED={state.gates.kaito_reference_approved}, "
            f"PILOT_APPROVED={state.gates.pilot_approved}, "
            f"PDF_READY={state.gates.pdf_ready}"
        )

    gates_path = project / "config" / "production_gates.json"
    if not gates_path.is_file():
        gates_path.write_text(
            json.dumps(
                {
                    "KAITO_REFERENCE_APPROVED": False,
                    "PILOT_APPROVED": False,
                    "PDF_READY": False,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        print(f"Created {gates_path.relative_to(project)}")

    if created_dirs:
        print(f"Created directories: {', '.join(created_dirs)}")
    else:
        print("All required directories present.")
    if created_keeps:
        print(f"Created .gitkeeps: {', '.join(created_keeps)}")

    print("\nNext steps:")
    print("  1. python scripts/generate_reference.py kaito")
    print("     (use ECHO_MOCK_GENERATION=1 for test placeholders)")
    print("  2. Review refs in Streamlit — do NOT auto-approve")
    print("  3. After KAITO_REFERENCE_APPROVED: python scripts/generate_pilot.py")
    print("  4. streamlit run app.py")
    print("  5. python scripts/status.py")


if __name__ == "__main__":
    main()
