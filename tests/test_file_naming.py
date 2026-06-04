"""Testy pro automatické pojmenování a organizaci nahraných souborů."""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

import pytest

from bpdpmanager.models import Student, Thesis
from bpdpmanager.models.enums import AttachmentKind, ThesisType
from bpdpmanager.models.opposing_thesis import OpposingThesis
from bpdpmanager.services import ThesisService
from bpdpmanager.services.file_naming import (
    KIND_TO_CODE,
    KIND_TO_SUBDIR,
    PLAGIARISM_SUBDIR,
    build_plagiarism_name,
    build_target_name,
    guess_is_plagiarism,
    guess_kind_from_filename,
    sanitize_for_fs,
    subdir_for,
)
from bpdpmanager.storage import JsonRepository

# --- file_naming: čisté funkce ------------------------------------------------


def test_kind_mappings_cover_all_attachment_kinds() -> None:
    """Každý ``AttachmentKind`` musí mít kód i podsložku — jinak by upload spadl."""
    for kind in AttachmentKind:
        assert kind in KIND_TO_CODE, f"chybí code pro {kind}"
        assert kind in KIND_TO_SUBDIR, f"chybí subdir pro {kind}"


def test_subdir_for_returns_string() -> None:
    assert subdir_for(AttachmentKind.SUPERVISOR_REVIEW) == "posudky"
    assert subdir_for(AttachmentKind.OPPONENT_REVIEW) == "posudky"
    assert subdir_for(AttachmentKind.THESIS_TEXT) == "text"
    assert subdir_for(AttachmentKind.THESIS_APPENDIX) == "prilohy"
    assert subdir_for(AttachmentKind.WORK_JOURNAL) == "denik"


def test_sanitize_strips_fs_unsafe_but_keeps_diacritics() -> None:
    assert sanitize_for_fs("Nováková") == "Nováková"
    assert sanitize_for_fs("Bad/Name:With*Chars?") == "BadNameWithChars"
    assert sanitize_for_fs("Multiple   spaces") == "Multiple_spaces"
    assert sanitize_for_fs("") == ""


def _touch(path: Path, mtime: float | None = None) -> Path:
    """Vytvoří prázdný soubor, volitelně nastaví mtime."""
    path.write_bytes(b"")
    if mtime is not None:
        os.utime(path, (mtime, mtime))
    return path


def _mtime_for_date(d: date) -> float:
    """Převede ``date`` na unix timestamp (lokální půlnoc)."""
    from datetime import datetime

    return datetime(d.year, d.month, d.day, 12, 0, 0).timestamp()


def test_build_target_name_basic(tmp_path: Path) -> None:
    src = _touch(tmp_path / "anything.pdf", mtime=_mtime_for_date(date(2026, 4, 15)))
    name = build_target_name("Novák", AttachmentKind.THESIS_TEXT, src)
    assert name == "Novák_text-prace_2026-04-15.pdf"


def test_build_target_name_preserves_diacritics(tmp_path: Path) -> None:
    src = _touch(tmp_path / "x.pdf", mtime=_mtime_for_date(date(2026, 1, 1)))
    name = build_target_name("Žďárský", AttachmentKind.ASSIGNMENT, src)
    assert name == "Žďárský_zadani_2026-01-01.pdf"


def test_build_target_name_empty_surname_fallback(tmp_path: Path) -> None:
    src = _touch(tmp_path / "x.pdf", mtime=_mtime_for_date(date(2026, 6, 1)))
    name = build_target_name(None, AttachmentKind.PRESENTATION, src)
    assert name == "Bez-prijmeni_prezentace_2026-06-01.pdf"


def test_build_target_name_collision_adds_version(tmp_path: Path) -> None:
    src = _touch(tmp_path / "x.pdf", mtime=_mtime_for_date(date(2026, 3, 10)))
    base = "Novák_posudek-vedouciho_2026-03-10.pdf"
    existing = {base}
    name = build_target_name(
        "Novák", AttachmentKind.SUPERVISOR_REVIEW, src, existing_names=existing
    )
    assert name == "Novák_posudek-vedouciho_2026-03-10_v2.pdf"

    existing.add(name)
    name3 = build_target_name(
        "Novák", AttachmentKind.SUPERVISOR_REVIEW, src, existing_names=existing
    )
    assert name3 == "Novák_posudek-vedouciho_2026-03-10_v3.pdf"


def test_build_target_name_lowercases_extension(tmp_path: Path) -> None:
    src = _touch(tmp_path / "DRAFT.PDF", mtime=_mtime_for_date(date(2026, 2, 2)))
    name = build_target_name("Novák", AttachmentKind.THESIS_TEXT, src)
    assert name.endswith(".pdf")


def test_build_plagiarism_name(tmp_path: Path) -> None:
    src = _touch(tmp_path / "theses.pdf", mtime=_mtime_for_date(date(2026, 5, 20)))
    name = build_plagiarism_name("Novák", src)
    assert name == "Novák_protokol-plagiat_2026-05-20.pdf"


# --- heuristika ---------------------------------------------------------------


@pytest.mark.parametrize(
    "filename, expected",
    [
        ("posudek_vedouciho.pdf", AttachmentKind.SUPERVISOR_REVIEW),
        ("posudek_vedoucího_novak.pdf", AttachmentKind.SUPERVISOR_REVIEW),
        ("supervisor_review.docx", AttachmentKind.SUPERVISOR_REVIEW),
        ("posudek_oponenta.pdf", AttachmentKind.OPPONENT_REVIEW),
        ("opponent_review.pdf", AttachmentKind.OPPONENT_REVIEW),
        ("oficialni_zadani.pdf", AttachmentKind.ASSIGNMENT),
        ("assignment.docx", AttachmentKind.ASSIGNMENT),
        ("prezentace_obhajoba.pptx", AttachmentKind.PRESENTATION),
        ("slides.key", AttachmentKind.PRESENTATION),
        ("pracovni_denik.md", AttachmentKind.WORK_JOURNAL),
        ("journal.txt", AttachmentKind.WORK_JOURNAL),
        ("prilohy_kod.zip", AttachmentKind.THESIS_APPENDIX),
        ("appendix_a.pdf", AttachmentKind.THESIS_APPENDIX),
        ("DP_text_final.pdf", AttachmentKind.THESIS_TEXT),
        ("bakalarska_prace.pdf", AttachmentKind.THESIS_TEXT),
        ("random.pdf", None),
        ("", None),
    ],
)
def test_guess_kind_from_filename(filename: str, expected: AttachmentKind | None) -> None:
    assert guess_kind_from_filename(filename) == expected


@pytest.mark.parametrize(
    "filename, expected",
    [
        ("plagiat_protokol.pdf", True),
        ("antiplagiarism_report.pdf", True),
        ("theses_check.pdf", True),
        ("protokol.pdf", True),
        ("random.pdf", False),
        ("", False),
    ],
)
def test_guess_is_plagiarism(filename: str, expected: bool) -> None:
    assert guess_is_plagiarism(filename) == expected


# --- integrace s ThesisService ------------------------------------------------


@pytest.fixture
def service(tmp_path: Path) -> ThesisService:
    repo = JsonRepository(path=tmp_path / "db.json", backup_path=tmp_path / "db.json.bak")
    return ThesisService(repo)


def _make_student_and_thesis(
    service: ThesisService, surname: str = "Novák"
) -> tuple[Student, Thesis]:
    student = service.upsert_student(Student(first_name="Jan", last_name=surname))
    thesis = Thesis(type=ThesisType.BP, academic_year="2025-26", student_id=student.id)
    service.upsert_thesis(thesis)
    return student, thesis


def test_attach_document_renames_and_organizes(
    service: ThesisService, tmp_path: Path
) -> None:
    _, thesis = _make_student_and_thesis(service, "Nováková")
    src = _touch(tmp_path / "neco_uplne_jineho.pdf", mtime=_mtime_for_date(date(2026, 4, 15)))

    att = service.attach_document(thesis.id, src, kind=AttachmentKind.THESIS_TEXT)

    assert att.url_or_path == "text/Nováková_text-prace_2026-04-15.pdf"
    abs_path = service.document_absolute_path(thesis.id, att)
    assert abs_path is not None and abs_path.exists()
    assert abs_path.parent.name == "text"


def test_attach_document_without_student_uses_fallback(
    service: ThesisService, tmp_path: Path
) -> None:
    thesis = Thesis(type=ThesisType.DP, academic_year="2025-26")
    service.upsert_thesis(thesis)
    src = _touch(tmp_path / "x.pdf", mtime=_mtime_for_date(date(2026, 1, 1)))

    att = service.attach_document(thesis.id, src, kind=AttachmentKind.OTHER)
    assert att.url_or_path == "ostatni/Bez-prijmeni_jine_2026-01-01.pdf"


def test_attach_document_collision_creates_v2(
    service: ThesisService, tmp_path: Path
) -> None:
    _, thesis = _make_student_and_thesis(service, "Novák")
    mtime = _mtime_for_date(date(2026, 3, 10))
    src1 = _touch(tmp_path / "a.pdf", mtime=mtime)
    src2 = _touch(tmp_path / "b.pdf", mtime=mtime)

    a1 = service.attach_document(thesis.id, src1, kind=AttachmentKind.SUPERVISOR_REVIEW)
    a2 = service.attach_document(thesis.id, src2, kind=AttachmentKind.SUPERVISOR_REVIEW)

    assert a1.url_or_path == "posudky/Novák_posudek-vedouciho_2026-03-10.pdf"
    assert a2.url_or_path == "posudky/Novák_posudek-vedouciho_2026-03-10_v2.pdf"


def test_attach_document_supervisor_and_opponent_share_folder(
    service: ThesisService, tmp_path: Path
) -> None:
    _, thesis = _make_student_and_thesis(service)
    src = _touch(tmp_path / "x.pdf", mtime=_mtime_for_date(date(2026, 5, 1)))

    s = service.attach_document(thesis.id, src, kind=AttachmentKind.SUPERVISOR_REVIEW)
    o = service.attach_document(thesis.id, src, kind=AttachmentKind.OPPONENT_REVIEW)

    assert s.url_or_path.startswith("posudky/")
    assert o.url_or_path.startswith("posudky/")


def test_set_plagiarism_pdf_renames_into_plagiat_subdir(
    service: ThesisService, tmp_path: Path
) -> None:
    _, thesis = _make_student_and_thesis(service, "Novák")
    src = _touch(tmp_path / "Theses_output.pdf", mtime=_mtime_for_date(date(2026, 5, 20)))

    rel = service.set_plagiarism_pdf(thesis.id, src)
    assert rel == f"{PLAGIARISM_SUBDIR}/Novák_protokol-plagiat_2026-05-20.pdf"

    path = service.plagiarism_pdf_path(thesis.id)
    assert path is not None and path.exists()


def test_opposing_attach_document_uses_inline_surname(
    service: ThesisService, tmp_path: Path
) -> None:
    op = OpposingThesis(
        type=ThesisType.BP,
        academic_year="2025-26",
        student_first_name="Eva",
        student_last_name="Černá",
    )
    service.upsert_opposing_thesis(op)
    src = _touch(tmp_path / "x.pdf", mtime=_mtime_for_date(date(2026, 2, 14)))

    att = service.opposing_attach_document(
        op.id, src, kind=AttachmentKind.OPPONENT_REVIEW
    )
    assert att.url_or_path == "posudky/Černá_posudek-oponenta_2026-02-14.pdf"
    abs_path = service.opposing_document_absolute_path(op.id, att)
    assert abs_path is not None and abs_path.exists()


def test_remove_document_works_with_subdir(service: ThesisService, tmp_path: Path) -> None:
    """Regrese: ``remove_document`` musí umět smazat soubor uložený v podsložce."""
    _, thesis = _make_student_and_thesis(service)
    src = _touch(tmp_path / "x.pdf", mtime=_mtime_for_date(date(2026, 6, 1)))
    att = service.attach_document(thesis.id, src, kind=AttachmentKind.THESIS_TEXT)
    abs_path = service.document_absolute_path(thesis.id, att)
    assert abs_path is not None and abs_path.exists()

    service.remove_document(thesis.id, 0, delete_file=True)
    assert not abs_path.exists()
    reloaded = service.get_thesis(thesis.id)
    assert reloaded is not None and reloaded.attachments == []
