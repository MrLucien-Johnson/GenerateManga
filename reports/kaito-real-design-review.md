# Kaito Real Design Review (TEMPLATE)

> **Status: BLOCKED** — awaiting REAL generation. Do not treat this file as a completed design review.

## Gate status

| Gate | Status |
|------|--------|
| `KAITO_MASTER_DESIGN_SELECTED` | **BLOCKED** — no master selected |
| `KAITO_REFERENCE_APPROVED` | **BLOCKED** — mock refs revoked (Phase 12) |
| `PILOT_APPROVED` | **BLOCKED** — mock pilot pages moved to `rejected/mock-pilot-pages/` |
| `PDF_READY` | **BLOCKED** |

## Environment

Run:

```bash
python scripts/check_generation_environment.py
```

| Check | Result |
|-------|--------|
| LOCAL_GENERATION | **BLOCKED** (placeholder until check is run on a GPU host) |
| CUDA / VRAM | _TBD_ |
| local_model_path | _TBD_ |
| diffusers / torch | _TBD_ |

## Design candidates

Generate with a REAL backend only:

```bash
python scripts/generate_kaito_designs.py
# or
python scripts/import_colab_kaito_designs.py path/to/package.zip --mark-production-eligible
```

| Candidate | Image | Model | Seed | Backend | source_type | Decision |
|-----------|-------|-------|------|---------|-------------|----------|
| A | _BLOCKED — not generated_ | — | — | — | — | — |
| B | _BLOCKED — not generated_ | — | — | — | — | — |
| C | _BLOCKED — not generated_ | — | — | — | — | — |
| D | _BLOCKED — not generated_ | — | — | — | — | — |

**Selected master:** `null` (do not auto-select)

## Human review checklist

- [ ] Environment READY (not mock)
- [ ] Four candidates reviewed side-by-side
- [ ] Continuity vs character bible verified
- [ ] Winner selected in Streamlit **Kaito Master Design** (with confirmation)
- [ ] Reference pack regenerated from selected master (REAL)
- [ ] `KAITO_REFERENCE_APPROVED` opened only after non-mock refs

## Notes

Phase 12 engineering landed schemas, mock production ban, design-candidate workflow, and gate resets. **Image generation and design selection are intentionally out of scope for this phase.**
