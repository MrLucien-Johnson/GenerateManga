# Colab workflow

The `colab` backend is an **optional offline/online exchange**. Colab does not need to be connected for `available()` — the backend only needs the local `colab/` directories.

## Directories

```
colab/
  outbound/   # job manifests written by the toolkit
  inbound/    # PNGs + optional JSON metadata from the notebook
  echo_of_the_inkwell_generator.ipynb  # Phase 12 Kaito master design notebook
```

Inbound/outbound binaries are gitignored.

## Phase 12 — Kaito master designs (notebook)

Use `colab/echo_of_the_inkwell_generator.ipynb` when you have a **Colab GPU** and want REAL design candidates A–D:

1. Runtime → GPU.
2. Install deps → **GPU check** (prints `COLAB_GPU_BLOCKED` and stops if no CUDA — no mock/Pillow fakes).
3. Paste or upload `characters/kaito/character-bible.json`.
4. Generate four coloring-book B&W line-art candidates with an open anime/manga model (default documented in the notebook: Animagine XL 3.1; change `MODEL_ID` as needed).
5. Download the zip (`candidate_*.png` + `manifest.json` with `source_type=REAL`, seeds, prompts).
6. Import locally:

```bash
python scripts/import_colab_kaito_designs.py path/to/kaito_designs_*.zip
```

Review in Streamlit **Kaito Master Design**. Never auto-select. Record the model in `reports/model-licensing.json`.

## Generic page flow

1. Build a prompt locally (`PromptBuilder`).
2. Call `ColabBackend.generate(...)` or `prepare_manifest(...)`.
3. Upload the outbound JSON (+ reference images if needed) into your Colab notebook.
4. Run generation in Colab under your own account/GPU.
5. Download results into `colab/inbound/job_<id>.png` (optional `job_<id>.json` with seed/model).
6. Call `import_result(job_id)` → copies into `generations/colab/`.
7. Create a `GenerationRecord` and run the normal human approval path.

## Optional exploration backends (when local / HF blocked)

If local CUDA and Hugging Face Inference are unavailable, these are **optional exploration** paths only — not auto-cleared for KDP:

| Backend | Role | License caveat |
|---------|------|----------------|
| `free_remote` | Zero-cost remote probe (e.g. Pollinations) via local toolkit | Third-party ToS; owner must review before commercial use |
| `studio_image` | Cursor / studio image tooling for design sketches | Owner must verify rights; treat as exploration until licensed |
| `colab` | Human-driven GPU notebook (this doc) | Depends on the open weights you load in Colab |

Prefer `local` or `huggingface` when available. Mock remains tests-only (`ECHO_MOCK_GENERATION=1`).

## Notes

- `generate()` does **not** wait on a remote session. If inbound art is missing it returns `success=False` with the manifest path and `job_id`.
- Treat Colab outputs as candidates. Approval is still required.
- Keep secrets in Colab userdata / local `.env` — never commit tokens.
- Notebooks under `colab/` should document model license and that large weights stay outside git.
- Phase 12 notebook **never** generates mock Pillow placeholders; no GPU ⇒ `COLAB_GPU_BLOCKED`.
