# Story workflow

## Source of truth

| File | Role |
|------|------|
| `story/manuscript.md` | Prose / narrative draft |
| `story/story-bible.json` | World, themes, cast overview |
| `story/page-plan.json` | Per–story-page production plan (50 pages for Volume 1) |

## Page plan fields (production pack)

Each page entry typically includes `story_page`, `chapter`, `scene`, `location`, `characters`, `action`, `emotion`, `camera_notes`, dialogue/captions, continuity hooks, and `art_status`.

The Python `PagePlan` / `PageEntry` models normalize this pack on load:

- missing `id` → `p{story_page}`
- `scene` → `title`, `action` → `summary`, `camera_notes` → `camera`
- unknown keys preserved under `extra`

Always pass `root=` in tests; production uses project root discovery.

## Recommended loop

1. **Plan** — confirm page purpose, cast, location, continuity_from_previous / continuity_for_next.
2. **Prompt** — `PromptBuilder.build(page_id)`.
3. **Generate** — mock first; real backends only after references are ready.
4. **Review** — continuity checklist; reject freely.
5. **Approve** — copy into `approved/` with a filename stem matching page id (`p1.png`, `p1_panel2.png`).
6. **Gate** — open pilot / PDF gates only after intentional human sign-off.
7. **Print** — preflight → `build_kdp_pdf` → manual KDP upload.

## Art status vs package ArtStatus

Page-plan `art_status` (e.g. `PLANNED`) is editorial. Package `ArtStatus` on `GenerationRecord` tracks a specific generation attempt. Do not confuse them.

## Pilot scope

Pages **1–5** are the pilot. Do not scale to the full 50-page generation campaign until the pilot gate is approved (see [PRODUCTION_PHASES.md](PRODUCTION_PHASES.md) and [reports/pilot-report.md](../reports/pilot-report.md)).
