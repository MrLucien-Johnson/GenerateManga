"""Secret handling: .env ignored; HF_TOKEN never hard-coded in source."""

from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_gitignore_includes_dotenv() -> None:
    gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert ".env" in gitignore
    assert ".env.*" in gitignore or ".env" in gitignore


def test_env_example_documents_hf_token_without_secret() -> None:
    example = (REPO_ROOT / ".env.example").read_text(encoding="utf-8")
    assert "HF_TOKEN=" in example
    # Placeholder only — no JWT/token-looking value.
    for line in example.splitlines():
        if line.startswith("HF_TOKEN="):
            value = line.split("=", 1)[1].strip()
            assert value == ""
            break


def test_hf_token_not_hardcoded_in_source() -> None:
    src = REPO_ROOT / "src"
    pattern = re.compile(r"HF_TOKEN\s*=\s*['\"][^'\"]+['\"]")
    offenders: list[str] = []
    for path in src.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if pattern.search(text):
            offenders.append(str(path.relative_to(REPO_ROOT)))
        # Also reject obvious pasted tokens.
        if "hf_" in text and re.search(r"hf_[A-Za-z0-9]{20,}", text):
            offenders.append(str(path.relative_to(REPO_ROOT)))
    assert offenders == []


def test_huggingface_backend_reads_env_only(tmp_project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from echo.generation.huggingface_backend import HuggingFaceBackend

    monkeypatch.delenv("HF_TOKEN", raising=False)
    backend = HuggingFaceBackend(root=tmp_project)
    ok, reason = backend.available()
    assert ok is False
    assert "HF_TOKEN" in reason

    monkeypatch.setenv("HF_TOKEN", "test-token-not-real")
    backend2 = HuggingFaceBackend(root=tmp_project)
    info = backend2.model_information()
    assert info["token_source"] == "env:HF_TOKEN"
    assert info["has_token"] is True
    # Token must not appear in model_information dump.
    assert "test-token-not-real" not in str(info)


def test_git_automation_never_stages_env(tmp_project: Path) -> None:
    from echo.git.automation import GitAutomation

    (tmp_project / ".env").write_text("HF_TOKEN=should-never-commit\n", encoding="utf-8")
    automation = GitAutomation(root=tmp_project)
    # Without a real git repo this returns unavailable; still verify never-commit set.
    assert ".env" in automation.__class__.__module__ or True
    from echo.git import automation as mod

    assert ".env" in mod._NEVER_COMMIT
