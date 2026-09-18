# Kaito Real Design Review — Phase 12

**Status:** HUMAN SELECTION REQUIRED  
**Gate:** `KAITO_MASTER_DESIGN_SELECTED = false`  
**Do not auto-select.** Engineering must not choose A/B/C/D for you.

## Backend used

| Field | Value |
|-------|--------|
| Primary attempt | Local diffusion — **BLOCKED** (no CUDA, no torch, no diffusers) |
| Hugging Face | **BLOCKED** (`HF_TOKEN` unset) |
| Free remote (Pollinations) | Tried; early samples mismatched character bible (wrong hair/gender cues) — discarded |
| Candidates delivered via | **`studio_image` / `cursor-generate-image`** (genuine AI manga line-art, not mock Pillow) |
| Model revision | n/a (studio image tool) |
| License | **Owner review required** — not auto-cleared for commercial KDP |

## Environment (this host)

```
LOCAL_GENERATION: BLOCKED
Reason: torch/diffusers/transformers/accelerate/safetensors missing; nvidia-smi absent; no local_model_path
RAM: ~16 GB | Disk free: ~228 GB
```

## Candidate count

**4** real design candidates (A–D)

## Candidate paths

| Candidate | Image | Metadata | Seed | Dimensions | Status |
|-----------|-------|----------|------|------------|--------|
| **A** | `characters/kaito/design-candidates/kaito-design-A.png` | `…/a4c10d3b2aba447cbad141d74ff5790b.json` | 12001 | 864×1152 | AWAITING_DESIGN_SELECTION |
| **B** | `characters/kaito/design-candidates/kaito-design-B.png` | `…/85e8eee6419b4e0f8ec83e460878c7d8.json` | 12098 | 864×1152 | AWAITING_DESIGN_SELECTION |
| **C** | `characters/kaito/design-candidates/kaito-design-C.png` | `…/2e236f6ad9aa424f939785374118cc80.json` | 12195 | 864×1152 | AWAITING_DESIGN_SELECTION |
| **D** | `characters/kaito/design-candidates/kaito-design-D.png` | `…/9445dc9fc1e04ee3b31e3a51de4a4123.json` | 12292 | 864×1152 | AWAITING_DESIGN_SELECTION |

## Candidate notes (for your eye — not a choice)

- **A:** Confident/curious; full-body + face; hood down; hoodie + sneakers  
- **B:** Softer thoughtful bust + full-body; jogger-style trousers  
- **C:** Adventurous grin; cargo trousers; hands in pockets  
- **D:** Focused creative; holding sketchbook  

All are black-and-white manga line art with messy spiky hair and hooded jacket — **not** geometric mock placeholders.

## Production / gate honesty

| Item | Count / state |
|------|----------------|
| Mock placeholders (legacy refs) | Still under `characters/kaito/references/` as NON-PRODUCTION; **cannot** open `KAITO_REFERENCE_APPROVED` |
| Real design candidates | 4 |
| Kaito selected | **NO** |
| Kaito references approved | **0/8** (canonical pack not generated until you pick a master) |
| Pilot pages approved | **0/5** (mock pilot revoked in Phase 12) |
| Final story pages approved | **0/50** |

## HUMAN SELECTION REQUIRED

1. Pull this branch / open the files above on GitHub  
2. Or launch review UI:

```bash
streamlit run app.py
```

3. Open sidebar → **Kaito Master Design**  
4. Compare A–D → **SELECT AS KAITO** with confirmation  
5. Or request regeneration  

Until you select:

- `KAITO_MASTER_DESIGN_SELECTED = false`  
- `KAITO_REFERENCE_APPROVED = false`  
- No manga pages 1–50 / 1–5 production generation  

## Colab (still available for future consistency packs)

Notebook: `colab/echo_of_the_inkwell_generator.ipynb`  
Import: `python scripts/import_colab_kaito_designs.py <package.zip>`
