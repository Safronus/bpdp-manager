"""Verzování příloh: různé soubory koexistují, stejný se verzuje + velikost."""

from __future__ import annotations

from pathlib import Path

import pytest

from bpdpmanager.models import Student, Thesis
from bpdpmanager.models.enums import AttachmentKind, ThesisStatus, ThesisType
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


def test_two_different_appendices_both_current(service, thesis, tmp_path) -> None:
    f1 = tmp_path / "part1.zip"
    f1.write_bytes(b"a" * 100)
    f2 = tmp_path / "part2.zip"
    f2.write_bytes(b"b" * 200)
    service.attach_document(thesis, f1, kind=AttachmentKind.THESIS_APPENDIX,
                            label="code_and_test_cases_part1.zip")
    service.attach_document(thesis, f2, kind=AttachmentKind.THESIS_APPENDIX,
                            label="test_cases_part_2.zip")
    apps = _apps(service, thesis)
    assert len(apps) == 2
    assert all(a.is_current for a in apps)  # obě zůstávají aktuální


def test_reattach_identical_appendix_is_deduped(service, thesis, tmp_path) -> None:
    """Opětovné stažení téhož souboru (shodný obsah) se NEpřidá podruhé."""
    f1 = tmp_path / "p1.zip"
    f1.write_bytes(b"a" * 100)
    f2 = tmp_path / "p2.zip"
    f2.write_bytes(b"b" * 200)
    service.attach_document(thesis, f1, kind=AttachmentKind.THESIS_APPENDIX,
                            label="part1.zip")
    service.attach_document(thesis, f2, kind=AttachmentKind.THESIS_APPENDIX,
                            label="part2.zip")
    # opětovné stažení part1 pod JINÝM cílovým názvem, ale shodný obsah → dedup
    f1b = tmp_path / "p1_again.zip"
    f1b.write_bytes(b"a" * 100)
    service.attach_document(thesis, f1b, kind=AttachmentKind.THESIS_APPENDIX,
                            label="part1_2026-06-08.zip")
    apps = _apps(service, thesis)
    assert len(apps) == 2                                # žádný duplikát nepřibyl
    assert all(a.is_current for a in apps)


def test_reupload_changed_appendix_versions_only_it(service, thesis, tmp_path) -> None:
    """Nový OBSAH pod stejným názvem → nová verze jen té přílohy."""
    f1 = tmp_path / "p1.zip"
    f1.write_bytes(b"a" * 100)
    f2 = tmp_path / "p2.zip"
    f2.write_bytes(b"b" * 200)
    service.attach_document(thesis, f1, kind=AttachmentKind.THESIS_APPENDIX,
                            label="part1.zip")
    service.attach_document(thesis, f2, kind=AttachmentKind.THESIS_APPENDIX,
                            label="part2.zip")
    # part1 se ZMĚNIL (jiný obsah, stejný název) → nová verze JEN u part1
    f1.write_bytes(b"a" * 100 + b"CHANGED")
    service.attach_document(thesis, f1, kind=AttachmentKind.THESIS_APPENDIX,
                            label="part1.zip")
    apps = _apps(service, thesis)
    p1 = [a for a in apps if a.label == "part1.zip"]
    p2 = [a for a in apps if a.label == "part2.zip"]
    assert sorted(a.version for a in p1) == [1, 2]
    assert sum(a.is_current for a in p1) == 1            # jen nová verze part1
    assert len(p2) == 1 and p2[0].is_current             # part2 nedotčen


def test_single_instance_kind_still_supersedes(service, thesis, tmp_path) -> None:
    f1 = tmp_path / "t1.pdf"
    f1.write_bytes(b"%PDF-1")
    f2 = tmp_path / "t2.pdf"
    f2.write_bytes(b"%PDF-2")
    service.attach_document(thesis, f1, kind=AttachmentKind.THESIS_TEXT,
                            label="text_a.pdf")
    service.attach_document(thesis, f2, kind=AttachmentKind.THESIS_TEXT,
                            label="text_b.pdf")
    texts = [a for a in service.get_thesis(thesis).attachments
             if a.kind == AttachmentKind.THESIS_TEXT]
    # text práce je jeden → druhý nahradí první (jen jeden current)
    assert sum(a.is_current for a in texts) == 1


def test_human_size_formatting() -> None:
    from bpdpmanager.ui.widgets.documents_widget import _human_size

    assert _human_size(0) == "0 B"
    assert _human_size(512) == "512 B"
    assert _human_size(1024) == "1.0 KB"
    assert _human_size(2_700_000).endswith(" MB")
    assert _human_size(1_610_612_736).endswith(" GB")
