from __future__ import annotations

from pathlib import Path

import pytest

from bpdpmanager.models import Student, Thesis
from bpdpmanager.models.enums import ThesisStatus, ThesisType
from bpdpmanager.services import ThesisService
from bpdpmanager.services.thesis_service import TransitionError
from bpdpmanager.storage import Database, JsonRepository


@pytest.fixture
def repo(tmp_path: Path) -> JsonRepository:
    return JsonRepository(path=tmp_path / "db.json", backup_path=tmp_path / "db.json.bak")


def test_creates_db_on_first_load(repo: JsonRepository) -> None:
    db = repo.load()
    assert isinstance(db, Database)
    assert db.version == 1
    assert "NSWI-P" in db.obory
    assert repo.path.exists()


def test_roundtrip_thesis(repo: JsonRepository) -> None:
    service = ThesisService(repo)
    student = Student(first_name="Jan", last_name="Vzorník", obor="NSWI-P")
    service.upsert_student(student)

    thesis = Thesis(
        type=ThesisType.BP,
        academic_year="2025/2026",
        student_id=student.id,
        title_cs="Testovací téma",
        annotation="Testovací anotace.",
    )
    service.upsert_thesis(thesis)

    service.reload()
    loaded = service.get_thesis(thesis.id)
    assert loaded is not None
    assert loaded.title_cs == "Testovací téma"
    assert loaded.student_id == student.id


def test_transition_requires_listing_fields(repo: JsonRepository) -> None:
    service = ThesisService(repo)
    thesis = Thesis(type=ThesisType.BP, academic_year="2025/2026", status=ThesisStatus.RESERVED)
    service.upsert_thesis(thesis)

    with pytest.raises(TransitionError):
        service.transition(thesis.id, ThesisStatus.LISTED)

    thesis.title_cs = "Téma"
    thesis.annotation = "Anotace."
    service.upsert_thesis(thesis)
    updated = service.transition(thesis.id, ThesisStatus.LISTED)
    assert updated.status == ThesisStatus.LISTED


def test_transition_requires_full_assignment(repo: JsonRepository) -> None:
    service = ThesisService(repo)
    thesis = Thesis(
        type=ThesisType.DP,
        academic_year="2025/2026",
        status=ThesisStatus.LISTED,
        title_cs="Téma",
        annotation="Anotace.",
    )
    service.upsert_thesis(thesis)

    with pytest.raises(TransitionError):
        service.transition(thesis.id, ThesisStatus.ASSIGNED)

    thesis.title_en = "Topic"
    thesis.objectives = "1. Bod 1"
    thesis.references = "1. Zdroj 1"
    service.upsert_thesis(thesis)
    updated = service.transition(thesis.id, ThesisStatus.ASSIGNED)
    assert updated.status == ThesisStatus.ASSIGNED


def test_disallowed_transition(repo: JsonRepository) -> None:
    service = ThesisService(repo)
    thesis = Thesis(type=ThesisType.BP, academic_year="2025/2026", status=ThesisStatus.INTERESTED)
    service.upsert_thesis(thesis)
    with pytest.raises(TransitionError):
        service.transition(thesis.id, ThesisStatus.DEFENDED)
