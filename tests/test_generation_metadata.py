"""Generation metadata create / save / load."""

from __future__ import annotations

from pathlib import Path

from echo.core.schemas import ArtStatus
from echo.generation.metadata import create_record, list_records_for_page, load_record, save_record
from echo.generation.mock_backend import MockGenerationBackend


def test_create_and_reload_record(tmp_project: Path) -> None:
    backend = MockGenerationBackend(root=tmp_project)
    out = tmp_project / "generations" / "meta.png"
    result = backend.generate(prompt="meta", width=64, height=64, seed=11, output_path=out)
    assert result.metadata.get("source_type") == "MOCK"
    record = create_record(
        page_id="p1",
        backend="mock",
        model="mock-lineart",
        seed=result.seed,
        positive_prompt="meta",
        negative_prompt="blurry",
        width=64,
        height=64,
        output_path=result.output_path,
        settings={"test": True},
        root=tmp_project,
    )
    loaded = load_record(record.id, root=tmp_project)
    assert loaded.id == record.id
    assert loaded.seed == 11
    assert loaded.positive_prompt == "meta"
    assert loaded.settings["test"] is True
    assert loaded.source_type.value == "MOCK"
    assert loaded.production_eligible is False
    assert loaded.is_mock()
    assert (tmp_project / "generations" / record.id / "record.json").is_file()


def test_list_records_for_page(tmp_project: Path) -> None:
    create_record(page_id="p1", backend="mock", seed=1, root=tmp_project)
    create_record(page_id="p1", backend="mock", seed=2, root=tmp_project)
    create_record(page_id="p2", backend="mock", seed=3, root=tmp_project)
    page1 = list_records_for_page("p1", root=tmp_project)
    assert len(page1) == 2
    assert all(r.page_id == "p1" for r in page1)


def test_save_updates_status(tmp_project: Path) -> None:
    record = create_record(page_id="p1", backend="mock", root=tmp_project)
    record.status = ArtStatus.REJECTED
    save_record(record, root=tmp_project)
    loaded = load_record(record.id, root=tmp_project)
    assert loaded.status == ArtStatus.REJECTED
