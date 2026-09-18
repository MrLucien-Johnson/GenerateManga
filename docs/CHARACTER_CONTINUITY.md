# Character continuity

Continuity is the difference between a coherent volume and a pile of unrelated drawings.

## Character folders

```
characters/<slug>/
  character-bible.json   # or bible.json / bible.md
  continuity.json        # reference slots + notes
  references/            # approved/locked line-art PNGs
  references/status.json # optional per-file ReferenceStatus map
```

`CharacterManager` is generic — no hard-coded appearance assumptions in code. Project-specific gates (e.g. Kaito) only check slug `kaito` status.

## ReferenceStatus lifecycle

`MISSING` → `GENERATED` → `APPROVED` → `LOCKED`

- **MISSING** — slot listed but no usable approved asset
- **GENERATED** — candidate on disk, not signed off
- **APPROVED** — human accepted for production use
- **LOCKED** — frozen for the volume; do not casually replace

Aggregate status (`overall_reference_status`):

- all `LOCKED` → `LOCKED`
- all `APPROVED` or `LOCKED` → `APPROVED`
- any `MISSING` → `MISSING`
- else `GENERATED`

Production `continuity.json` may declare `reference_slots` with filenames and statuses even before files exist. The manager merges those slots with on-disk images.

## Gate: KAITO_REFERENCE_APPROVED

Pilot character references must reach `APPROVED` or `LOCKED` before treating later production stages as open. Set explicitly via `echo.continuity.gates.set_gate`, or let `evaluate_pdf_ready` auto-detect when Kaito references are approved.

Until this gate is open: plan and mock freely; do not claim book-production readiness.

## Continuity checklist

`echo.continuity.checklist.ContinuityChecklist` covers identity, costume, props (inkwell), location, lighting, panel flow, no baked text, bleed/safe margins, physical page numbers, and blank reverses. Use it during human review of candidates.

## Prompt continuity block

`PromptBuilder` appends locked-reference instructions and each character’s reference status so backends that accept reference images can be pointed at `characters/<slug>/references/`.
