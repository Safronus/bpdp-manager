"""Test ZIP export/import jedné práce (round-trip)."""

from __future__ import annotations

from pathlib import Path

import pytest

from bpdpmanager.models import Obor, Opponent, Student, Thesis
from bpdpmanager.models.enums import AttachmentKind, OpponentKind, ThesisStatus, ThesisType
from bpdpmanager.services import ThesisService
from bpdpmanager.services.thesis_export import (
    ThesisExportError,
    export_thesis_to_zip,
    import_thesis_from_zip,
    read_thesis_zip_manifest,
)
from bpdpmanager.storage import JsonRepository


@pytest.fixture
def service(tmp_path: Path) -> ThesisService:
    repo = JsonRepository(path=tmp_path / "db.json", backup_path=tmp_path / "db.json.bak")
    return ThesisService(repo)


def test_export_import_roundtrip(service: ThesisService, tmp_path: Path) -> None:
    service.upsert_obor(Obor(name="ITA-P", stag_code="pbITA"))
    student = Student(first_name="Jan", last_name="Novák", obor="ITA-P", university_id="A1")
    service.upsert_student(student)
    opp = Opponent(kind=OpponentKind.INTERNAL, name="Ing. Oponent")
    service.upsert_opponent(opp)
    t = Thesis(type=ThesisType.BP, academic_year="2024/2025", student_id=student.id,
               opponent_id=opp.id, status=ThesisStatus.IN_PROGRESS, title_cs="Moje práce",
               grade_supervisor="B")
    service.upsert_thesis(t)
    src = tmp_path / "posudek.pdf"
    src.write_bytes(b"%PDF dummy")
    service.attach_document(t.id, src, kind=AttachmentKind.SUPERVISOR_REVIEW)

    zip_path = tmp_path / "prace.zip"
    stats = export_thesis_to_zip(service, t.id, zip_path)
    assert zip_path.is_file()
    assert stats["files"] == 1

    preview = read_thesis_zip_manifest(zip_path)
    assert preview.export_type == "thesis"
    assert "Moje práce" in preview.title

    # Import do ČISTÉ služby (jiné zařízení/profil).
    repo2 = JsonRepository(path=tmp_path / "db2.json", backup_path=tmp_path / "db2.json.bak")
    svc2 = ThesisService(repo2)
    new_id = import_thesis_from_zip(svc2, zip_path)

    nt = svc2.get_thesis(new_id)
    assert nt is not None
    assert nt.id != t.id  # nová identita
    assert nt.title_cs == "Moje práce"
    assert nt.grade_supervisor == "B"
    assert nt.status == ThesisStatus.IN_PROGRESS
    # student + oponent + obor obnoveny
    st = svc2.get_student(nt.student_id)
    assert st is not None and st.university_id == "A1"
    assert svc2.get_obor("ITA-P") is not None
    assert svc2.get_opponent(nt.opponent_id) is not None
    # soubor posudku se přenesl a existuje
    assert len(nt.attachments) == 1
    p = svc2.document_absolute_path(new_id, nt.attachments[0])
    assert p is not None and p.exists()


def test_import_rejects_non_thesis_zip(service: ThesisService, tmp_path: Path) -> None:
    import zipfile
    bad = tmp_path / "bad.zip"
    with zipfile.ZipFile(bad, "w") as zf:
        zf.writestr("manifest.json", '{"type":"profile"}')
    with pytest.raises(ThesisExportError):
        import_thesis_from_zip(service, bad)
