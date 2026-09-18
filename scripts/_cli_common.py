"""Shared CLI helpers for Echo of the Inkwell scripts and Streamlit app.

Works around known story/package mismatches:
- ``story/page-plan.json`` uses editorial fields (no ``id``, string ``version``)
  while ``echo.story.page_plan.PageEntry`` requires ``id`` and int ``version``.
- Character bibles are stored as ``character-bible.json`` / ``location-bible.json``
  while ``CharacterManager`` looks for ``bible.json``.
- Reference slot lifecycle lives in ``continuity.json`` ``reference_slots``;
  ``CharacterManager`` also tracks ``references/status.json``.
"""

from __future__ import annotations

import json
import os
import sys
import traceback
from pathlib import Path
from typing import Any

# Ensure src/ is importable when scripts are run directly.
_ROOT_CANDIDATE = Path(__file__).resolve().parents[1]
_SRC = _ROOT_CANDIDATE / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from echo.core.config import get_config, mock_generation_enabled  # noqa: E402
from echo.core.errors import EchoError  # noqa: E402
from echo.core.paths import project_root, story_dir  # noqa: E402
from echo.core.schemas import ArtStatus, ReferenceStatus  # noqa: E402
from echo.core.state import load_state  # noqa: E402
from echo.generation.registry import get_backend  # noqa: E402
from echo.prompts.style import (  # noqa: E402
    COLORING_BOOK_RULES,
    MASTER_VISUAL_STYLE,
    NEGATIVE_CONSTRAINTS,
)
from echo.story.page_plan import PageEntry, PagePlan, PanelPlan  # noqa: E402

NON_PRODUCTION_LABEL = "NON-PRODUCTION TEST"
STORY_PAGE_COUNT = 50


def root() -> Path:
    return project_root()


def die(message: str, *, code: int = 1, hint: str | None = None) -> None:
    """Print a useful error and exit (no raw stack trace)."""
    print(f"ERROR: {message}", file=sys.stderr)
    if hint:
        print(f"Hint: {hint}", file=sys.stderr)
    raise SystemExit(code)


def handle_cli_errors(fn):
    """Decorator: turn EchoError / common failures into clean exits."""

    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except EchoError as exc:
            die(exc.message, hint=exc.hint)
        except SystemExit:
            raise
        except KeyboardInterrupt:
            die("Interrupted.", code=130)
        except Exception as exc:  # noqa: BLE001
            if os.environ.get("ECHO_CLI_DEBUG", "").strip() in {"1", "true", "yes"}:
                traceback.print_exc()
            die(
                f"{type(exc).__name__}: {exc}",
                hint="Re-run with ECHO_CLI_DEBUG=1 for a full traceback.",
            )

    return wrapper


def page_id_for(story_page: int) -> str:
    return f"page_{int(story_page):02d}"


def story_plan_path(project: Path | None = None) -> Path:
    return story_dir(project) / "page-plan.json"


def load_story_plan(*, project: Path | None = None) -> dict[str, Any]:
    path = story_plan_path(project)
    if not path.is_file():
        die(f"Story page plan not found: {path}", hint="Run scripts/setup_project.py first.")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        die(f"Invalid JSON in page-plan.json: {exc.msg}")
    if not isinstance(data, dict) or "pages" not in data:
        die("page-plan.json must be an object with a 'pages' array.")
    return data


def save_story_plan(data: dict[str, Any], *, project: Path | None = None) -> Path:
    path = story_plan_path(project)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def get_story_page(story_page: int, *, project: Path | None = None) -> dict[str, Any]:
    plan = load_story_plan(project=project)
    for page in plan.get("pages", []):
        if int(page.get("story_page", -1)) == int(story_page):
            return page
    die(
        f"Story page {story_page} not found in page-plan.json.",
        hint=f"Valid range is typically 1–{STORY_PAGE_COUNT}.",
    )
    raise AssertionError  # unreachable


def adapt_story_page(raw: dict[str, Any]) -> PageEntry:
    """Map editorial page-plan entry -> echo PageEntry (extra fields preserved)."""
    sp = int(raw["story_page"])
    panel_count = int(raw.get("suggested_panel_count") or 1)
    layout = str(panel_count) if panel_count >= 1 else "1"
    dialogue = raw.get("dialogue") or []
    if isinstance(dialogue, str):
        dialogue = [dialogue]
    caption = raw.get("caption") or ""
    panels: list[PanelPlan] = []
    if panel_count == 1:
        panels = [
            PanelPlan(
                id=f"p{sp}_1",
                description=str(raw.get("action") or raw.get("story_purpose") or ""),
                dialogue=list(dialogue),
                captions=[caption] if caption else [],
                camera=str(raw.get("camera_notes") or ""),
                emotion=str(raw.get("emotion") or ""),
                characters=list(raw.get("characters") or []),
                location=raw.get("location"),
                objects=list(raw.get("objects") or []),
            )
        ]
    else:
        for i in range(1, panel_count + 1):
            panels.append(
                PanelPlan(
                    id=f"p{sp}_{i}",
                    description=str(raw.get("action") or ""),
                    dialogue=list(dialogue) if i == 1 else [],
                    captions=[caption] if caption and i == 1 else [],
                    camera=str(raw.get("camera_notes") or ""),
                    emotion=str(raw.get("emotion") or ""),
                    characters=list(raw.get("characters") or []),
                    location=raw.get("location"),
                    objects=list(raw.get("objects") or []),
                )
            )

    known = {
        "story_page",
        "scene",
        "chapter",
        "action",
        "story_purpose",
        "suggested_panel_count",
        "camera_notes",
        "dialogue",
        "caption",
        "characters",
        "location",
        "objects",
        "emotion",
        "art_status",
        "continuity_from_previous",
        "continuity_for_next",
    }
    extra = {k: v for k, v in raw.items() if k not in known}
    extra.update(
        {
            "chapter": raw.get("chapter"),
            "scene": raw.get("scene"),
            "action": raw.get("action"),
            "story_purpose": raw.get("story_purpose"),
            "caption": caption,
            "dialogue": dialogue,
            "continuity_from_previous": raw.get("continuity_from_previous", []),
            "continuity_for_next": raw.get("continuity_for_next", []),
            "art_status": raw.get("art_status", "PLANNED"),
            "suggested_panel_count": panel_count,
        }
    )
    return PageEntry(
        id=page_id_for(sp),
        story_page=sp,
        title=str(raw.get("scene") or raw.get("chapter") or f"Page {sp}"),
        summary=str(raw.get("action") or raw.get("story_purpose") or ""),
        layout=layout,
        panels=panels,
        characters=list(raw.get("characters") or []),
        location=raw.get("location"),
        objects=list(raw.get("objects") or []),
        emotion=str(raw.get("emotion") or ""),
        camera=str(raw.get("camera_notes") or ""),
        notes=str(caption),
        extra=extra,
    )


def to_echo_page_plan(*, project: Path | None = None) -> PagePlan:
    raw = load_story_plan(project=project)
    version_raw = raw.get("version", 1)
    try:
        version = int(str(version_raw).split(".")[0])
    except ValueError:
        version = 1
    pages = [adapt_story_page(p) for p in raw.get("pages", [])]
    return PagePlan(
        version=version,
        title=str(raw.get("title") or "Echo of the Inkwell"),
        front_matter_pages=int(raw.get("front_matter_pages") or 0),
        blank_reverse_pages=bool(raw.get("blank_reverse_pages", True)),
        pages=pages,
    )


_COMPAT_INSTALLED = False


def install_page_plan_compat() -> None:
    """Monkeypatch ``load_page_plan`` so echo APIs accept editorial story JSON."""
    global _COMPAT_INSTALLED
    if _COMPAT_INSTALLED:
        return
    import echo.story.page_plan as page_plan_mod

    original = page_plan_mod.load_page_plan

    def _compatible_load(*, root: Path | None = None) -> PagePlan:
        try:
            return original(root=root)
        except Exception:
            return to_echo_page_plan(project=root)

    page_plan_mod.load_page_plan = _compatible_load  # type: ignore[assignment]
    _COMPAT_INSTALLED = True


def load_character_bible(slug: str, *, project: Path | None = None) -> dict[str, Any]:
    project = project or root()
    cdir = project / "characters" / slug
    for name in ("bible.json", "character-bible.json"):
        path = cdir / name
        if path.is_file():
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
    return {"slug": slug, "text": "", "notes": "No bible file present."}


def load_character_continuity(slug: str, *, project: Path | None = None) -> dict[str, Any]:
    project = project or root()
    path = project / "characters" / slug / "continuity.json"
    if not path.is_file():
        die(f"Continuity file missing for character '{slug}': {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def save_character_continuity(
    slug: str,
    data: dict[str, Any],
    *,
    project: Path | None = None,
) -> Path:
    project = project or root()
    path = project / "characters" / slug / "continuity.json"
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def missing_reference_slots(continuity: dict[str, Any]) -> dict[str, dict[str, Any]]:
    slots = continuity.get("reference_slots") or {}
    return {
        name: slot
        for name, slot in slots.items()
        if str(slot.get("status", "MISSING")).upper() == ReferenceStatus.MISSING.value
    }


def resolve_generation_backend(*, project: Path | None = None, prefer_mock: bool | None = None):
    """Return ``(backend, name, is_mock)`` preferring mock when configured."""
    project = project or root()
    use_mock = prefer_mock if prefer_mock is not None else mock_generation_enabled(project)
    try:
        gen = get_config("generation", root=project, use_cache=False)
    except Exception:
        gen = {}
    default = str(gen.get("default_backend") or "mock").lower()
    if use_mock or default == "mock":
        backend = get_backend("mock", root=project)
        return backend, "mock", True
    name = default
    backend = get_backend(name, root=project)
    ok, reason = backend.available()
    if not ok:
        if mock_generation_enabled(project) or prefer_mock:
            backend = get_backend("mock", root=project)
            return backend, "mock", True
        die(
            f"Backend '{name}' unavailable: {reason}",
            hint="Set ECHO_MOCK_GENERATION=1 or generation.json use_mock_backend=true.",
        )
    return backend, name, name == "mock"


def generation_dimensions(*, project: Path | None = None) -> tuple[int, int]:
    try:
        gen = get_config("generation", root=project, use_cache=False)
    except Exception:
        gen = {}
    return int(gen.get("width", 2550)), int(gen.get("height", 3300))


def build_page_prompt(
    story_page: int,
    *,
    project: Path | None = None,
    extra_positive: str = "",
    non_production: bool = False,
) -> dict[str, Any]:
    """Build a generation prompt from editorial page-plan + character bible."""
    project = project or root()
    page = get_story_page(story_page, project=project)
    chars = list(page.get("characters") or [])
    char_bits: list[str] = []
    for slug in chars:
        bible = load_character_bible(slug, project=project)
        appearance = (
            bible.get("prompt")
            or bible.get("appearance")
            or _summarize_character_bible(bible)
            or slug
        )
        name = bible.get("name") or slug
        char_bits.append(f"- {name}: {appearance}")

    positive_parts = [
        MASTER_VISUAL_STYLE.strip(),
        COLORING_BOOK_RULES.strip(),
        "CHARACTERS:\n" + "\n".join(char_bits) if char_bits else "",
        f"LOCATION: {page.get('location') or 'unspecified'}",
        f"PAGE: {page_id_for(story_page)} (story page {story_page}). {page.get('scene') or ''}",
        f"SCENE: {page.get('action') or page.get('story_purpose') or ''}",
        f"EMOTION: {page.get('emotion') or ''}",
        f"CAMERA: {page.get('camera_notes') or ''}",
        "CONTINUITY: Match locked references. Keep costume and props consistent.",
        f"Continuity from previous: {page.get('continuity_from_previous') or []}",
    ]
    if non_production:
        positive_parts.append(
            f"LABEL REQUIREMENT: Clearly mark output as {NON_PRODUCTION_LABEL}."
        )
    if extra_positive:
        positive_parts.append(extra_positive.strip())

    width, height = generation_dimensions(project=project)
    try:
        gen = get_config("generation", root=project, use_cache=False)
    except Exception:
        gen = {}

    return {
        "page_id": page_id_for(story_page),
        "panel_id": None,
        "story_page": story_page,
        "positive": "\n\n".join(p for p in positive_parts if p),
        "negative": NEGATIVE_CONSTRAINTS.strip(),
        "reference_assets": [],
        "dimensions": {"width": width, "height": height},
        "model": gen.get("model"),
        "backend": gen.get("default_backend", "mock"),
        "seed": gen.get("seed"),
        "settings": {
            "layout": str(page.get("suggested_panel_count") or 1),
            "guidance_scale": gen.get("guidance_scale", 7.5),
            "num_inference_steps": gen.get("num_inference_steps", 30),
            "coloring_book": True,
            "non_production": non_production,
        },
        "story_context": {
            "action": page.get("action"),
            "caption": page.get("caption"),
            "dialogue": page.get("dialogue"),
            "emotion": page.get("emotion"),
            "chapter": page.get("chapter"),
            "scene": page.get("scene"),
        },
    }


def build_reference_prompt(
    slug: str,
    slot_name: str,
    *,
    project: Path | None = None,
    non_production: bool = True,
) -> str:
    bible = load_character_bible(slug, project=project)
    appearance = (
        bible.get("prompt")
        or bible.get("appearance")
        or _summarize_character_bible(bible)
        or slug
    )
    name = bible.get("name") or slug
    parts = [
        MASTER_VISUAL_STYLE.strip(),
        COLORING_BOOK_RULES.strip(),
        f"Character reference sheet slot: {slot_name}",
        f"Character: {name}",
        str(appearance),
        f"Clean black-and-white line art reference for slot '{slot_name}'.",
        "Single character focus, consistent proportions, no background clutter.",
    ]
    if non_production:
        parts.append(f"Watermark / label: {NON_PRODUCTION_LABEL}")
    return "\n\n".join(parts)


def _summarize_character_bible(bible: dict[str, Any]) -> str:
    bits: list[str] = []
    for key in (
        "face_shape",
        "eye_shape",
        "hairstyle",
        "hair_silhouette",
        "approximate_height",
    ):
        if bible.get(key):
            bits.append(f"{key}: {bible[key]}")
    clothing = bible.get("clothing") or {}
    if isinstance(clothing, dict) and clothing.get("default_outfit"):
        bits.append(f"outfit: {clothing['default_outfit']}")
    jacket = bible.get("jacket_design") or {}
    if isinstance(jacket, dict) and jacket.get("type"):
        bits.append(f"jacket: {jacket['type']}")
    if bible.get("text"):
        bits.append(str(bible["text"])[:800])
    return "; ".join(bits)


def gate_open(gate_name: str, *, project: Path | None = None) -> bool:
    state = load_state(root=project)
    try:
        return state.gates.is_open(gate_name)
    except KeyError:
        return False


def count_generation_stats(*, project: Path | None = None) -> dict[str, int]:
    """Count approved / generated / rejected from on-disk state (no false positives)."""
    project = project or root()
    approved = list((project / "approved").glob("**/*"))
    rejected = list((project / "rejected").glob("**/*"))
    approved_n = sum(
        1 for p in approved if p.is_file() and p.suffix.lower() in {".png", ".jpg", ".jpeg"}
    )
    rejected_n = sum(
        1 for p in rejected if p.is_file() and p.suffix.lower() in {".png", ".jpg", ".jpeg"}
    )

    generated_n = 0
    gen_root = project / "generations"
    if gen_root.is_dir():
        for record_json in gen_root.glob("*/record.json"):
            try:
                data = json.loads(record_json.read_text(encoding="utf-8"))
                status = str(data.get("status", "")).upper()
                if status in {ArtStatus.GENERATED.value, ArtStatus.APPROVED.value}:
                    generated_n += 1
            except Exception:
                continue

    return {
        "approved": approved_n,
        "generated": generated_n,
        "rejected": rejected_n,
        "remaining": max(0, STORY_PAGE_COUNT - approved_n),
        "target_pages": STORY_PAGE_COUNT,
    }


def progress_stage_status(*, project: Path | None = None) -> dict[str, str]:
    """Derive honest pipeline stage statuses from files (not optimistic defaults)."""
    project = project or root()
    state = load_state(root=project)
    stats = count_generation_stats(project=project)

    story_bible = project / "story" / "story-bible.json"
    page_plan = project / "story" / "page-plan.json"
    kaito_cont = project / "characters" / "kaito" / "continuity.json"
    refs = list((project / "characters" / "kaito" / "references").glob("*.png"))
    reports_print = project / "reports" / "print-validation.json"
    kdp_preview = list((project / "kdp" / "previews").glob("*.pdf"))
    kdp_final = list((project / "kdp" / "final").glob("*.pdf"))

    def stage(done: bool, started: bool) -> str:
        if done:
            return "complete"
        if started:
            return "in_progress"
        return "not_started"

    kaito_gate = state.gates.kaito_reference_approved
    ref_statuses: list[str] = []
    if kaito_cont.is_file():
        cont = json.loads(kaito_cont.read_text(encoding="utf-8"))
        for slot in (cont.get("reference_slots") or {}).values():
            ref_statuses.append(str(slot.get("status", "MISSING")).upper())

    all_refs_approved = bool(ref_statuses) and all(
        s in {"APPROVED", "LOCKED"} for s in ref_statuses
    )
    any_ref_generated = any(s == "GENERATED" for s in ref_statuses) or bool(refs)

    page_count = 0
    if page_plan.is_file():
        page_count = len(load_story_plan(project=project).get("pages", []))

    return {
        "Story Bible": stage(story_bible.is_file(), story_bible.is_file()),
        "Character Refs": stage(
            kaito_gate or all_refs_approved, any_ref_generated or bool(ref_statuses)
        ),
        "Page Planning": stage(page_count >= STORY_PAGE_COUNT, page_plan.is_file()),
        "Generation": stage(stats["generated"] >= STORY_PAGE_COUNT, stats["generated"] > 0),
        "Review": stage(
            stats["approved"] > 0 and stats["remaining"] == 0, stats["generated"] > 0
        ),
        "Approval": stage(stats["approved"] >= STORY_PAGE_COUNT, stats["approved"] > 0),
        "Composition": stage(
            any((project / "pages").glob("*.png")),
            any((project / "pages").glob("*.png")),
        ),
        "Print Validation": stage(
            reports_print.is_file()
            and json.loads(reports_print.read_text(encoding="utf-8")).get("print_ready")
            is True,
            reports_print.is_file(),
        ),
        "KDP Export": stage(bool(kdp_final), bool(kdp_preview) or bool(kdp_final)),
    }
