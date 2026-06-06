"""Testy repetent — bezpečný dedup (nepřepisovat jiné adipidno) + auto-vazba."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from bpdpmanager.models import OpposingThesis, Student, Thesis  # noqa: E402
from bpdpmanager.models.enums import ThesisStatus, ThesisType  # noqa: E402
from bpdpmanager.services import ThesisService  # noqa: E402
from bpdpmanager.services.stag_csv_importer import ImportRole, ParsedRecord  # noqa: E402
from bpdpmanager.storage import JsonRepository  # noqa: E402
from bpdpmanager.ui.stag_import_dialog import StagImportDialog  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    yield QApplication.instance() or QApplication([])


@pytest.fixture
def service(tmp_path: Path) -> ThesisService:
    repo = JsonRepository(path=tmp_path / "db.json", backup_path=tmp_path / "db.json.bak")
    return ThesisService(repo)


def test_dedup_does_not_overwrite_different_adipidno(qapp, service: ThesisService) -> None:
    student = Student(first_name="Jan", last_name="Novák", university_id="A1")
    service.upsert_student(student)
    # Řádný pokus (neobhájeno) s vlastním STAG ID.
    t1 = Thesis(type=ThesisType.BP, academic_year="2024/2025", student_id=student.id,
                status=ThesisStatus.CANCELLED, adipidno="X1")
    service.upsert_thesis(t1)

    dlg = StagImportDialog(service)
    # Opravný pokus = jiné STAG ID, stejný student/rok/typ.
    rec = ParsedRecord(role=ImportRole.SUPERVISOR, raw={})
    rec.adipidno = "X2"
    rec.academic_year = "2024/2025"
    rec.type_code = "BP"
    rec.student_uni_id = "A1"
    # NESMÍ napárovat na t1 (jiné adipidno) → vznikne nová práce.
    assert dlg._find_existing_thesis(student.id, rec) is None

    # Naopak stejné adipidno → napáruje (aktualizace).
    rec.adipidno = "X1"
    assert dlg._find_existing_thesis(student.id, rec) is t1


def test_auto_link_theses(service: ThesisService) -> None:
    s = Student(first_name="A", last_name="B", university_id="A1")
    service.upsert_student(s)
    t1 = Thesis(type=ThesisType.BP, academic_year="2024/2025", student_id=s.id,
                status=ThesisStatus.CANCELLED, adipidno="X1")
    t2 = Thesis(type=ThesisType.BP, academic_year="2024/2025", student_id=s.id,
                status=ThesisStatus.DEFENDED, adipidno="X2")
    service.upsert_thesis(t1)
    service.upsert_thesis(t2)
    assert service.auto_link_retakes() == 1
    assert service.get_thesis(t1.id).related_thesis_id == t2.id
    assert service.get_thesis(t2.id).related_thesis_id == t1.id
    assert service.auto_link_retakes() == 0  # idempotentní


def test_auto_link_opposing(service: ThesisService) -> None:
    o1 = OpposingThesis(type=ThesisType.DP, academic_year="2024/2025",
                        student_university_id="B2", adipidno="Y1")
    o2 = OpposingThesis(type=ThesisType.DP, academic_year="2024/2025",
                        student_university_id="B2", adipidno="Y2")
    service.upsert_opposing_thesis(o1)
    service.upsert_opposing_thesis(o2)
    assert service.auto_link_retakes() == 1
    assert service.get_opposing_thesis(o1.id).related_thesis_id == o2.id
