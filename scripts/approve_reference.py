#!/usr/bin/env python3
"""Approve or lock a character reference slot (human-driven; never auto-called).

Examples:
  python scripts/approve_reference.py kaito front
  python scripts/approve_reference.py kaito front --lock
  python scripts/approve_reference.py kaito --all
  python scripts/approve_reference.py kaito --open-gate
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _cli_common import die, handle_cli_errors, load_character_continuity, root  # noqa: E402

from echo.characters.manager import CharacterManager  # noqa: E402
from echo.continuity.gates import (  # noqa: E402
    GateName,
    assert_no_mock_for_kaito_gate,
    set_gate,
)
from echo.core.errors import EchoError  # noqa: E402
from echo.core.schemas import ReferenceStatus  # noqa: E402


def _clear_kaito_gate_messages(*, project: Path) -> None:
    """Clear stale gate-open notes when an open-gate attempt is refused."""
    cont_path = project / "characters" / "kaito" / "continuity.json"
    if cont_path.is_file():
        cont = json.loads(cont_path.read_text(encoding="utf-8"))
        pg = cont.setdefault("production_gate", {})
        pg["KAITO_REFERENCE_APPROVED"] = False
        cont["production_gate"] = pg
        cont_path.write_text(json.dumps(cont, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    try:
        set_gate(GateName.KAITO_REFERENCE_APPROVED, False, root=project, note=None)
    except Exception:
        pass


@handle_cli_errors
def main() -> None:
    parser = argparse.ArgumentParser(description="Approve/lock character reference slots.")
    parser.add_argument("character_id", help="Character slug, e.g. kaito")
    parser.add_argument("slot", nargs="?", help="Slot name, e.g. front")
    parser.add_argument("--all", action="store_true", help="Approve all GENERATED slots")
    parser.add_argument("--lock", action="store_true", help="Set LOCKED instead of APPROVED")
    parser.add_argument(
        "--open-gate",
        action="store_true",
        help="Open KAITO_REFERENCE_APPROVED after all slots are APPROVED/LOCKED (kaito only)",
    )
    parser.add_argument(
        "--confirm-design",
        action="store_true",
        help="Required with --open-gate: you consciously approve the design",
    )
    args = parser.parse_args()

    project = root()
    slug = args.character_id.strip().lower()
    mgr = CharacterManager(root=project)
    status = ReferenceStatus.LOCKED if args.lock else ReferenceStatus.APPROVED

    if args.all:
        cont = load_character_continuity(slug, project=project)
        slots = cont.get("reference_slots") or {}
        for name, slot in slots.items():
            if not isinstance(slot, dict):
                continue
            current = str(slot.get("status") or "MISSING")
            if current in {"MISSING"}:
                die(f"Slot '{name}' is MISSING — generate first.")
            mgr.set_reference_slot_status(slug, name, status)
            print(f"{name} -> {status.value}")
    elif args.slot:
        mgr.set_reference_slot_status(slug, args.slot, status)
        print(f"{args.slot} -> {status.value}")
    elif not args.open_gate:
        die("Provide a slot name, --all, and/or --open-gate.")

    if args.open_gate:
        if slug != "kaito":
            die("--open-gate currently applies to the KAITO_REFERENCE_APPROVED production gate.")
        if not args.confirm_design:
            die(
                "Refusing to open gate without --confirm-design.",
                hint="Review all references, then re-run with --confirm-design.",
            )
        try:
            assert_no_mock_for_kaito_gate(root=project)
        except EchoError as exc:
            _clear_kaito_gate_messages(project=project)
            die(exc.message, hint=exc.hint)

        overall = mgr.overall_reference_status(slug)
        if overall not in (ReferenceStatus.APPROVED, ReferenceStatus.LOCKED):
            _clear_kaito_gate_messages(project=project)
            die(
                f"Cannot open gate — aggregate status is {overall.value}.",
                hint="Approve or lock every reference slot first.",
            )
        try:
            set_gate(
                GateName.KAITO_REFERENCE_APPROVED,
                True,
                root=project,
                note=f"Human CLI approval at {datetime.now(timezone.utc).isoformat()}",
            )
        except EchoError as exc:
            _clear_kaito_gate_messages(project=project)
            die(exc.message, hint=exc.hint)

        cont = load_character_continuity(slug, project=project)
        cont.setdefault("production_gate", {})["KAITO_REFERENCE_APPROVED"] = True
        path = project / "characters" / slug / "continuity.json"
        path.write_text(json.dumps(cont, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print("KAITO_REFERENCE_APPROVED = true")


if __name__ == "__main__":
    main()
