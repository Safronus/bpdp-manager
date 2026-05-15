from __future__ import annotations

from pathlib import Path

import pytest

from bpdpmanager.models import Opponent, Student, Thesis
from bpdpmanager.models.enums import AttachmentKind, OpponentKind, ThesisType
from bpdpmanager.services import ThesisService
from bpdpmanager.storage import JsonRepository


@pytest.fixture
def service(tmp_path: Path) -> ThesisService:
    repo = JsonRepository(path=tmp_path / "db.json", backup_path=tmp_path / "db.json.bak")
    return ThesisService(repo)


# --- obory --------------------------------------------------------------------


def test_add_and_list_obor(service: ThesisService) -> None:
    initial = set(service.list_obory())
    service.add_obor("CUST-X")
    assert "CUST-X" in service.list_obory()
    assert set(service.list_obory()) == initial | {"CUST-X"}


def test_rename_obor_updates_students(service: ThesisService, tmp_path: Path) -> None:
    student = Student(first_name="Jan", last_name="Vzor", obor="NSWI-P")
    service.upsert_student(student)
    count = service.rename_obor("NSWI-P", "NSWI-PRESENCNI")
    assert count == 1
    refreshed = service.get_student(student.id)
    assert refreshed is not None and refreshed.obor == "NSWI-PRESENCNI"


def test_remove_obor_clears_students(service: ThesisService) -> None:
    student = Student(first_name="Eva", last_name="Test", obor="NSWI-P")
    service.upsert_student(student)
    count = service.remove_obor("NSWI-P")
    assert count == 1
    refreshed = service.get_student(student.id)
    assert refreshed is not None and refreshed.obor == ""
    assert "NSWI-P" not in service.list_obory()


# --- oponenti -----------------------------------------------------------------


def test_opponent_kind_defaults_to_internal(service: ThesisService) -> None:
    opp = Opponent(name="Test")
    assert opp.kind == OpponentKind.INTERNAL
    assert not opp.is_external


def test_filter_opponents_by_kind(service: ThesisService) -> None:
    service.upsert_opponent(Opponent(name="Interní 1", kind=OpponentKind.INTERNAL))
    service.upsert_opponent(Opponent(name="Externí 1", kind=OpponentKind.EXTERNAL))
    service.upsert_opponent(Opponent(name="Externí 2", kind=OpponentKind.EXTERNAL))

    internals = service.list_opponents(kind=OpponentKind.INTERNAL)
    externals = service.list_opponents(kind=OpponentKind.EXTERNAL)
    assert len(internals) == 1
    assert len(externals) == 2
    assert all(o.kind == OpponentKind.INTERNAL for o in internals)
    assert all(o.kind == OpponentKind.EXTERNAL for o in externals)


def test_external_opponent_keeps_address_and_phone(service: ThesisService) -> None:
    opp = Opponent(
        name="Externí",
        kind=OpponentKind.EXTERNAL,
        phone="+420 123 456 789",
        address="Demo 1, Zlín",
    )
    service.upsert_opponent(opp)
    service.reload()
    refreshed = service.get_opponent(opp.id)
    assert refreshed is not None
    assert refreshed.phone == "+420 123 456 789"
    assert refreshed.address == "Demo 1, Zlín"


# --- dokumenty ----------------------------------------------------------------


def test_attach_document_copies_file_and_appends(service: ThesisService, tmp_path: Path) -> None:
    thesis = Thesis(type=ThesisType.BP, academic_year="2025/2026")
    service.upsert_thesis(thesis)

    source = tmp_path / "posudek.pdf"
    source.write_bytes(b"%PDF-1.4 fake pdf content\n")

    attachment = service.attach_document(
        thesis.id,
        source,
        kind=AttachmentKind.SUPERVISOR_REVIEW,
        label="Posudek vedoucího",
    )
    assert attachment.kind == AttachmentKind.SUPERVISOR_REVIEW
    assert attachment.is_file

    target = service.document_absolute_path(thesis.id, attachment)
    assert target is not None
    assert target.exists()
    assert target.read_bytes() == source.read_bytes()

    refreshed = service.get_thesis(thesis.id)
    assert refreshed is not None
    assert len(refreshed.attachments) == 1


def test_attach_document_uniquifies_filename(service: ThesisService, tmp_path: Path) -> None:
    thesis = Thesis(type=ThesisType.BP, academic_year="2025/2026")
    service.upsert_thesis(thesis)

    source = tmp_path / "posudek.pdf"
    source.write_bytes(b"a")

    a1 = service.attach_document(thesis.id, source, kind=AttachmentKind.SUPERVISOR_REVIEW)
    a2 = service.attach_document(thesis.id, source, kind=AttachmentKind.OPPONENT_REVIEW)
    assert a1.url_or_path != a2.url_or_path


def test_remove_document_with_delete_file(service: ThesisService, tmp_path: Path) -> None:
    thesis = Thesis(type=ThesisType.BP, academic_year="2025/2026")
    service.upsert_thesis(thesis)
    source = tmp_path / "doc.pdf"
    source.write_bytes(b"x")
    attachment = service.attach_document(thesis.id, source, kind=AttachmentKind.OTHER)
    target = service.document_absolute_path(thesis.id, attachment)
    assert target is not None and target.exists()

    service.remove_document(thesis.id, 0, delete_file=True)
    assert not target.exists()
    refreshed = service.get_thesis(thesis.id)
    assert refreshed is not None and refreshed.attachments == []
