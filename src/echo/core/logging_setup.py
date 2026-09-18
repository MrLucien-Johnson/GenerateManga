"""Logging setup — writes to ``logs/``, never logs secrets."""

from __future__ import annotations

import logging
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Iterable

from echo.core.paths import logs_dir

# Patterns that should never appear in log output.
_SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)(hf[_-]?token|api[_-]?key|secret|password|token)\s*[:=]\s*\S+"),
    re.compile(r"(?i)Bearer\s+[A-Za-z0-9._\-]+"),
    re.compile(r"hf_[A-Za-z0-9]{10,}"),
)

_SENSITIVE_KEYS = frozenset(
    {
        "hf_token",
        "token",
        "api_key",
        "apikey",
        "password",
        "secret",
        "authorization",
        "HF_TOKEN",
    }
)


class SecretRedactingFilter(logging.Filter):
    """Redact known secret patterns from log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()
        except Exception:
            return True
        redacted = msg
        for pattern in _SECRET_PATTERNS:
            if pattern.groups:
                redacted = pattern.sub(
                    lambda m: f"{m.group(1)}=***REDACTED***",
                    redacted,
                )
            else:
                redacted = pattern.sub("***REDACTED***", redacted)
        if redacted != msg:
            record.msg = redacted
            record.args = ()
        return True


def redact_mapping(data: dict) -> dict:
    """Return a copy of ``data`` with sensitive keys replaced."""
    out: dict = {}
    for key, value in data.items():
        if key in _SENSITIVE_KEYS or str(key).lower() in {k.lower() for k in _SENSITIVE_KEYS}:
            out[key] = "***REDACTED***"
        elif isinstance(value, dict):
            out[key] = redact_mapping(value)
        else:
            out[key] = value
    return out


def setup_logging(
    *,
    name: str = "echo",
    level: int | str = logging.INFO,
    log_file: str | Path | None = None,
    root: Path | None = None,
    also_console: bool = True,
) -> logging.Logger:
    """Configure and return the Echo logger.

    Logs go to ``logs/echo.log`` by default. Secrets are redacted.
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(level)
    logger.propagate = False

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    secret_filter = SecretRedactingFilter()

    file_path = Path(log_file) if log_file else logs_dir(root) / "echo.log"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        file_path,
        maxBytes=5_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.addFilter(secret_filter)
    logger.addHandler(file_handler)

    if also_console:
        console = logging.StreamHandler()
        console.setFormatter(formatter)
        console.addFilter(secret_filter)
        logger.addHandler(console)

    return logger


def get_logger(name: str = "echo") -> logging.Logger:
    """Return a child logger; ensures root echo logging is configured."""
    root = logging.getLogger("echo")
    if not root.handlers:
        setup_logging()
    if name == "echo":
        return root
    return logging.getLogger(name)


def reset_logging(names: Iterable[str] = ("echo",)) -> None:
    """Remove handlers (for tests)."""
    for name in names:
        logger = logging.getLogger(name)
        for handler in list(logger.handlers):
            logger.removeHandler(handler)
            handler.close()
