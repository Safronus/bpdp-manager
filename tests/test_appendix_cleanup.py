"""Úklid duplicitních příloh: detekce + smazání podle shodného obsahu."""

from __future__ import annotations

from pathlib import Path

import pytest

from bpdpmanager.models import Student, Thesis
from bpdpmanager.models.enums import AttachmentKind, ThesisStatus, ThesisType
from bpdpmanager.models.thesis import Attachment
from bpdpmanager.services import ThesisService
from bpdpmanager.storage import JsonRepository


@pytest.fixture
def service(tmp_path: Path) -> ThesisService:
    repo = JsonRepository(
        path=tmp_path / "db.json", backup_path=tmp_path / "db.json.bak"
    )
    return ThesisService(repo)


@pytest.fixture
def thesis(service: ThesisService) -> str:
    s = Student(first_name="Dominik", last_name="Fabian")
    service.upsert_student(s)
    t = Thesis(type=ThesisType.DP, status=ThesisStatus.IN_PROGRESS,
               academic_year="2025/2026", student_id=s.id)
    service.upsert_thesis(t)
    return t.id


def _apps(service, tid):
    return [a for a in service.get_thesis(tid).attachments
            if a.kind == AttachmentKind.THESIS_APPENDIX]


def _inject_duplicate(service, tid, src: Path, label: str,
                      kind=AttachmentKind.THESIS_APPENDIX) -> None:
    """Vlož přílohu se shodným obsahem jako `src`, obejdi dedup-na-vstupu."""
    import shutil

    from bpdpmanager.config import thesis_documents_dir

    base = thesis_documents_dir(tid)
    base.mkdir(parents=True, exist_ok=True)
    dest = base / label
    shutil.copy2(src, dest)
    t = service.get_thesis(tid)
    t.attachments.append(Attachment(
        label=label, url_or_path=label,
        kind=kind, is_file=True, version=1, is_current=True,
    ))
    service.upsert_thesis(t)


def test_find_duplicate_flags_identical_content(service, thesis, tmp_path) -> None:
    f = tmp_path / "prilohy.zip"
    f.write_bytes(b"Z" * 4000)
    service.attach_document(thesis, f, kind=AttachmentKind.THESIS_APPENDIX,
                            label="prilohy_2026-06-06.zip")
    _inject_duplicate(service, thesis, f, "prilohy_2026-06-08.zip")
    dups = service.find_duplicate_appendices()
    assert len(dups) == 1
    assert dups[0].work_id == thesis
    assert dups[0].size == 4000


def test_find_duplicate_ignores_different_content(service, thesis, tmp_path) -> None:
    f1 = tmp_path / "a.zip"
    f1.write_bytes(b"A" * 4000)
    f2 = tmp_path / "b.zip"
    f2.write_bytes(b"B" * 4000)  # stejná velikost, jiný obsah
    service.attach_document(thesis, f1, kind=AttachmentKind.THESIS_APPENDIX,
                            label="part1.zip")
    service.attach_document(thesis, f2, kind=AttachmentKind.THESIS_APPENDIX,
                            label="part2.zip")
    assert service.find_duplicate_appendices() == []


def test_find_duplicate_ignores_text_and_reviews(service, thesis, tmp_path) -> None:
    f = tmp_path / "text.pdf"
    f.write_bytes(b"%PDF-1.4 same content")
    service.attach_document(thesis, f, kind=AttachmentKind.THESIS_TEXT,
                            label="text_a.pdf")
    # druhý text se stejným obsahem — cleanup se ho NESMÍ dotknout
    _inject_duplicate(service, thesis, f, "text_b.pdf",
                      kind=AttachmentKind.THESIS_TEXT)
    assert service.find_duplicate_appendices() == []


def test_delete_removes_dup_keeps_one_and_marks_current(service, thesis, tmp_path) -> None:
    f = tmp_path / "prilohy.zip"
    f.write_bytes(b"Z" * 4000)
    service.attach_document(thesis, f, kind=AttachmentKind.THESIS_APPENDIX,
                            label="prilohy_2026-06-06.zip")
    _inject_duplicate(service, thesis, f, "prilohy_2026-06-08.zip")
    dups = service.find_duplicate_appendices()
    items = [(d.work_id, d.is_opposing, d.del_url) for d in dups]
    # soubor duplikátu existuje před smazáním
    dup_abs = service._abs_attachment_path(  # type: ignore[attr-defined]
        thesis,
        next(a for a in _apps(service, thesis) if a.url_or_path == dups[0].del_url),
        opposing=False,
    )
    assert dup_abs.exists()

    removed = service.delete_appendix_duplicates(items)
    assert removed == 1
    apps = _apps(service, thesis)
    assert len(apps) == 1
    assert apps[0].is_current
    assert not dup_abs.exists()           # fyzicky smazán
    assert service.find_duplicate_appendices() == []
