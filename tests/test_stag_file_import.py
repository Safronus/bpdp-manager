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
    StagImportDialog,
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


def _pending(name, kind, section, selected, sf) -> _DownloadedStagFile:
    return _DownloadedStagFile(
        path=None, filename=name, kind=kind, section=section,
        size=10, selected=selected, stag_file=sf,
    )


def test_build_download_jobs_respects_selection_and_role(
    qapp, service: ThesisService
) -> None:
    """Joby na pozadí: jen vybrané, správný cíl/role/typ; bez cíle se přeskočí."""
    dlg = StagImportDialog(service)
    sf1, sf3 = object(), object()
    dlg._stag_pending_files = {
        "A1": [
            _pending("text.pdf", AttachmentKind.THESIS_TEXT, "text", True, sf1),
            _pending("skip.pdf", AttachmentKind.OTHER, "other", False, object()),
        ],
        "B2": [
            _pending("posudek.pdf", AttachmentKind.OPPONENT_REVIEW,
                     "opponent_review", True, sf3),
        ],
        "C3": [  # bez cíle v DB → přeskočí se celé
            _pending("x.pdf", AttachmentKind.OTHER, "other", True, object()),
        ],
    }
    dlg._stag_pending_labels = {"A1": "Novák Jan", "B2": "Malá Eva", "C3": "X"}

    jobs = dlg._build_stag_download_jobs(
        thesis_by_adip={"A1": "tid-1"},
        opposing_by_adip={"B2": "oid-2"},
    )

    assert len(jobs) == 2
    j_text = next(j for j in jobs if j.adipidno == "A1")
    assert j_text.target_id == "tid-1" and j_text.is_opposing is False
    assert j_text.kind == AttachmentKind.THESIS_TEXT
    assert j_text.stag_file is sf1 and j_text.student_label == "Novák Jan"
    j_op = next(j for j in jobs if j.adipidno == "B2")
    assert j_op.target_id == "oid-2" and j_op.is_opposing is True
    assert j_op.kind == AttachmentKind.OPPONENT_REVIEW


def test_mainwindow_stag_attach_fn_attaches_and_cleans_temp(
    qapp, tmp_path: Path, service: ThesisService
) -> None:
    """`_stag_attach_fn` připojí stažený soubor k práci a smaže temp."""
    from bpdpmanager.ui.main_window import MainWindow
    from bpdpmanager.ui.stag_download_manager import StagFileJob, StagFileResult

    student = Student(first_name="Jan", last_name="Novák")
    service.upsert_student(student)
    t = Thesis(type=ThesisType.DP, academic_year="2024/2025", student_id=student.id)
    service.upsert_thesis(t)

    class _SF:
        filename = "text.pdf"
        section = "text"

    mw = MainWindow(service)
    try:
        job = StagFileJob(
            target_id=t.id, is_opposing=False, adipidno="X",
            student_label="Novák Jan", stag_file=_SF(),
            kind=AttachmentKind.THESIS_TEXT,
        )
        tmp = tmp_path / "stag_text.pdf"
        tmp.write_bytes(b"PDFDATA")
        mw._stag_attach_fn(StagFileResult(job=job, path=tmp, size=7))

        loaded = service.get_thesis(t.id)
        assert any(a.kind == AttachmentKind.THESIS_TEXT for a in loaded.attachments)
        assert not tmp.exists()   # temp uklizen po připojení
    finally:
        mw.close()
