# Echo of the Inkwell

Local-first manga studio toolkit for producing **Echo of the Inkwell** — a coloring-book style children's manga — through human-approved generation, continuity gates, and KDP-ready PDF assembly.

This repository is **local-first**. Nothing publishes itself. Generation candidates stay on disk until a human approves them. There is **no auto-publish** to Amazon KDP or any storefront.

## Status: two different “done”

| Status | Meaning |
|--------|---------|
| **ENGINEERING COMPLETE** | Package, configs, story packs, mock generation, approval workflow, gates, PDF builder, and tests exist and pass. You can clone and run the pipeline with the **mock** backend. |
| **BOOK PRODUCTION COMPLETE** | Kaito references approved, pilot pages 1–5 approved, full volume art approved, preflight green, interior PDF accepted for print. **Not reached yet.** |

Until the pilot gate passes, treat every PNG from mock/local/HF/Colab as a candidate — never as finished book art.

## Quick start (clone → first mock generation)

```bash
git clone https://github.com/mrlucien-johnson/generatemanga.git
cd generatemanga

python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

pip install -e ".[dev]"
# or: pip install -r requirements.txt && pip install pytest

cp .env.example .env        # optional; leave HF_TOKEN empty for mock work
export ECHO_MOCK_GENERATION=1
```

Run the test suite (uses the Pillow mock backend — **no remote image APIs**):

```bash
pytest -q
```

First mock generation from Python:

```bash
python - <<'PY'
from pathlib import Path
from echo.generation.mock_backend import MockGenerationBackend
from echo.generation.metadata import create_record
from echo.core.schemas import ArtStatus

root = Path(".").resolve()
backend = MockGenerationBackend(root=root)
out = root / "generations" / "demo_p1.png"
result = backend.generate(
    prompt="Kaito at his desk, clean manga line art",
    width=512,
    height=512,
    seed=42,
    output_path=out,
)
record = create_record(
    page_id="p1",
    backend="mock",
    seed=result.seed,
    output_path=result.output_path,
    status=ArtStatus.GENERATED,
    root=root,
)
print("wrote", result.output_path, "record", record.id)
print("Label this NON-PRODUCTION until human approval.")
PY
```

Approve only after visual review:

```bash
python - <<'PY'
from echo.review.approval import approve
# approve("<record_id>")  # copies into approved/; never overwrites silently
PY
```

## Core commands

| Goal | Command / API |
|------|----------------|
| Install (dev) | `pip install -e ".[dev]"` |
| Tests (mock only) | `pytest -q` |
| Force mock backend | `export ECHO_MOCK_GENERATION=1` or set `config/generation.json` → `"use_mock_backend": true` |
| Build prompt for a page | `PromptBuilder(root=...).build("p1", seed=1, save=True)` |
| Approve / reject | `ApprovalWorkflow.approve(id)` / `.reject(id)` |
| Map story ↔ physical pages | `PhysicalPageMapper` |
| Preflight report | `echo.publishing.preflight.run_preflight()` |
| Build KDP PDF (approved art only) | `echo.publishing.kdp.build_kdp_pdf(require_gates=True)` |

Optional backends (not required for tests):

- **Local Diffusers** — see [docs/LOCAL_GENERATION.md](docs/LOCAL_GENERATION.md) (no auto-download of multi-GB weights)
- **Hugging Face Inference** — see [docs/HUGGINGFACE.md](docs/HUGGINGFACE.md) (`HF_TOKEN` from env only)
- **Google Colab exchange** — see [docs/COLAB.md](docs/COLAB.md)

## Principles

1. **Human approval** — generated files land in `generations/`; only approved copies enter `approved/`.
2. **Never auto-publish** — `config/git.json` keeps `auto_push: false`; KDP upload is always a manual human step.
3. **Story page ≠ physical page** — front matter and blank reverse pages shift print numbers ([docs/KDP_WORKFLOW.md](docs/KDP_WORKFLOW.md)).
4. **Continuity gates** — Kaito reference approval and pilot approval block “PDF ready” until opened.
5. **Secrets stay local** — `.env` is gitignored; tokens are never read from JSON configs.

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Generation](docs/GENERATION.md)
- [Character continuity](docs/CHARACTER_CONTINUITY.md)
- [Story workflow](docs/STORY_WORKFLOW.md)
- [Colab](docs/COLAB.md)
- [Hugging Face](docs/HUGGINGFACE.md)
- [Local generation](docs/LOCAL_GENERATION.md)
- [KDP workflow](docs/KDP_WORKFLOW.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)
- [Large files](docs/LARGE_FILES.md)
- [Production phases](docs/PRODUCTION_PHASES.md)
- [Pilot report template](reports/pilot-report.md)

## Layout (high level)

```
src/echo/          Python package (core, generation, review, publishing, …)
story/             Manuscript, story bible, page plan
characters/        Character bibles + continuity + references
locations/         Location bibles
objects/           Object bibles (e.g. inkwell)
config/            project, generation, kdp, git JSON
generations/       Candidates (gitignored binaries)
approved/          Human-approved art only
rejected/          Rejected candidates
kdp/               Interior / preview / final PDF outputs
tests/             pytest suite (mock backend)
docs/              Operator documentation
```

## License

MIT — see `pyproject.toml`. Respect model and asset licenses separately when using remote or local diffusion weights.
