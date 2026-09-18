# Production phases

Phases mark production maturity. **Engineering complete ≠ book production complete.**

| Phase | Name | Brief |
|-------|------|--------|
| **0** | Scaffold | Repo layout, package install, configs, mock backend, tests green |
| **1** | Story pack | Manuscript, story bible, 50-page plan present |
| **2** | Character bibles | Kaito (+ supporting cast) bibles and continuity packs |
| **3** | World packs | Locations + key objects (inkwell) documented |
| **4** | Reference campaign | Generate → review → approve/lock Kaito reference sheet |
| **5** | Gate: references | `KAITO_REFERENCE_APPROVED` open |
| **6** | Prompt freeze | Style + page prompts stable for pilot |
| **7** | Pilot generate | Story pages **1–5** candidates via chosen backend |
| **8** | Pilot gate | Human approval of pages 1–5; `PILOT_APPROVED` open — see [pilot-report](../reports/pilot-report.md) |
| **9** | Volume generate | Remaining pages with continuity checklist |
| **10** | Print assembly | Approved art → preflight → 8.5×11 PDF with blank reverses |
| **11** | Release prep | Manual KDP upload / printer handoff — **never automated** |

## Pilot gate (phase 8)

Do not scale generation until:

- Kaito references approved/locked
- Pages 1–5 art approved into `approved/`
- Continuity checklist complete for the pilot
- Pilot report filled (not the empty template)

## Current snapshot

- Phases **0–3**: in progress / available in-repo (engineering + story content).
- Phase **4+**: pending real reference and page art approval.
- Pilot report: **template only** — pilot not yet run.
