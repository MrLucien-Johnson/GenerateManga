# Generation

## Backends

| Name | Purpose | Remote network? |
|------|---------|-----------------|
| `mock` | Deterministic Pillow PNGs for tests / dry runs | No |
| `local` | Diffusers + torch with a **pre-downloaded** model path | No (after model present) |
| `huggingface` | HF Inference API | Yes (`HF_TOKEN`) |
| `free_remote` | Optional zero-cost remote exploration (e.g. Pollinations) when local/HF blocked | Yes (no API key typical) |
| `studio_image` | Optional studio/Cursor image exploration for design sketches | Tool-dependent |
| `colab` | Write job manifests / import notebook results | Optional (human-driven) |

Resolve via `echo.generation.registry.get_backend(name, root=...)`.

`free_remote` and `studio_image` are **optional exploration** backends when local GPU or Hugging Face are blocked. They are not auto-cleared for commercial KDP — record provenance in `reports/model-licensing.json` and have the owner review ToS / rights before production. Prefer `local` or `huggingface` when available. See also `docs/COLAB.md`.

## Provenance (Phase 12)

Every `GenerationRecord` carries:

| Field | Default | Meaning |
|-------|---------|---------|
| `source_type` | `UNKNOWN` | `MOCK` / `REAL` / `UNKNOWN` |
| `production_eligible` | `false` | Must be true to approve into production |
| `model_revision` | optional | Model revision / hash |
| `license_notes` | optional | Licensing notes |

- `record.is_mock()` is true when `source_type==MOCK` **or** `backend=="mock"`.
- `create_record` / `save_record` force `source_type=MOCK` and `production_eligible=False` when `backend=="mock"`.
- Mock assets **cannot** open `KAITO_REFERENCE_APPROVED`, cannot be production-approved (unless `force_non_production=True` for tests), and cannot enter a gated production PDF.

## Enabling mock mode

Any of:

```bash
export ECHO_MOCK_GENERATION=1
```

or in `config/generation.json`:

```json
{ "use_mock_backend": true, "default_backend": "mock" }
```

Production default (Phase 12): `use_mock_backend: false`, `default_backend: "local"`.

Tests always use mock via `ECHO_MOCK_GENERATION=1` in fixtures — they must not call remote image APIs.

## Design candidates

```bash
python scripts/check_generation_environment.py   # LOCAL_GENERATION READY/BLOCKED
python scripts/generate_kaito_designs.py         # N=4 candidates; refuses mock; does not select
python scripts/import_colab_kaito_designs.py <pkg>
```

Colab GPU path (Phase 12): `colab/echo_of_the_inkwell_generator.ipynb` — requires CUDA; prints `COLAB_GPU_BLOCKED` and stops with no mock images if GPU is missing. Import the zip with `import_colab_kaito_designs.py`.

Candidates live under `characters/kaito/design-candidates/`. Human selects via Streamlit **Kaito Master Design** or `select_master(id)`. Never auto-select.

## Typical generate → record cycle

```python
from echo.generation.mock_backend import MockGenerationBackend
from echo.generation.metadata import create_record
from echo.core.schemas import ArtStatus

backend = MockGenerationBackend(root=root)
result = backend.generate(prompt=..., width=256, height=256, seed=1, output_path=path)
record = create_record(
    page_id="p1",
    backend="mock",
    seed=result.seed,
    output_path=result.output_path,
    positive_prompt=...,
    status=ArtStatus.GENERATED,
    root=root,
)
# record.source_type == MOCK, production_eligible == False
```

For production-path tests, use `backend="test"`, `source_type=REAL`, `production_eligible=True`.

Records live at `generations/<record_id>/record.json` with a `_by_page/<page_id>/` index.

## Prompt assembly

`PromptBuilder.build(page_id, seed=..., save=True)` layers:

1. Master visual style + coloring-book rules
2. Character bible / continuity rules
3. Objects + locations
4. Page / panel scene text
5. Continuity reminder + reference status
6. Negative constraints (no baked text, no color washes, etc.)

Saved under `prompts/<page_id>/latest.json`.

## Regeneration

Backends expose `regenerate(...)`. Default implementation calls `generate` and may pass `previous_seed` in settings. Always create a **new** `GenerationRecord` (optionally with `parent_id`) — do not overwrite prior candidates in place.

## Health checks

```python
backend.health_check()  # available, seed/negative/reference support, model info
```

Unavailable backends raise `BackendUnavailable` with a user-facing hint (install extras, set token, or enable mock).
