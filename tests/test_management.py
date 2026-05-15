from __future__ import annotations

from pathlib import Path

import pytest

from bpdpmanager.models import Obor, Opponent, Student, Thesis
from bpdpmanager.models.enums import AttachmentKind, OpponentKind, StudyForm, ThesisType
from bpdpmanager.models.student import derive_form_from_obor
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


# --- obory s tajemnicemi -----------------------------------------------------


def test_add_obor_returns_obor_object(service: ThesisService) -> None:
    obor = service.add_obor("NEW-Z")
    assert obor is not None
    assert obor.name == "NEW-Z"
    assert obor.secretary_name is None


def test_upsert_obor_stores_secretary(service: ThesisService) -> None:
    obor = service.add_obor("NEW-Z")
    obor.secretary_name = "Ing. Test Sekretářka"
    obor.secretary_email = "tajemnice@example.com"
    obor.secretary_phone = "+420 111 222 333"
    service.upsert_obor(obor)

    service.reload()
    refreshed = service.get_obor("NEW-Z")
    assert refreshed is not None
    assert refreshed.secretary_name == "Ing. Test Sekretářka"
    assert refreshed.secretary_email == "tajemnice@example.com"
    assert refreshed.secretary_phone == "+420 111 222 333"


def test_list_obor_objects_sorted_by_name(service: ThesisService) -> None:
    service.add_obor("ZULU")
    service.add_obor("ALPHA")
    service.add_obor("MIKE")
    names = [o.name for o in service.list_obor_objects()]
    # default fixture obory don't exist (empty DB), so first three are these
    assert names[:3] == ["ALPHA", "MIKE", "ZULU"]


def test_old_obory_strings_migrate_to_objects(tmp_path) -> None:
    """Stará JSON struktura s obory jako list[str] se musí načíst bez chyby."""
    from bpdpmanager.storage import Database

    db = Database.model_validate(
        {
            "version": 1,
            "obory": ["NSWI-P", "NKYB-K"],
            "students": [],
            "opponents": [],
            "theses": [],
        }
    )
    assert len(db.obory) == 2
    assert all(isinstance(o, Obor) for o in db.obory)
    names = {o.name for o in db.obory}
    assert names == {"NSWI-P", "NKYB-K"}


def test_old_thesis_objectives_list_migrate_to_text() -> None:
    """Staré pole objectives/references jako list[str] se konvertuje na číslovaný text."""
    thesis = Thesis.model_validate(
        {
            "type": "BP",
            "academic_year": "2024/2025",
            "objectives": ["První bod.", "Druhý bod."],
            "references": ["SMITH, J. Title. 2020.", "ANOTHER. Title. 2021."],
        }
    )
    assert thesis.objectives == "1. První bod.\n2. Druhý bod."
    assert thesis.references == "1. SMITH, J. Title. 2020.\n2. ANOTHER. Title. 2021."


# --- forma studia (odvozená z přípony oboru) ---------------------------------


def test_form_derived_from_obor_presential() -> None:
    assert derive_form_from_obor("NSWI-P") == StudyForm.PRESENTIAL
    assert derive_form_from_obor("NKYB-P") == StudyForm.PRESENTIAL
    assert derive_form_from_obor("nswi-p") == StudyForm.PRESENTIAL  # case-insensitive


def test_form_derived_from_obor_combined() -> None:
    assert derive_form_from_obor("NSWI-K") == StudyForm.COMBINED
    assert derive_form_from_obor("NKYB-K") == StudyForm.COMBINED


def test_form_derived_none_when_no_suffix() -> None:
    assert derive_form_from_obor("") is None
    assert derive_form_from_obor(None) is None
    assert derive_form_from_obor("NSWI") is None
    assert derive_form_from_obor("Computer Science") is None


def test_student_form_property_reflects_obor() -> None:
    s = Student(first_name="Jan", last_name="Vzor", obor="NSWI-P")
    assert s.form == StudyForm.PRESENTIAL
    s.obor = "NSWI-K"
    assert s.form == StudyForm.COMBINED
    s.obor = "Custom"
    assert s.form is None


def test_old_form_field_in_json_is_ignored(service: ThesisService) -> None:
    """Načtení staré JSON struktury s 'form' polem nesmí selhat — pole se ignoruje."""
    # simulace načtení starých dat
    s = Student.model_validate(
        {"first_name": "Eva", "last_name": "Stará", "obor": "NSWI-K", "form": "P"}
    )
    assert s.obor == "NSWI-K"
    # form se odvozuje z obor, ne z legacy pole
    assert s.form == StudyForm.COMBINED


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
