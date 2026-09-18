# Architecture

Echo of the Inkwell is a **local-first production toolkit**: story packs and configs live in the repo; generation backends plug in behind a common interface; humans approve art; publishing builds print PDFs only from `approved/`.

## Package map (`src/echo/`)

| Module | Role |
|--------|------|
| `core` | Paths (`ECHO_PROJECT_ROOT`), config, state, schemas, errors, logging |
| `story` | Page plan load/save; **physical page mapping** (story ≠ print) |
| `characters` | Generic character manager (bibles, continuity, reference status) |
| `prompts` | Style constants + layered `PromptBuilder` + prompt history |
| `generation` | Backends: `mock`, `local`, `huggingface`, `colab` + metadata records |
| `review` | Approval state machine (`GENERATED` → `APPROVED` / `REJECTED`) |
| `continuity` | Checklist + production gates (`KAITO_REFERENCE_APPROVED`, `PILOT_APPROVED`, `PDF_READY`) |
| `composition` | Panel layout / text overlay helpers (post-generation) |
| `publishing` | KDP PDF (reportlab) + preflight |
| `qa` | Image QA + print readiness checks |
| `git` | Optional GitPython helpers; never stages `.env`; `auto_push` defaults false |

## Data flow

```
story/page-plan.json
        │
        ▼
 PromptBuilder ──► prompts/<page_id>/
        │
        ▼
 GenerationBackend ──► generations/ + GenerationRecord
        │
        ▼
 Human review (ApprovalWorkflow)
        │
   ┌────┴────┐
   ▼         ▼
approved/  rejected/
   │
   ▼
 continuity gates + preflight
   │
   ▼
 kdp/final/interior.pdf   ← manual upload only
```

## Project root resolution

1. `ECHO_PROJECT_ROOT` env var
2. Walk upward for `pyproject.toml`, `config/project.json`, or `.git`
3. Fall back to cwd

Tests set `ECHO_PROJECT_ROOT` to a `tmp_path` and call `clear_path_cache()`.

## Config files (`config/`)

- `project.json` — name, default character, directory names
- `generation.json` — backend, dimensions, mock flag, model paths (no secrets)
- `kdp.json` — 8.5×11 trim, bleed, blank reverses, DPI, output path
- `git.json` — auto-commit approved (optional), **auto_push false**
- `state.json` — runtime gates/progress (gitignored)

## Hard rules encoded in code

- Mock/test art is labeled non-production.
- Approval never silently overwrites an existing approved file (`force=True` required).
- PDF builder uses **approved art only**.
- Hugging Face token is read from **`HF_TOKEN` environment only**.
- Local backend **does not auto-download** multi-GB weights.
