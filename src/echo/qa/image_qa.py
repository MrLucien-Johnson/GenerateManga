"""Deterministic image QA checks."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from PIL import Image, UnidentifiedImageError


@dataclass
class ImageQAReport:
    path: str
    ok: bool
    exists: bool = False
    image_type: str | None = None
    width: int | None = None
    height: int | None = None
    aspect_ratio: float | None = None
    has_alpha: bool | None = None
    corrupted: bool = False
    sha256: str | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "ok": self.ok,
            "exists": self.exists,
            "image_type": self.image_type,
            "width": self.width,
            "height": self.height,
            "aspect_ratio": self.aspect_ratio,
            "has_alpha": self.has_alpha,
            "corrupted": self.corrupted,
            "sha256": self.sha256,
            "errors": self.errors,
            "warnings": self.warnings,
        }


def _file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def check_image(
    path: str | Path,
    *,
    expect_width: int | None = None,
    expect_height: int | None = None,
    expect_aspect: float | None = None,
    aspect_tolerance: float = 0.02,
    allow_alpha: bool = True,
) -> ImageQAReport:
    """Run deterministic checks on a single image file."""
    path = Path(path)
    report = ImageQAReport(path=str(path), ok=False)
    if not path.is_file():
        report.errors.append("File does not exist")
        return report
    report.exists = True

    try:
        report.sha256 = _file_hash(path)
        with Image.open(path) as img:
            img.verify()
        with Image.open(path) as img:
            report.image_type = img.format
            report.width, report.height = img.size
            report.has_alpha = (
                img.mode in {"RGBA", "LA"}
                or (img.mode == "P" and "transparency" in img.info)
            )
            if report.height:
                report.aspect_ratio = report.width / report.height
    except UnidentifiedImageError:
        report.corrupted = True
        report.errors.append("Unidentified or unsupported image type")
        return report
    except OSError as exc:
        report.corrupted = True
        report.errors.append(f"Corrupt or unreadable image: {exc}")
        return report

    if expect_width and report.width != expect_width:
        report.errors.append(f"Width {report.width} != expected {expect_width}")
    if expect_height and report.height != expect_height:
        report.errors.append(f"Height {report.height} != expected {expect_height}")
    if expect_aspect and report.aspect_ratio is not None:
        if abs(report.aspect_ratio - expect_aspect) > aspect_tolerance:
            report.errors.append(
                f"Aspect {report.aspect_ratio:.4f} != expected {expect_aspect:.4f}"
            )
    if report.has_alpha and not allow_alpha:
        report.warnings.append("Image has alpha channel")

    report.ok = not report.errors and not report.corrupted
    return report


def check_images(
    paths: list[str | Path],
    *,
    detect_duplicates: bool = True,
    **kwargs: Any,
) -> dict[str, Any]:
    """Check many images; optionally flag SHA-256 duplicates."""
    reports = [check_image(p, **kwargs) for p in paths]
    duplicates: list[list[str]] = []
    if detect_duplicates:
        by_hash: dict[str, list[str]] = {}
        for rep in reports:
            if rep.sha256:
                by_hash.setdefault(rep.sha256, []).append(rep.path)
        duplicates = [group for group in by_hash.values() if len(group) > 1]
        for group in duplicates:
            for rep in reports:
                if rep.path in group:
                    rep.warnings.append(f"Duplicate hash group: {group}")

    return {
        "ok": all(r.ok for r in reports) and not duplicates,
        "count": len(reports),
        "passed": sum(1 for r in reports if r.ok),
        "failed": sum(1 for r in reports if not r.ok),
        "duplicates": duplicates,
        "reports": [r.to_dict() for r in reports],
    }
