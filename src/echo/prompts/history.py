"""Store composed prompts under ``prompts/``."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from echo.core.paths import ensure_dir, prompts_dir


def save_prompt(
    payload: dict[str, Any],
    *,
    page_id: str,
    root: Path | None = None,
) -> Path:
    """Persist a prompt dict as JSON under ``prompts/<page_id>/``."""
    base = ensure_dir(prompts_dir(root) / page_id)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = base / f"{stamp}_{uuid4().hex[:8]}.json"
    record = {
        **payload,
        "saved_at": stamp,
        "page_id": page_id,
    }
    path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    # Also write/overwrite a "latest" pointer for convenience.
    latest = base / "latest.json"
    latest.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    return path


def load_latest_prompt(page_id: str, *, root: Path | None = None) -> dict[str, Any] | None:
    path = prompts_dir(root) / page_id / "latest.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def list_prompts(page_id: str, *, root: Path | None = None) -> list[Path]:
    base = prompts_dir(root) / page_id
    if not base.is_dir():
        return []
    return sorted(p for p in base.glob("*.json") if p.name != "latest.json")
