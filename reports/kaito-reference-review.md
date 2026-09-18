# KAITO CHARACTER DESIGN APPROVAL — Human Review Gate

**Status:** WAITING FOR YOUR APPROVAL  
**Engineering:** complete enough to generate and review candidates  
**Book production:** NOT started (`KAITO_REFERENCE_APPROVED=false`)

## Important honesty note

The current reference candidates were produced by the **mock** backend (`mock-lineart`).
They are **geometric NON-PRODUCTION TEST placeholders**, not final manga line art.

They exist so you can exercise the approval workflow, inspect metadata/seeds, and
decide when to run a real backend (local diffusion / Colab / Hugging Face).

**Do not lock Kaito or open `KAITO_REFERENCE_APPROVED` based on mock placeholders
if you intend to publish.** Regenerate with a real model first, then approve.

## Candidate files (GENERATED, not APPROVED)

| Slot | File | Seed | Record ID |
|------|------|------|-----------|
| front | `characters/kaito/references/kaito_front.png` | 2433183897 | `b3237568fefa44e3a8377793f5c3965a` |
| three-quarter | `characters/kaito/references/kaito_three_quarter.png` | 1642863531 | `7889fd93846f4c51ac77a70818401aef` |
| side | `characters/kaito/references/kaito_side.png` | 3291108921 | `ef5d002cd4134e079c45177c0e92763c` |
| back | `characters/kaito/references/kaito_back.png` | 2583163590 | `d7f9dbaabbca4f4d93d5e6ce1a1e87ac` |
| full-body | `characters/kaito/references/kaito_full_body.png` | 3875203750 | `25de94ae5b2e40bfa51338957f2e92e3` |
| expressions | `characters/kaito/references/kaito_expressions.png` | 3955163007 | `a9520d77ab9a4be2a8c76a9973097176` |
| hands | `characters/kaito/references/kaito_hands.png` | 3359173021 | `e2f492ef340243c4b0040dfdabf34a4e` |
| jacket-detail | `characters/kaito/references/kaito_jacket_detail.png` | 3412683992 | `6678566f2b754ee2bcce5f0447ca86d3` |

Full prompts and settings: `generations/<record_id>/record.json`.

## Backend used for these candidates

- Backend: `mock`
- Model: `mock-lineart`
- Dimensions: 1024×1024
- Label burned into images: `NON-PRODUCTION TEST`

## How to review

1. Open the Review Studio:
   ```bash
   streamlit run app.py
   ```
2. Go to **Continuity / References**.
3. Inspect each slot against `characters/kaito/character-bible.json`.
4. Approve / reject / lock slots deliberately (UI buttons or CLI below).
5. Only when you are satisfied with a **real** design, open the gate.

### CLI alternatives

```bash
# After regenerating with a real backend and reviewing:
python scripts/approve_reference.py kaito front
python scripts/approve_reference.py kaito --all
python scripts/approve_reference.py kaito --open-gate --confirm-design
```

## What happens after you approve

1. `KAITO_REFERENCE_APPROVED = true`
2. You may run the pilot batch:
   ```bash
   python scripts/generate_pilot.py
   ```
3. Stop again for pilot continuity review (`reports/pilot-report.md`).
4. Only then enable larger production batches.

## Real generation routes (when ready)

```bash
# Local (requires diffusers + model you install deliberately)
# Edit config/generation.json: use_mock_backend=false, default_backend=local

# Hugging Face (optional; needs HF_TOKEN in .env — never commit it)
# default_backend=huggingface

# Colab (optional notebook)
# See colab/echo_of_the_inkwell_generator.ipynb and docs/COLAB.md
```

See also: `docs/LOCAL_GENERATION.md`, `docs/HUGGINGFACE.md`, `docs/CHARACTER_CONTINUITY.md`.
