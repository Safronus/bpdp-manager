"""Dialog tisku posudků MyQ — naplnění výběru + sběr vybraných úloh."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from bpdpmanager.models import OpposingThesis, Student, Thesis
from bpdpmanager.models.enums import AttachmentKind, ThesisStatus, ThesisType
from bpdpmanager.services import ThesisService
from bpdpmanager.storage import JsonRepository
from bpdpmanager.ui.myq_print_dialog import MyQPrintDialog

_ROLE_NAME = Qt.ItemDataRole.UserRole + 2


@pytest.fixture(scope="module")
def qapp():
    yield QApplication.instance() or QApplication([])


@pytest.fixture
def service(tmp_path: Path) -> ThesisService:
    repo = JsonRepository(
        path=tmp_path / "db.json", backup_path=tmp_path / "db.json.bak"
    )
    return ThesisService(repo)


def _seed(service: ThesisService, tmp_path: Path) -> None:
    year = service.current_academic_year()
    # Vedená práce S posudkem vedoucího.
    s1 = Student(first_name="Jan", last_name="Novák")
    service.upsert_student(s1)
    t1 = Thesis(type=ThesisType.BP, status=ThesisStatus.IN_PROGRESS,
                academic_year=year, student_id=s1.id)
    service.upsert_thesis(t1)
    pv = tmp_path / "pv.pdf"
    pv.write_bytes(b"%PDF-1")
    service.attach_document(t1.id, pv, kind=AttachmentKind.SUPERVISOR_REVIEW)
    # Vedená práce BEZ posudku → nesmí se nabídnout.
    s2 = Student(first_name="Eva", last_name="Dvořáková")
    service.upsert_student(s2)
    t2 = Thesis(type=ThesisType.BP, status=ThesisStatus.IN_PROGRESS,
                academic_year=year, student_id=s2.id)
    service.upsert_thesis(t2)
    # Oponovaná práce S posudkem oponenta (aktuální rok).
    op = OpposingThesis(type=ThesisType.BP, academic_year=year,
                        student_first_name="Petr", student_last_name="Svoboda",
                        title_cs="X")
    service.upsert_opposing_thesis(op)
    po = tmp_path / "po.pdf"
    po.write_bytes(b"%PDF-2")
    service.opposing_attach_document(op.id, po, kind=AttachmentKind.OPPONENT_REVIEW)


def test_dialog_lists_only_works_with_pdf(qapp, service, tmp_path) -> None:
    _seed(service, tmp_path)
    dlg = MyQPrintDialog(service)
    names = [leaf.data(0, _ROLE_NAME) for leaf in dlg._iter_leaves()]
    assert "Jan Novák" in names          # vedená s posudkem
    assert "Petr Svoboda" in names       # oponovaná s posudkem
    assert "Eva Dvořáková" not in names  # bez posudku → nenabízí se
    assert len(names) == 2


def test_select_all_and_collect_jobs(qapp, service, tmp_path) -> None:
    _seed(service, tmp_path)
    dlg = MyQPrintDialog(service)
    assert dlg._selected_jobs() == []          # default nic nezaškrtnuto
    dlg._set_all_checked(True)
    jobs = dlg._selected_jobs()
    assert {n for n, _p in jobs} == {"Jan Novák", "Petr Svoboda"}
    assert all(Path(p).suffix == ".pdf" for _n, p in jobs)
    dlg._set_all_checked(False)
    assert dlg._selected_jobs() == []


def test_empty_when_no_reviews(qapp, service) -> None:
    dlg = MyQPrintDialog(service)
    assert list(dlg._iter_leaves()) == []
