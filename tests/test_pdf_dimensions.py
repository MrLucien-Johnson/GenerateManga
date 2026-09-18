"""KDP PDF dimensions and blank reverse assembly with mock approved art."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from PIL import Image

from echo.continuity.gates import GateName, set_gate
from echo.core.errors import GateBlocked, ValidationError
from echo.core.state import load_state, save_state
from echo.publishing.kdp import build_kdp_pdf
from echo.story.physical_pages import PhysicalPageMapper


def _write_approved(tmp_project: Path, name: str, size: tuple[int, int] = (128, 128)) -> Path:
    path = tmp_project / "approved" / name
    Image.new("RGB", size, "white").save(path, format="PNG")
    return path


def _open_production_gates(tmp_project: Path) -> None:
    set_gate(GateName.KAITO_REFERENCE_APPROVED, True, root=tmp_project)
    set_gate(GateName.PILOT_APPROVED, True, root=tmp_project)
    state = load_state(root=tmp_project)
    state.gates.kaito_master_design_selected = True
    save_state(state, root=tmp_project)


def _pdf_mediabox_inches(pdf_path: Path) -> tuple[float, float]:
    raw = pdf_path.read_bytes()
    match = re.search(rb"/MediaBox\s*\[\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*\]", raw)
    assert match, "MediaBox not found in PDF"
    x0, y0, x1, y1 = (float(match.group(i)) for i in range(1, 5))
    return (x1 - x0) / 72.0, (y1 - y0) / 72.0


def _pdf_page_count(pdf_path: Path) -> int:
    raw = pdf_path.read_bytes()
    # Count page objects roughly via /Type /Page (not /Pages).
    return len(re.findall(rb"/Type\s*/Page(?!s)\b", raw))


def test_pdf_page_size_8_5_x_11_with_bleed(tmp_project: Path) -> None:
    _write_approved(tmp_project, "p1.png")
    _write_approved(tmp_project, "p2.png")
    _open_production_gates(tmp_project)

    out = build_kdp_pdf(root=tmp_project, require_gates=True)
    assert out.is_file()
    assert out.read_bytes()[:4] == b"%PDF"

    width_in, height_in = _pdf_mediabox_inches(out)
    # Trim 8.5x11 + 0.125 bleed each side => 8.75 x 11.25 inches.
    assert abs(width_in - 8.75) < 0.01
    assert abs(height_in - 11.25) < 0.01

    mapper = PhysicalPageMapper(root=tmp_project)
    assert mapper.total_physical_pages() == 6
    assert _pdf_page_count(out) == 6


def test_pdf_builds_with_blank_reverses(tmp_project: Path) -> None:
    _write_approved(tmp_project, "p1.png")
    _write_approved(tmp_project, "p2.png")
    out = build_kdp_pdf(root=tmp_project, require_gates=False)
    assert out.is_file()
    assert _pdf_page_count(out) == PhysicalPageMapper(root=tmp_project).total_physical_pages()


def test_pdf_blocked_by_gates(tmp_project: Path) -> None:
    _write_approved(tmp_project, "p1.png")
    with pytest.raises(GateBlocked):
        build_kdp_pdf(root=tmp_project, require_gates=True)


def test_pdf_requires_approved_art(tmp_project: Path) -> None:
    with pytest.raises(ValidationError):
        build_kdp_pdf(root=tmp_project, require_gates=False)
