# Pilot report — Echo of the Inkwell

> **TEMPLATE — pilot not yet run.**  
> Pages **1–5** are pending Kaito reference approval and human page approval.  
> Do not treat this file as evidence of a completed pilot until the checklist below is filled and signed.

## Meta

| Field | Value |
|-------|--------|
| Volume | 1 |
| Pilot pages | Story pages 1–5 |
| Report status | **NOT RUN** |
| Date started | _TBD_ |
| Date completed | _TBD_ |
| Reviewer | _TBD_ |

## Prerequisites

| Gate / item | Status |
|-------------|--------|
| Kaito character bible present | Yes (in repo) |
| Kaito reference slots | MISSING (see `characters/kaito/continuity.json`) |
| `KAITO_REFERENCE_APPROVED` | **Closed** |
| Backend used for pilot | _TBD (mock / local / hf / colab)_ |
| Seeds recorded per page | _TBD_ |

## Page results (1–5)

| Story page | Page id | Candidate record id(s) | Approved path | Continuity OK | Notes |
|------------|---------|------------------------|---------------|---------------|-------|
| 1 | p1 | _pending_ | _pending_ | ☐ | |
| 2 | p2 | _pending_ | _pending_ | ☐ | |
| 3 | p3 | _pending_ | _pending_ | ☐ | |
| 4 | p4 | _pending_ | _pending_ | ☐ | |
| 5 | p5 | _pending_ | _pending_ | ☐ | |

## Continuity checklist summary

- [ ] Character identity matches locked references
- [ ] Costume / jacket consistency
- [ ] Key props (sketchbook / inkwell as applicable)
- [ ] Location match to page plan
- [ ] No baked-in dialogue text
- [ ] Clean line art for coloring-book print
- [ ] Story vs physical page mapping understood for print preview

## Decision

| Outcome | Mark when true |
|---------|----------------|
| Pilot **APPROVED** → open `PILOT_APPROVED` gate | ☐ |
| Pilot **REJECTED** → revise references/prompts and rerun | ☐ |
| Pilot **not run** (current) | ☑ |

## Sign-off

| Role | Name | Date |
|------|------|------|
| Art director / author | | |
| Engineering | | |

---

After approval, update `config/state.json` via `echo.continuity.gates.set_gate("PILOT_APPROVED", True)` and archive generation seeds in this report for reproducibility.
