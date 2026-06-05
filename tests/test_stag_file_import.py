"""Testy importu souborů ze STAG — náhled výběru a párování práce v DB."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from bpdpmanager.models import OpposingThesis, Student, Thesis  # noqa: E402
from bpdpmanager.models.enums import AttachmentKind, ThesisType  # noqa: E402
from bpdpmanager.services import ThesisService  # noqa: E402
from bpdpmanager.services import stag_api  # noqa: E402
from bpdpmanager.storage import JsonRepository  # noqa: E402
from bpdpmanager.ui.stag_import_dialog import (  # noqa: E402
    _SECTION_TO_KIND,
    StagDownloadDialog,
    StagFilesPreviewDialog,
    _DownloadedStagFile,
)


@pytest.fixture(scope="module")
def qapp():
    yield QApplication.instance() or QApplication([])


@pytest.fixture
def service(tmp_path: Path) -> ThesisService:
    repo = JsonRepository(path=tmp_path / "db.json", backup_path=tmp_path / "db.json.bak")
    return ThesisService(repo)


def _mk_file(tmp_path: Path, name: str, section: str) -> _DownloadedStagFile:
    p = tmp_path / name
    p.write_bytes(b"x")
    return _DownloadedStagFile(
        path=p, filename=name,
        kind=_SECTION_TO_KIND.get(section, AttachmentKind.OTHER),
        section=section, size=1,
    )


def test_section_to_kind_mapping() -> None:
    assert _SECTION_TO_KIND["text"] == AttachmentKind.THESIS_TEXT
    assert _SECTION_TO_KIND["appendix"] == AttachmentKind.THESIS_APPENDIX
    assert _SECTION_TO_KIND["supervisor_review"] == AttachmentKind.SUPERVISOR_REVIEW
    assert _SECTION_TO_KIND["opponent_review"] == AttachmentKind.OPPONENT_REVIEW
    assert _SECTION_TO_KIND["other"] == AttachmentKind.OTHER


def test_preview_default_all_selected(qapp, tmp_path: Path) -> None:
    f1 = _mk_file(tmp_path, "text.pdf", "text")
    f2 = _mk_file(tmp_path, "prilohy.zip", "appendix")
    dlg = StagFilesPreviewDialog([("Novák Jan (DP)", [f1, f2])])
    # Defaultně vše zaškrtnuto
    for r in range(dlg.table.rowCount()):
        assert dlg.table.item(r, 0).checkState() == Qt.CheckState.Checked
    dlg._accept()
    assert f1.selected and f2.selected
    assert f1.kind == AttachmentKind.THESIS_TEXT


def test_preview_uncheck_one(qapp, tmp_path: Path) -> None:
    f1 = _mk_file(tmp_path, "text.pdf", "text")
    f2 = _mk_file(tmp_path, "posudek.pdf", "opponent_review")
    dlg = StagFilesPreviewDialog([("Novák Jan", [f1, f2])])
    dlg.table.item(0, 0).setCheckState(Qt.CheckState.Unchecked)
    dlg._accept()
    assert not f1.selected
    assert f2.selected


def test_preview_set_all_none(qapp, tmp_path: Path) -> None:
    f1 = _mk_file(tmp_path, "a.pdf", "text")
    dlg = StagFilesPreviewDialog([("X", [f1])])
    dlg._set_all(False)
    dlg._accept()
    assert not f1.selected


def test_find_db_target_by_adipidno(qapp, service: ThesisService) -> None:
    student = Student(first_name="Jan", last_name="Novák", university_id="A1")
    service.upsert_student(student)
    t = Thesis(type=ThesisType.DP, academic_year="2024/2025",
               student_id=student.id, adipidno="66896")
    service.upsert_thesis(t)

    dlg = StagDownloadDialog(service=service)
    r = stag_api.StagThesisResult(adipidno="66896", surname="Novák", name="Jan",
                                  type_label="Diplomová práce")
    assert dlg._find_db_target(r) == (t.id, None)


def test_find_db_target_opposing_by_name_type(qapp, service: ThesisService) -> None:
    op = OpposingThesis(type=ThesisType.BP, academic_year="2024/2025",
                        student_first_name="Eva", student_last_name="Malá")
    service.upsert_opposing_thesis(op)

    dlg = StagDownloadDialog(service=service)
    r = stag_api.StagThesisResult(adipidno="99999", surname="Malá", name="Eva",
                                  type_label="Bakalářská práce")
    # adipIdno nesedí → fallback přes jméno + typ
    assert dlg._find_db_target(r) == (None, op.id)


def test_find_db_target_no_match(qapp, service: ThesisService) -> None:
    dlg = StagDownloadDialog(service=service)
    r = stag_api.StagThesisResult(adipidno="123", surname="Nikdo", name="Nový",
                                  type_label="Diplomová práce")
    assert dlg._find_db_target(r) == (None, None)
