"""Integrační test odesílacího dialogu (offscreen) — výběr sekretářky, filtr."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from bpdpmanager.models import Obor, OpposingThesis, Profile, Student, Thesis  # noqa: E402
from bpdpmanager.models.enums import AttachmentKind, ThesisStatus, ThesisType  # noqa: E402
from bpdpmanager.services import ThesisService  # noqa: E402
from bpdpmanager.storage import JsonRepository  # noqa: E402
from bpdpmanager.ui.send_reviews_dialog import SendReviewsDialog  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    yield QApplication.instance() or QApplication([])


@pytest.fixture
def service(tmp_path: Path) -> ThesisService:
    repo = JsonRepository(path=tmp_path / "db.json", backup_path=tmp_path / "db.json.bak")
    return ThesisService(repo)


class _FakePM:
    """Minimální náhrada ProfileManager — dialog čte jen `.active`."""

    def __init__(self, profile: Profile) -> None:
        self.active = profile


def _setup(service: ThesisService, tmp_path: Path) -> None:
    service.upsert_obor(
        Obor(name="Softwarové inženýrství", secretary_name="Nováková",
             secretary_email="sek@utb.cz")
    )
    student = Student(first_name="Jan", last_name="Novák", university_id="A1",
                      obor="Softwarové inženýrství")
    service.upsert_student(student)
    t = Thesis(type=ThesisType.BP, academic_year="2024/2025",
               student_id=student.id, title_cs="Téma práce",
               status=ThesisStatus.IN_PROGRESS)
    service.upsert_thesis(t)
    pdf = tmp_path / "posudek.pdf"
    pdf.write_bytes(b"%PDF dummy")
    service.attach_document(t.id, pdf, kind=AttachmentKind.SUPERVISOR_REVIEW)


def _pm() -> _FakePM:
    return _FakePM(Profile(name="P", data_dir="/tmp", user_name="Petr Žáček",
                           user_email="me@utb.cz"))


def test_dialog_lists_secretary_and_work(qapp, service: ThesisService, tmp_path: Path) -> None:
    _setup(service, tmp_path)
    dlg = SendReviewsDialog(service, _pm(), "supervisor")

    # Sekretářka se nabídla
    assert dlg.cb_secretary.count() == 1
    assert dlg.cb_secretary.currentData() == "sek@utb.cz"
    # Práce s hotovým PDF je v tabulce a předzaškrtnutá (nezaslaná)
    assert dlg.table.rowCount() == 1
    assert dlg.table.item(0, 0).checkState() == Qt.CheckState.Checked
    # Tělo e-mailu se sestavilo
    body = dlg.ed_body.toPlainText()
    assert "Bakalářské práce:" in body
    assert "Jan Novák (A1)" in body
    assert "Téma práce" in body
    # Kopie sobě defaultně zapnutá
    assert dlg.chk_cc.isChecked()


def test_sent_work_hidden_by_default(qapp, service: ThesisService, tmp_path: Path) -> None:
    _setup(service, tmp_path)
    # označ jako odeslané
    t = service.list_theses()[0]
    service.mark_supervisor_review_sent(t.id)

    dlg = SendReviewsDialog(service, _pm(), "supervisor")
    # Odeslané se defaultně skryjí
    assert dlg.table.rowCount() == 0
    # Po zapnutí „zobrazit i odeslané" se objeví (odznačené)
    dlg.chk_show_sent.setChecked(True)
    assert dlg.table.rowCount() == 1
    assert dlg.table.item(0, 0).checkState() == Qt.CheckState.Unchecked


def test_opponent_reviews_only_current_year(
    qapp, service: ThesisService, tmp_path: Path
) -> None:
    """Odeslání oponentských posudků nabízí jen AKTUÁLNÍ akademický rok."""
    cur = service.current_academic_year()
    op_now = OpposingThesis(type=ThesisType.BP, academic_year=cur,
                            student_last_name="Aktualni")
    op_old = OpposingThesis(type=ThesisType.BP, academic_year="2018/2019",
                            student_last_name="Stary")
    for op in (op_now, op_old):
        service.upsert_opposing_thesis(op)
        pdf = tmp_path / f"{op.id}.pdf"
        pdf.write_bytes(b"%PDF dummy")
        service.opposing_attach_document(op.id, pdf, kind=AttachmentKind.OPPONENT_REVIEW)

    dlg = SendReviewsDialog(service, _pm(), "opponent")
    ids = {it.work_id for it in dlg._all_role_items()}
    assert op_now.id in ids        # aktuální rok se nabízí
    assert op_old.id not in ids    # starší rok NE


def test_no_secretary_no_rows(qapp, service: ThesisService, tmp_path: Path) -> None:
    # Práce existuje, ale obor nemá sekretářku → nic se nenabídne
    student = Student(first_name="X", last_name="Y", obor="Bez sekretářky")
    service.upsert_student(student)
    t = Thesis(type=ThesisType.DP, academic_year="2024/2025", student_id=student.id)
    service.upsert_thesis(t)
    pdf = tmp_path / "p.pdf"
    pdf.write_bytes(b"%PDF")
    service.attach_document(t.id, pdf, kind=AttachmentKind.SUPERVISOR_REVIEW)

    dlg = SendReviewsDialog(service, _pm(), "supervisor")
    assert dlg.cb_secretary.currentData() is None
    assert dlg.table.rowCount() == 0
