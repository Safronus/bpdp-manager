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
    assert db.version >= 1  # auto-bump na aktuální SCHEMA_VERSION
    assert "NSWI-P" in {o.name for o in db.obory}
    assert repo.path.exists()


def test_save_survives_backup_failure(repo: JsonRepository, monkeypatch) -> None:
    """Selhání .bak zálohy (např. iCloud offload → timeout) nesmí shodit zápis."""
    import shutil

    db = repo.load()                       # vytvoří db.json
    monkeypatch.setattr(shutil, "copy2",
                        lambda *a, **k: (_ for _ in ()).throw(
                            TimeoutError(60, "Operation timed out")))
    repo.save(db)                          # nesmí vyhodit výjimku
    assert repo.path.exists()
    assert repo.load().version == db.version   # data se opravdu zapsala


def test_migrate_survives_save_failure(tmp_path, monkeypatch) -> None:
    """Načtení staršího schématu nespadne, když zápis bumpu verze selže."""
    import json
    import shutil

    p = tmp_path / "db.json"
    base = JsonRepository(path=p, backup_path=tmp_path / "db.json.bak")
    base.load()                            # vytvoří db.json
    data = json.loads(p.read_text(encoding="utf-8"))
    data["version"] = 1                    # podvrhni starou verzi
    p.write_text(json.dumps(data), encoding="utf-8")

    monkeypatch.setattr(shutil, "copy2",
                        lambda *a, **k: (_ for _ in ()).throw(OSError("offload")))
    repo2 = JsonRepository(path=p, backup_path=tmp_path / "db.json.bak")
    loaded = repo2.load()                  # load → _migrate → save (copy2 padá)
    assert loaded.version >= 1             # nespadlo


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
    """v0.15.0: ASSIGNED bylo sloučeno do IN_PROGRESS. Stejné požadavky platí
    pro vstup do IN_PROGRESS — titul EN, body zadání, literatura."""
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
        service.transition(thesis.id, ThesisStatus.IN_PROGRESS)

    thesis.title_en = "Topic"
    thesis.objectives = "1. Bod 1"
    thesis.references = "1. Zdroj 1"
    service.upsert_thesis(thesis)
    updated = service.transition(thesis.id, ThesisStatus.IN_PROGRESS)
    assert updated.status == ThesisStatus.IN_PROGRESS


def test_disallowed_transition(repo: JsonRepository) -> None:
    service = ThesisService(repo)
    thesis = Thesis(type=ThesisType.BP, academic_year="2025/2026", status=ThesisStatus.INTERESTED)
    service.upsert_thesis(thesis)
    with pytest.raises(TransitionError):
        service.transition(thesis.id, ThesisStatus.DEFENDED)
