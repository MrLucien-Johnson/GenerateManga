#!/usr/bin/env python3
"""Echo of the Inkwell — Streamlit Review Studio + Dashboard."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from _cli_common import (  # noqa: E402
    NON_PRODUCTION_LABEL,
    STORY_PAGE_COUNT,
    build_page_prompt,
    count_generation_stats,
    gate_open,
    get_story_page,
    install_page_plan_compat,
    load_character_bible,
    load_character_continuity,
    load_story_plan,
    page_id_for,
    progress_stage_status,
    resolve_generation_backend,
    root,
    save_story_plan,
)

from echo.continuity.checklist import ContinuityChecklist  # noqa: E402
from echo.core.config import mock_generation_enabled  # noqa: E402
from echo.core.errors import EchoError  # noqa: E402
from echo.core.state import load_state, save_state  # noqa: E402
from echo.generation.metadata import (  # noqa: E402
    create_record,
    list_records_for_page,
)
from echo.core.schemas import ArtStatus  # noqa: E402
from echo.publishing.preflight import run_preflight  # noqa: E402
from echo.review.approval import ApprovalWorkflow  # noqa: E402

install_page_plan_compat()

st.set_page_config(
    page_title="Echo of the Inkwell — Manga Production Studio",
    page_icon="✒️",
    layout="wide",
)


def _project() -> Path:
    return root()


def _latest_record(page_id: str):
    records = list_records_for_page(page_id, root=_project())
    if not records:
        return None
    return sorted(records, key=lambda r: r.created_at)[-1]


def _resolve_image_path(rel_or_abs: str | None) -> Path | None:
    if not rel_or_abs:
        return None
    path = Path(rel_or_abs)
    if path.is_file():
        return path
    candidate = _project() / rel_or_abs
    return candidate if candidate.is_file() else None


def _previous_approved_path(story_page: int) -> Path | None:
    if story_page <= 1:
        return None
    prev_id = page_id_for(story_page - 1)
    approved = _project() / "approved"
    for pattern in (f"{prev_id}*", f"*page_{story_page - 1:02d}*"):
        matches = sorted(approved.glob(pattern))
        files = [p for p in matches if p.suffix.lower() in {".png", ".jpg", ".jpeg"}]
        if files:
            return files[-1]
    return None


def render_dashboard() -> None:
    st.title("Echo of the Inkwell")
    st.subheader("Manga Production Studio")

    project = _project()
    state = load_state(root=project)
    stats = count_generation_stats(project=project)
    stages = progress_stage_status(project=project)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Approved", f"{stats['approved']}/{STORY_PAGE_COUNT}")
    c2.metric("Generated records", stats["generated"])
    c3.metric("Remaining", stats["remaining"])
    c4.metric("Rejected", stats["rejected"])
    c5.metric("Current page", state.current_page_id or "—")

    st.markdown("### Pipeline progress")
    for name, status in stages.items():
        if status == "complete":
            st.success(f"{name}: complete")
        elif status == "in_progress":
            st.info(f"{name}: in progress")
        else:
            st.write(f"{name}: not started")

    st.markdown("### Gates & backend")
    g1, g2, g3, g4 = st.columns(4)
    g1.write(f"KAITO_REFERENCE_APPROVED: `{state.gates.kaito_reference_approved}`")
    g2.write(f"PILOT_APPROVED: `{state.gates.pilot_approved}`")
    g3.write(f"PDF_READY: `{state.gates.pdf_ready}`")
    try:
        backend, name, is_mock = resolve_generation_backend(project=project)
        ok, reason = backend.available()
        g4.write(f"Backend: `{name}` available={ok} mock_cfg={mock_generation_enabled(project)}")
        st.caption(reason)
    except SystemExit as exc:
        g4.write("Backend: unavailable")
        st.caption(str(exc))


def render_review() -> None:
    project = _project()
    if "review_page" not in st.session_state:
        st.session_state.review_page = 1

    nav1, nav2, nav3 = st.columns([1, 2, 1])
    with nav1:
        if st.button("← PREV", use_container_width=True):
            st.session_state.review_page = max(1, st.session_state.review_page - 1)
    with nav3:
        if st.button("NEXT →", use_container_width=True):
            st.session_state.review_page = min(STORY_PAGE_COUNT, st.session_state.review_page + 1)
    with nav2:
        st.session_state.review_page = st.number_input(
            "Story page",
            min_value=1,
            max_value=STORY_PAGE_COUNT,
            value=int(st.session_state.review_page),
            step=1,
        )

    story_page = int(st.session_state.review_page)
    page_id = page_id_for(story_page)
    st.header(f"Review — Page {story_page} of {STORY_PAGE_COUNT}")
    st.caption(f"page_id=`{page_id}`")

    story = get_story_page(story_page, project=project)
    record = _latest_record(page_id)

    left, right = st.columns([1.2, 1])
    with left:
        img_path = _resolve_image_path(record.output_path if record else None)
        if img_path:
            st.image(str(img_path), caption=f"Candidate — {img_path.name}", use_container_width=True)
            if record and (record.settings or {}).get("non_production"):
                st.warning(NON_PRODUCTION_LABEL)
        else:
            st.info("No generated candidate for this page yet.")

        prev = _previous_approved_path(story_page)
        if prev:
            with st.expander("Previous approved page"):
                st.image(str(prev), use_container_width=True)

    with right:
        st.markdown("#### Story context")
        st.write(f"**Scene:** {story.get('scene')}")
        st.write(f"**Action:** {story.get('action')}")
        st.write(f"**Caption:** {story.get('caption') or '—'}")
        st.write(f"**Dialogue:** {story.get('dialogue') or []}")
        st.write(f"**Emotion:** {story.get('emotion')}")

        if record:
            st.markdown("#### Generation")
            st.write(f"**Record:** `{record.id}`")
            st.write(f"**Model:** {record.model}  **Backend:** {record.backend}")
            st.write(f"**Seed:** {record.seed}  **Status:** {record.status.value}")
            with st.expander("Prompt"):
                st.text(record.positive_prompt[:4000])
        else:
            st.write("No generation record.")

        st.markdown("#### Continuity checklist")
        st.caption("All required items must be checked before APPROVE.")
        if "checklist_ids" not in st.session_state:
            st.session_state.checklist_ids = {}
        key = f"cl_{story_page}"
        checked = set(st.session_state.checklist_ids.get(key, []))
        template = ContinuityChecklist()
        new_checked: list[str] = []
        for item in template.items:
            val = st.checkbox(
                f"[{item.category.value}] {item.description}",
                value=item.id in checked,
                key=f"{key}_{item.id}",
            )
            if val:
                new_checked.append(item.id)
        st.session_state.checklist_ids[key] = new_checked
        checklist = ContinuityChecklist.from_checked_ids(new_checked)

        b1, b2, b3 = st.columns(3)
        b4, b5, b6 = st.columns(3)

        if b1.button("APPROVE", type="primary", use_container_width=True):
            if not record:
                st.error("Nothing to approve.")
            elif not checklist.is_complete():
                missing = [i.id for i in checklist.required_incomplete()]
                st.error(f"Complete continuity checklist first. Missing: {', '.join(missing)}")
            else:
                try:
                    approved = ApprovalWorkflow(root=project).approve(
                        record.id,
                        dest_name=f"{page_id}.png",
                    )
                    state = load_state(root=project)
                    state.current_page_id = page_id
                    save_state(state, root=project)
                    st.success(f"Approved → {approved.approved_path}")
                except EchoError as exc:
                    st.error(exc.user_message)

        if b2.button("REGENERATE", use_container_width=True):
            _run_regenerate(story_page, record)

        if b3.button("GENERATE VARIATIONS", use_container_width=True):
            _run_variations(story_page, record)

        if b4.button("EDIT PROMPT", use_container_width=True):
            st.session_state[f"edit_prompt_{story_page}"] = True

        if b5.button("REJECT", use_container_width=True):
            if not record:
                st.error("Nothing to reject.")
            else:
                reason = st.session_state.get(f"reject_reason_{story_page}", "Rejected in Review Studio")
                try:
                    ApprovalWorkflow(root=project).reject(record.id, reason=reason)
                    st.warning("Rejected.")
                except EchoError as exc:
                    st.error(exc.user_message)

        if b6.button("COMPARE", use_container_width=True):
            st.session_state[f"compare_{story_page}"] = True

        if st.session_state.get(f"edit_prompt_{story_page}"):
            edited = st.text_area(
                "Edit positive prompt",
                value=(record.positive_prompt if record else build_page_prompt(story_page)["positive"]),
                height=200,
            )
            if st.button("Save prompt edit & regenerate"):
                _run_regenerate(story_page, record, extra_prompt=edited, replace_prompt=True)
                st.session_state[f"edit_prompt_{story_page}"] = False

        st.text_input("Reject reason", key=f"reject_reason_{story_page}", value="Continuity / quality")

        if st.session_state.get(f"compare_{story_page}"):
            records = list_records_for_page(page_id, root=project)
            st.markdown("#### Compare candidates")
            cols = st.columns(min(3, max(1, len(records))))
            for idx, rec in enumerate(sorted(records, key=lambda r: r.created_at)[-3:]):
                path = _resolve_image_path(rec.output_path)
                with cols[idx % len(cols)]:
                    st.caption(f"{rec.id[:8]}… seed={rec.seed} {rec.status.value}")
                    if path:
                        st.image(str(path), use_container_width=True)


def _run_regenerate(story_page: int, parent, extra_prompt: str = "", replace_prompt: bool = False) -> None:
    project = _project()
    gate_ok = gate_open("KAITO_REFERENCE_APPROVED", project=project)
    non_production = not gate_ok
    page_id = page_id_for(story_page)
    payload = build_page_prompt(story_page, project=project, non_production=non_production)
    positive = extra_prompt if replace_prompt and extra_prompt else payload["positive"]
    if extra_prompt and not replace_prompt:
        positive = f"{positive}\n\n{extra_prompt}"
    backend, name, _ = resolve_generation_backend(project=project, prefer_mock=True)
    width, height = 1024, 1320
    out = project / "generations" / "pages" / page_id / f"{page_id}_regen_ui.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    result = backend.generate(
        prompt=positive,
        negative_prompt=payload["negative"],
        width=width,
        height=height,
        output_path=out,
    )
    if not result.success:
        st.error(result.error or "Regenerate failed")
        return
    rel = str(Path(result.output_path).resolve().relative_to(project.resolve()))
    create_record(
        page_id=page_id,
        backend=name,
        model=result.model,
        seed=result.seed,
        positive_prompt=positive,
        negative_prompt=payload["negative"],
        width=width,
        height=height,
        output_path=rel,
        status=ArtStatus.GENERATED,
        parent_id=parent.id if parent else None,
        settings={"non_production": non_production, "via": "streamlit"},
        root=project,
    )
    st.success(f"Regenerated seed={result.seed}")
    st.rerun()


def _run_variations(story_page: int, parent) -> None:
    project = _project()
    gate_ok = gate_open("KAITO_REFERENCE_APPROVED", project=project)
    non_production = not gate_ok
    page_id = page_id_for(story_page)
    payload = build_page_prompt(story_page, project=project, non_production=non_production)
    backend, name, _ = resolve_generation_backend(project=project, prefer_mock=True)
    for i in range(3):
        out = project / "generations" / "pages" / page_id / f"{page_id}_var_{i + 1}.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        result = backend.generate(
            prompt=payload["positive"] + f"\n\nVariation {i + 1}",
            negative_prompt=payload["negative"],
            width=1024,
            height=1320,
            seed=None,
            output_path=out,
        )
        if result.success and result.output_path:
            rel = str(Path(result.output_path).resolve().relative_to(project.resolve()))
            create_record(
                page_id=page_id,
                backend=name,
                model=result.model,
                seed=result.seed,
                positive_prompt=payload["positive"],
                negative_prompt=payload["negative"],
                width=1024,
                height=1320,
                output_path=rel,
                status=ArtStatus.GENERATED,
                parent_id=parent.id if parent else None,
                settings={"variation": i + 1, "non_production": non_production},
                root=project,
            )
    st.success("Generated 3 variations.")
    st.rerun()


def render_story_editor() -> None:
    project = _project()
    plan = load_story_plan(project=project)
    pages = plan.get("pages") or []
    page_nums = [int(p["story_page"]) for p in pages]
    story_page = st.selectbox("Story page", page_nums, index=0)
    page = next(p for p in pages if int(p["story_page"]) == story_page)

    st.header(f"Story Editor — Page {story_page}")
    approved_exists = bool(list((project / "approved").glob(f"{page_id_for(story_page)}*")))
    if approved_exists:
        st.warning(
            "This page has approved art. Material story changes will NOT silently invalidate "
            "the approval — you must deliberately re-review / regenerate."
        )

    action = st.text_area("Action", value=str(page.get("action") or ""), height=100)
    caption = st.text_area("Caption", value=str(page.get("caption") or ""), height=60)
    dialogue_raw = st.text_area(
        "Dialogue (one line per balloon)",
        value="\n".join(page.get("dialogue") or []),
        height=100,
    )
    emotion = st.text_input("Emotion", value=str(page.get("emotion") or ""))
    panel_count = st.number_input(
        "Panel count",
        min_value=1,
        max_value=6,
        value=int(page.get("suggested_panel_count") or 1),
    )
    continuity_notes = st.text_area(
        "Continuity notes (for next)",
        value=", ".join(page.get("continuity_for_next") or []),
        height=60,
    )

    if st.button("Save story page", type="primary"):
        material = (
            action.strip() != str(page.get("action") or "").strip()
            or emotion.strip() != str(page.get("emotion") or "").strip()
            or int(panel_count) != int(page.get("suggested_panel_count") or 1)
        )
        if approved_exists and material:
            st.error(
                "Material change on an approved page. "
                "Save aborted to prevent silent invalidation. "
                "Unapprove / regenerate deliberately, then re-save, or confirm below."
            )
            if st.checkbox("I understand — apply material change without auto-invalidating approval"):
                _apply_story_edit(
                    plan,
                    story_page,
                    action,
                    caption,
                    dialogue_raw,
                    emotion,
                    panel_count,
                    continuity_notes,
                    project,
                )
                st.warning("Saved. Approved art was NOT removed — re-review required.")
        else:
            _apply_story_edit(
                plan,
                story_page,
                action,
                caption,
                dialogue_raw,
                emotion,
                panel_count,
                continuity_notes,
                project,
            )
            st.success("Saved.")


def _apply_story_edit(
    plan,
    story_page,
    action,
    caption,
    dialogue_raw,
    emotion,
    panel_count,
    continuity_notes,
    project,
) -> None:
    for page in plan["pages"]:
        if int(page["story_page"]) == int(story_page):
            page["action"] = action
            page["caption"] = caption
            page["dialogue"] = [ln.strip() for ln in dialogue_raw.splitlines() if ln.strip()]
            page["emotion"] = emotion
            page["suggested_panel_count"] = int(panel_count)
            page["continuity_for_next"] = [
                p.strip() for p in continuity_notes.split(",") if p.strip()
            ]
            break
    save_story_plan(plan, project=project)


def render_continuity() -> None:
    project = _project()
    st.header("Continuity / References — Kaito")
    cont = load_character_continuity("kaito", project=project)
    bible = load_character_bible("kaito", project=project)
    st.write(f"**Name:** {bible.get('name', 'Kaito')}")
    st.write(f"**Gate in continuity:** {cont.get('production_gate')}")
    state = load_state(root=project)
    st.write(f"**State KAITO_REFERENCE_APPROVED:** `{state.gates.kaito_reference_approved}`")

    slots = cont.get("reference_slots") or {}
    rows = []
    for name, slot in slots.items():
        rows.append(
            {
                "slot": name,
                "filename": slot.get("filename"),
                "status": slot.get("status"),
                "path": slot.get("path"),
            }
        )
    st.dataframe(rows, use_container_width=True)

    ref_dir = project / "characters" / "kaito" / "references"
    images = sorted(ref_dir.glob("*.png"))
    if images:
        cols = st.columns(3)
        for i, img in enumerate(images):
            with cols[i % 3]:
                st.image(str(img), caption=img.name, use_container_width=True)
    else:
        st.info("No reference PNGs on disk yet. Run scripts/generate_reference.py kaito")


def render_preflight() -> None:
    st.header("Preflight")
    if st.button("Run preflight now"):
        report = run_preflight(root=_project(), write_report=True)
        st.session_state["preflight_report"] = report
    report = st.session_state.get("preflight_report")
    path = _project() / "reports" / "preflight.json"
    if report is None and path.is_file():
        report = json.loads(path.read_text(encoding="utf-8"))
    if not report:
        st.info("No preflight report yet.")
        return
    st.metric("PDF_READY", report.get("PDF_READY", "NO"))
    st.json(report)


def main() -> None:
    st.sidebar.title("Echo Studio")
    page = st.sidebar.radio(
        "Navigate",
        ["Dashboard", "Review", "Story Editor", "Continuity / References", "Preflight"],
    )
    if page == "Dashboard":
        render_dashboard()
    elif page == "Review":
        render_review()
    elif page == "Story Editor":
        render_story_editor()
    elif page == "Continuity / References":
        render_continuity()
    else:
        render_preflight()


if __name__ == "__main__":
    main()
