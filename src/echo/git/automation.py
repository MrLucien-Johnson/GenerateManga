"""Optional GitPython automation — never commits ``.env``."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from echo.core.config import get_config
from echo.core.logging_setup import get_logger
from echo.core.paths import project_root

logger = get_logger("echo.git")

# Paths that must never be staged/committed by automation.
_NEVER_COMMIT = {
    ".env",
    ".env.local",
    ".env.production",
}


class GitAutomation:
    """Thin wrapper around GitPython with safe defaults."""

    def __init__(self, *, root: Path | None = None) -> None:
        self.root = root or project_root()
        self._repo = None
        self._gitpython_error: str | None = None

    def available(self) -> tuple[bool, str]:
        try:
            import git  # noqa: F401
        except ImportError:
            return False, "GitPython not installed (optional dependency)."
        try:
            self._ensure_repo()
        except Exception as exc:
            return False, f"Not a git repository or cannot open: {exc}"
        return True, "GitPython ready."

    def _ensure_repo(self) -> Any:
        if self._repo is not None:
            return self._repo
        from git import Repo

        self._repo = Repo(self.root)
        return self._repo

    def load_git_config(self) -> dict[str, Any]:
        try:
            return get_config("git", root=self.root)
        except Exception:
            return {"auto_commit_approved": True, "auto_push": False}

    def auto_commit_approved(
        self,
        paths: list[str | Path] | None = None,
        *,
        message: str | None = None,
    ) -> dict[str, Any]:
        """Stage approved assets and commit if ``auto_commit_approved`` is true.

        Never stages ``.env`` or other secret files. ``auto_push`` defaults false.
        """
        cfg = self.load_git_config()
        if not cfg.get("auto_commit_approved", True):
            return {"committed": False, "reason": "auto_commit_approved disabled in config/git.json"}

        ok, reason = self.available()
        if not ok:
            logger.info("Skipping git commit: %s", reason)
            return {"committed": False, "reason": reason}

        repo = self._ensure_repo()
        if paths is None:
            paths = ["approved"]
        safe_paths: list[str] = []
        for path in paths:
            p = Path(path)
            name = p.name
            if name in _NEVER_COMMIT or str(path) in _NEVER_COMMIT:
                logger.warning("Refusing to stage secret file: %s", path)
                continue
            # Block any path that looks like an env file.
            if name.startswith(".env"):
                logger.warning("Refusing to stage env file: %s", path)
                continue
            safe_paths.append(str(path))

        if not safe_paths:
            return {"committed": False, "reason": "No safe paths to commit."}

        repo.index.add(safe_paths)
        if not repo.index.diff("HEAD") and not repo.untracked_files:
            # Still may have staged changes; check staged.
            if not repo.index.diff("HEAD"):
                return {"committed": False, "reason": "Nothing to commit."}

        msg = message or "Approve art assets"
        commit = repo.index.commit(msg)
        result: dict[str, Any] = {
            "committed": True,
            "hexsha": commit.hexsha,
            "message": msg,
            "paths": safe_paths,
            "pushed": False,
        }

        if cfg.get("auto_push", False):
            try:
                origin = repo.remote(name="origin")
                origin.push()
                result["pushed"] = True
            except Exception as exc:
                logger.warning("auto_push failed: %s", exc)
                result["push_error"] = str(exc)
        return result


def auto_commit_approved(
    paths: list[str | Path] | None = None,
    *,
    root: Path | None = None,
    message: str | None = None,
) -> dict[str, Any]:
    return GitAutomation(root=root).auto_commit_approved(paths, message=message)
