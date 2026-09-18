# Pilot Report — Echo of the Inkwell

Generated: 2026-09-18T12:29:54.434953+00:00
Non-production: False
Backend: mock

## Status

- PILOT_APPROVED: **false** (not auto-set — human review required)
- KAITO_REFERENCE_APPROVED at run time: **True**

## Pages 1–5

| Story page | Page id | Record id | Seed | Path | Review |
|------------|---------|-----------|------|------|--------|
| 1 | page_01 | `ea461e253e63463a9ab239cfc390c389` | 3843420908 | `generations/pages/page_01/page_01_pilot.png` | PENDING |
| 2 | page_02 | `ceaff36fa55f45169af1e04714989bce` | 201763758 | `generations/pages/page_02/page_02_pilot.png` | PENDING |
| 3 | page_03 | `877cfad9e0a84a6faea8bedb36426661` | 1514998782 | `generations/pages/page_03/page_03_pilot.png` | PENDING |
| 4 | page_04 | `5e1e9e4848824c0f93fa9617558cd8ef` | 1379955665 | `generations/pages/page_04/page_04_pilot.png` | PENDING |
| 5 | page_05 | `df7b310c2b4442c6a404cf2665b56963` | 569187836 | `generations/pages/page_05/page_05_pilot.png` | PENDING |

## Review checklist (human)

- [ ] Continuity vs Kaito locked references
- [ ] Costume / jacket consistency
- [ ] No baked-in dialogue text
- [ ] Panel readability for coloring-book print
- [ ] Approve or reject each page in Streamlit Review Studio

## After approval

Only after human sign-off, set `PILOT_APPROVED=true` via gates (do not trust this script to flip the gate).

## Continuity / quality observations (mock backend)

- **Character consistency:** N/A — mock outputs are geometric placeholders, not Kaito likenesses.
- **Line-art quality:** Placeholder only (circle/triangle/diagonal style marks).
- **Coloring suitability:** White background with sparse black lines — structurally OK for pipeline tests; not artistic content.
- **Backend reliability:** Mock succeeded for all 5 pages; deterministic seeds recorded.
- **Generation times:** Sub-second each (Pillow).
- **Failed generations:** None.
- **Prompt improvements:** Real manga prompts are assembled and stored under `prompts/page_0X/`; switch to local/HF/Colab before judging prompt quality.
- **Recommended settings:** Keep mock for CI/pipeline; use real backend for creative review.

## Gate

**PILOT_APPROVED remains false.** Human must approve pages 1–5 (or explicitly open the pilot gate for further mock pipeline testing) before bulk generation.
