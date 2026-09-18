# Colab workflow

The `colab` backend is an **optional offline/online exchange**. Colab does not need to be connected for `available()` — the backend only needs the local `colab/` directories.

## Directories

```
colab/
  outbound/   # job manifests written by the toolkit
  inbound/    # PNGs + optional JSON metadata from the notebook
```

Inbound/outbound binaries are gitignored.

## Flow

1. Build a prompt locally (`PromptBuilder`).
2. Call `ColabBackend.generate(...)` or `prepare_manifest(...)`.
3. Upload the outbound JSON (+ reference images if needed) into your Colab notebook.
4. Run generation in Colab under your own account/GPU.
5. Download results into `colab/inbound/job_<id>.png` (optional `job_<id>.json` with seed/model).
6. Call `import_result(job_id)` → copies into `generations/colab/`.
7. Create a `GenerationRecord` and run the normal human approval path.

## Notes

- `generate()` does **not** wait on a remote session. If inbound art is missing it returns `success=False` with the manifest path and `job_id`.
- Treat Colab outputs as candidates. Approval is still required.
- Keep secrets in Colab userdata / local `.env` — never commit tokens.
- Notebooks in this repo (if added under `colab/`) should document model license and that large weights stay outside git.
