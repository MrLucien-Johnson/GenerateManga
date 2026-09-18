# Local generation

Local Diffusers generation is optional (`pip install -e ".[local]"` → `torch`, `diffusers`).

## Hard rule: no silent auto-download

`LocalDiffusionBackend` **will not** download multi-GB weights automatically.

You must either:

1. Point `ECHO_LOCAL_MODEL_PATH` or `config/generation.json` → `local_model_path` at an **existing** model directory, and confirm you understand the size/license, or
2. Enable mock mode (`ECHO_MOCK_GENERATION=1` / `use_mock_backend`) for placeholders.

Setting `local_model_id` alone is insufficient — the backend refuses to fetch by id.

## VRAM and hardware (guidance)

| Hardware | Practical notes |
|----------|-----------------|
| 24 GB+ VRAM | Comfortable for many 1024² SD/Flux-class pipelines |
| 12–16 GB | Use smaller models, attention slicing, lower resolution for drafts |
| 8 GB | Draft/low-res only; prefer mock for pipeline testing |
| CPU only | Extremely slow; acceptable for tiny smoke experiments, not production |

Exact requirements depend on the weights you choose. Prefer generating draft sizes, then upscaling approved comps outside this toolkit if needed.

## Storage

- Model caches belong under ignored paths (`models/`, `huggingface/`, `.cache/`, etc. — see `.gitignore`).
- Generation PNGs under `generations/` are gitignored; keep metadata JSON if you need audit trails.
- Budget tens of GB for a single modern checkpoint plus caches.

## Licensing

You are responsible for the license of any checkpoint you place on disk (research-only, commercial, sharing restrictions). Echo of the Inkwell does not redistribute third-party weights.

## CPU fallback

If CUDA is unavailable, Diffusers may run on CPU when you wire a production pipeline — expect orders-of-magnitude slower runs. For engineering validation, **use the mock backend** instead of CPU diffusion.

## Current foundation build

This repo’s local backend probes install + model path availability. Full production inference still expects an explicit local runner or an extension of `LocalDiffusionBackend.generate`. Until then, use `mock` for tests and CI.
