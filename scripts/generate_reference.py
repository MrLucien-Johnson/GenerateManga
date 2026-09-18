#!/usr/bin/env python3
"""Generate character reference candidates for MISSING slots only.

Does NOT auto-approve. Updates continuity statuses to GENERATED only.
Labels NON-PRODUCTION TEST clearly when the production gate is not met.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _cli_common import (  # noqa: E402
    NON_PRODUCTION_LABEL,
    build_reference_prompt,
    die,
    gate_open,
    handle_cli_errors,
    load_character_continuity,
    missing_reference_slots,
    resolve_generation_backend,
    root,
    save_character_continuity,
)

from echo.characters.manager import CharacterManager  # noqa: E402
from echo.core.schemas import ArtStatus, ReferenceStatus  # noqa: E402
from echo.generation.metadata import create_record  # noqa: E402


@handle_cli_errors
def main() -> None:
    parser = argparse.ArgumentParser(description="Generate missing character reference slots.")
    parser.add_argument("character_id", help="Character slug, e.g. kaito")
    parser.add_argument(
        "--force-mock",
        action="store_true",
        help="Force mock backend regardless of config",
    )
    args = parser.parse_args()

    project = root()
    slug = args.character_id.strip().lower()
    char_dir = project / "characters" / slug
    if not char_dir.is_dir():
        die(
            f"Character '{slug}' not found.",
            hint=f"Expected directory at characters/{slug}/",
        )

    continuity = load_character_continuity(slug, project=project)
    missing = missing_reference_slots(continuity)
    if not missing:
        print(f"No MISSING reference slots for '{slug}'. Nothing to generate.")
        return

    gate_ok = gate_open("KAITO_REFERENCE_APPROVED", project=project)
    non_production = not gate_ok
    if non_production:
        print(f"*** {NON_PRODUCTION_LABEL} ***")
        print("KAITO_REFERENCE_APPROVED is false — outputs are test candidates only.")
        print("This script will NOT auto-approve any references.\n")

    backend, backend_name, is_mock = resolve_generation_backend(
        project=project,
        prefer_mock=True if args.force_mock else None,
    )
    # Prefer mock when env/config says so; also default to mock for refs when
    # production gate is closed (safer for early pipeline).
    if non_production and not is_mock:
        backend, backend_name, is_mock = resolve_generation_backend(
            project=project, prefer_mock=True
        )

    mgr = CharacterManager(root=project)
    ref_dir = mgr.references_dir(slug)
    ref_dir.mkdir(parents=True, exist_ok=True)

    # Reference sheets: modest square for candidates (mock is cheap at any size).
    width, height = (1024, 1024)
    generated: list[str] = []

    for slot_name, slot in missing.items():
        filename = str(slot.get("filename") or f"{slug}_{slot_name}.png")
        out_path = ref_dir / filename
        prompt = build_reference_prompt(
            slug, slot_name, project=project, non_production=non_production
        )
        print(f"Generating slot '{slot_name}' -> {out_path.relative_to(project)} ...")
        result = backend.generate(
            prompt=prompt,
            negative_prompt="photorealistic, color fill, watermark spam, extra limbs",
            width=width,
            height=height,
            seed=None,
            output_path=out_path,
            settings={"slot": slot_name, "character": slug, "non_production": non_production},
        )
        if not result.success or not result.output_path:
            die(f"Generation failed for slot '{slot_name}': {result.error}")

        rel_out = str(Path(result.output_path).resolve().relative_to(project.resolve()))
        record = create_record(
            page_id=f"ref_{slug}_{slot_name}",
            panel_id=slot_name,
            backend=backend_name,
            model=result.model,
            seed=result.seed,
            positive_prompt=prompt,
            negative_prompt="photorealistic, color fill, watermark spam, extra limbs",
            width=width,
            height=height,
            output_path=rel_out,
            reference_assets=[],
            settings={
                "kind": "character_reference",
                "slot": slot_name,
                "character": slug,
                "non_production": non_production,
                "label": NON_PRODUCTION_LABEL if non_production else None,
            },
            status=ArtStatus.GENERATED,
            root=project,
        )

        # Continuity: GENERATED only — never APPROVED here.
        slot["status"] = ReferenceStatus.GENERATED.value
        slot["path"] = rel_out
        slot["approved_at"] = None
        slot["generated_at"] = datetime.now(timezone.utc).isoformat()
        slot["generation_record_id"] = record.id
        continuity["reference_slots"][slot_name] = slot

        mgr.set_reference_status(slug, filename, ReferenceStatus.GENERATED)
        generated.append(f"{slot_name} ({filename}) record={record.id} seed={result.seed}")

    save_character_continuity(slug, continuity, project=project)

    print(f"\nGenerated {len(generated)} reference candidate(s) for '{slug}':")
    for line in generated:
        print(f"  - {line}")
    print("\nStatus set to GENERATED only. Review and approve manually (do not skip).")
    if non_production:
        print(f"Remember: all of the above are {NON_PRODUCTION_LABEL} until the gate opens.")


if __name__ == "__main__":
    main()
