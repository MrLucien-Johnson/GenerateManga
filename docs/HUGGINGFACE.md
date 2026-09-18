# Hugging Face backend

## Credentials

- Set `HF_TOKEN` in the environment or in a local `.env` (gitignored).
- Copy from `.env.example` — the example value is empty on purpose.
- Tokens are **never** read from `config/*.json`.

```bash
cp .env.example .env
# edit .env → HF_TOKEN=hf_...
export HF_TOKEN  # or rely on python-dotenv in your own scripts
```

## Install

```bash
pip install -e ".[hf]"
# or: pip install huggingface_hub
```

## Usage

```python
from echo.generation.registry import get_backend

backend = get_backend("huggingface", root=root)
ok, reason = backend.available()
if not ok:
    print(reason)  # missing token or package
else:
    result = backend.generate(prompt=..., width=1024, height=1024, seed=1)
```

Default model id comes from `config/generation.json` → `huggingface_model` (overridable in the backend constructor).

## Safety

- Tests must not call the live API; use `mock` / `ECHO_MOCK_GENERATION=1`.
- Check model license and ToS before using outputs commercially.
- Failures raise `BackendUnavailable` with a clear hint — do not retry blindly in loops that burn quota.
