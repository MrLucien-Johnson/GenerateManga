# Troubleshooting

## `BackendUnavailable`

- **mock**: should never fail if Pillow is installed (`pip install -e .`).
- **local**: install `[local]` extras; set an existing `local_model_path`; or enable mock. No auto-download.
- **huggingface**: export `HF_TOKEN`; install `[hf]`; check model access.
- **colab**: write manifest, run notebook, place inbound PNG, then `import_result`.

## Approval errors

- **Already APPROVED** — pass `force=True` only when deliberately replacing.
- **Generated file missing** — `output_path` broken or cleaned; regenerate.
- **Cannot reject APPROVED** — `unapprove` first or replace deliberately.

## GateBlocked / PDF_READY NO

Check `config/state.json` gates and `evaluate_pdf_ready` / `run_preflight`:

- Kaito references still `MISSING`
- Pilot not approved
- Missing `approved/pN.png` for required page ids

## Story page numbers look “wrong” in print

You are seeing physical pages. Use `PhysicalPageMapper.story_to_physical` / `physical_to_story`. Remember blank reverses and front matter.

## Tests cannot find project root

Set `ECHO_PROJECT_ROOT` and call `echo.core.paths.clear_path_cache()` (fixtures already do this).

## Invalid page-plan / character bible

Production packs use `character-bible.json` and rich page-plan fields. The package normalizes these on load. If validation fails, check JSON syntax first, then ensure `story_page` is present on each page.

## Secrets accidentally staged

`.env` is gitignored and Git automation refuses `.env*` paths. If a secret was committed historically, rotate the token immediately and scrub history.

## Large files bloating clones

See [LARGE_FILES.md](LARGE_FILES.md). Prefer local-only candidates; use LFS or external storage deliberately.
