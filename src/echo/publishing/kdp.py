"""Build KDP interior PDF from approved art only using reportlab."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from echo.core.config import get_config
from echo.core.errors import GateBlocked, ValidationError
from echo.core.paths import approved_dir, ensure_dir, project_root, resolve_path
from echo.story.physical_pages import PhysicalPageKind, PhysicalPageMapper
from echo.story.page_plan import load_page_plan


def _inch(value: float) -> float:
    return float(value)


def build_kdp_pdf(
    *,
    root: Path | None = None,
    output_path: str | Path | None = None,
    require_gates: bool = True,
    page_number_on_blanks: bool = False,
) -> Path:
    """Assemble a print PDF from approved images + blank reverse pages.

    Only files under ``approved/`` are used. Front matter / blank reverses
    follow :class:`~echo.story.physical_pages.PhysicalPageMapper`.
    """
    try:
        from reportlab.pdfgen import canvas
    except ImportError as exc:
        raise ValidationError(
            "reportlab is required to build KDP PDFs.",
            hint="pip install reportlab",
        ) from exc

    root = root or project_root()
    kdp = get_config("kdp", root=root)

    if require_gates:
        from echo.continuity.gates import evaluate_pdf_ready
        from echo.core.schemas import ArtStatus, SourceType
        from echo.generation.metadata import load_record
        from echo.core.paths import generations_dir

        report = evaluate_pdf_ready(root=root)
        if not report.get("pdf_ready"):
            raise GateBlocked(
                "PDF_READY",
                detail=(
                    f"approved={report.get('approved_count')}, "
                    f"kaito={report.get('kaito_reference_approved')}, "
                    f"master={report.get('kaito_master_design_selected')}, "
                    f"pilot={report.get('pilot_approved')}, "
                    f"prod_ok={report.get('production_assets_ok')}, "
                    f"missing={report.get('missing_pages')}"
                ),
            )

        # Extra hard ban: refuse MOCK approved assets even if gates look open.
        gen_root = generations_dir(root)
        if gen_root.is_dir():
            for record_json in gen_root.glob("*/record.json"):
                try:
                    record = load_record(record_json.parent.name, root=root)
                except Exception:
                    continue
                if record.status != ArtStatus.APPROVED:
                    continue
                if record.is_mock() or record.source_type == SourceType.MOCK:
                    raise GateBlocked(
                        "PDF_READY",
                        detail=f"Approved record {record.id} is MOCK — cannot build production PDF.",
                        hint="Remove mock assets from approved/ and regenerate with REAL backends.",
                    )

    trim_w = _inch(kdp.get("trim_width_in", 8.5))
    trim_h = _inch(kdp.get("trim_height_in", 11.0))
    bleed = _inch(kdp.get("bleed_in", 0.125))
    page_w = trim_w + 2 * bleed
    page_h = trim_h + 2 * bleed
    blank_reverse = bool(kdp.get("blank_reverse_pages", True))

    if output_path is None:
        out_rel = kdp.get("output_pdf") or "kdp/final/interior.pdf"
        output_path = resolve_path(out_rel, root=root)
    else:
        output_path = Path(output_path)
    ensure_dir(output_path.parent)

    plan = load_page_plan(root=root)
    plan.blank_reverse_pages = blank_reverse
    mapper = PhysicalPageMapper(plan, blank_reverse_pages=blank_reverse, root=root)

    approved = approved_dir(root)
    approved_files = sorted(
        p
        for p in approved.glob("**/*")
        if p.is_file() and p.suffix.lower() in {".png", ".jpg", ".jpeg"}
    )
    if not approved_files:
        raise ValidationError(
            "No approved art found.",
            hint="Approve at least one generation into approved/ first.",
        )

    def find_art(page_id: str | None, story_page: int | None) -> Path | None:
        if page_id:
            for path in approved_files:
                if path.stem == page_id or path.stem.startswith(f"{page_id}_") or path.stem.startswith(f"{page_id}-"):
                    return path
        if story_page is not None:
            for path in approved_files:
                if f"page{story_page}" in path.stem or f"p{story_page}" == path.stem:
                    return path
                if path.stem.endswith(f"_{story_page}") or path.stem.endswith(f"-{story_page}"):
                    return path
        return None

    c = canvas.Canvas(str(output_path), pagesize=(page_w * 72, page_h * 72))
    pages_written = 0

    # If no page plan, dump approved files sequentially with optional blanks.
    physical_pages = mapper.all_pages()
    if not plan.pages:
        for idx, art in enumerate(approved_files):
            _draw_image_page(c, art, page_w, page_h)
            pages_written += 1
            if blank_reverse:
                c.showPage()
                pages_written += 1
        c.save()
        return output_path

    art_fallback = list(approved_files)
    for phys in physical_pages:
        if phys.kind == PhysicalPageKind.FRONT_MATTER:
            c.showPage()
            pages_written += 1
            continue
        if phys.kind == PhysicalPageKind.BLANK_REVERSE:
            if page_number_on_blanks:
                c.setFillColorRGB(0.8, 0.8, 0.8)
                c.setFont("Helvetica", 10)
                c.drawCentredString(page_w * 36, 36, str(phys.physical_number))
            c.showPage()
            pages_written += 1
            continue
        # ILLUSTRATED
        art = find_art(phys.page_id, phys.story_page)
        if art is None and art_fallback:
            art = art_fallback.pop(0)
        if art is None:
            raise ValidationError(
                f"No approved art for story page {phys.story_page} ({phys.page_id}).",
                hint="Approve art whose filename stem matches the page id.",
            )
        _draw_image_page(c, art, page_w, page_h)
        pages_written += 1

    c.save()
    return output_path


def _draw_image_page(c: Any, image_path: Path, page_w_in: float, page_h_in: float) -> None:
    from reportlab.lib.utils import ImageReader

    img = ImageReader(str(image_path))
    c.drawImage(
        img,
        0,
        0,
        width=page_w_in * 72,
        height=page_h_in * 72,
        preserveAspectRatio=True,
        anchor="c",
    )
    c.showPage()
