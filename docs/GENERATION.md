# Generation

## Backends

| Name | Purpose | Remote network? |
|------|---------|-----------------|
| `mock` | Deterministic Pillow PNGs for tests / dry runs | No |
| `local` | Diffusers + torch with a **pre-downloaded** model path | No (after model present) |
| `huggingface` | HF Inference API | Yes (`HF_TOKEN`) |
| `colab` | Write job manifests / import notebook results | Optional (human-driven) |

Resolve via `echo.generation.registry.get_backend(name, root=...)`.

## Enabling mock mode

Any of:

```bash
export ECHO_MOCK_GENERATION=1
```

or in `config/generation.json`:

```json
{ "use_mock_backend": true, "default_backend": "mock" }
```

Tests always use mock — they must not call remote image APIs.

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
```

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
