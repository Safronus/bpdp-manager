"""Výběr studenta — přehled se záznamy BP/DP téže osoby, hledání, duplicity."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QDialog

from bpdpmanager.models import Student, Thesis
from bpdpmanager.models.enums import ThesisStatus, ThesisType
from bpdpmanager.services import ThesisService
from bpdpmanager.services import student_lookup as sl
from bpdpmanager.storage import JsonRepository


@pytest.fixture(scope="module")
def qapp():
    yield QApplication.instance() or QApplication([])


@pytest.fixture
def service(tmp_path: Path) -> ThesisService:
    repo = JsonRepository(path=tmp_path / "db.json", backup_path=tmp_path / "db.json.bak")
    return ThesisService(repo)


@pytest.fixture
def bp_dp(service: ThesisService) -> tuple[Student, Student]:
    """Fiktivní osoba se dvěma záznamy: BP (obhájeno) a DP (zájemce)."""
    bp = Student(first_name="Jan", last_name="Novák", obor="ITA-P",
                 university_id="A20001", email="jan.novak@example.test")
    dp = Student(first_name="Jan", last_name="Novák", obor="NSWI-P",
                 university_id="A24002", email="jan.novak@example.test")
    other = Student(first_name="Eva", last_name="Černá", obor="ITA-K",
                    university_id="A21003")
    for s in (bp, dp, other):
        service.upsert_student(s)
    service.upsert_thesis(Thesis(type=ThesisType.BP, academic_year="2024/2025",
                                 status=ThesisStatus.DEFENDED, student_id=bp.id,
                                 title_cs="Fiktivní bakalářka"))
    service.upsert_thesis(Thesis(type=ThesisType.DP, academic_year="2026/2027",
                                 status=ThesisStatus.INTERESTED, student_id=dp.id))
    return bp, dp


# --- služba ---------------------------------------------------------------------


def test_summaries_order_and_theses_label(service, bp_dp) -> None:
    bp, dp = bp_dp
    summ = sl.student_summaries(service)
    # příjmení bez diakritiky: Černá < Novák; stejné jméno → podle os. čísla
    assert [s.student.university_id for s in summ] == ["A21003", "A20001", "A24002"]
    by_id = {s.student.id: s for s in summ}
    assert by_id[bp.id].theses_label == "BP 2024/2025 Obhájeno"
    assert by_id[dp.id].theses_label == "DP 2026/2027 Zájemce bez tématu"
    assert sl.same_name_count(summ, bp) == 2


@pytest.mark.parametrize(("query", "expected"), [
    ("novak", {"A20001", "A24002"}),          # bez diakritiky
    ("A24002", {"A24002"}),                   # osobní číslo
    ("nswi", {"A24002"}),                     # obor
    ("jan nswi", {"A24002"}),                 # víc slov = všechna musí sedět
    ("cerna", {"A21003"}),
    ("", {"A20001", "A24002", "A21003"}),
    ("nikdo", set()),
])
def test_filter_summaries(service, bp_dp, query, expected) -> None:
    found = sl.filter_summaries(sl.student_summaries(service), query)
    assert {s.student.university_id for s in found} == expected


def test_open_theses_of_type(service, bp_dp) -> None:
    bp, dp = bp_dp
    # BP je obhájená (Historie) → nepočítá se jako otevřená
    assert sl.open_theses_of_type(service, bp.id, ThesisType.BP) == []
    open_dp = sl.open_theses_of_type(service, dp.id, ThesisType.DP)
    assert len(open_dp) == 1
    assert sl.open_theses_of_type(service, dp.id, ThesisType.BP) == []
    assert sl.open_theses_of_type(service, dp.id, ThesisType.DP,
                                  exclude_id=open_dp[0].id) == []


def test_followup_student_copies_identity_only(bp_dp) -> None:
    bp, _ = bp_dp
    new = sl.followup_student(bp)
    assert (new.first_name, new.last_name, new.email) == ("Jan", "Novák", bp.email)
    assert new.id != bp.id and new.university_id is None and new.obor == ""


# --- dialog ---------------------------------------------------------------------


def _row_ids(dlg) -> list[str]:
    from bpdpmanager.ui.student_picker_dialog import _ID_ROLE

    return [dlg.table.item(r, 0).data(_ID_ROLE) for r in range(dlg.table.rowCount())]


def test_picker_shows_both_records_and_preselects(qapp, service, bp_dp) -> None:
    from bpdpmanager.ui.student_picker_dialog import StudentPickerDialog

    bp, dp = bp_dp
    dlg = StudentPickerDialog(service, current_id=dp.id)
    assert len(_row_ids(dlg)) == 3
    assert dlg._current_id() == dp.id                       # předvybraný DP záznam
    uids = {dlg.table.item(r, 1).text() for r in range(3)}
    assert {"A20001", "A24002"} <= uids                     # os. čísla viditelná
    name_item = next(dlg.table.item(r, 0) for r in range(3)
                     if dlg.table.item(r, 1).text() == "A20001")
    assert name_item.font().bold() and name_item.toolTip()  # stejné jméno zvýrazněno
    html = dlg.detail.toHtml()
    assert "A24002" in html and "2 záznamy" in html

    dlg.ed_search.setText("A20001")                         # filtr → 1 řádek, vybraný
    assert _row_ids(dlg) == [bp.id] and dlg._current_id() == bp.id
    assert "Fiktivní bakalářka" in dlg.detail.toHtml()
    dlg._accept_selected()
    assert dlg.result() == QDialog.DialogCode.Accepted
    assert dlg.selected_student_id == bp.id


def test_picker_none_and_empty_filter(qapp, service, bp_dp) -> None:
    from bpdpmanager.ui.student_picker_dialog import StudentPickerDialog

    _, dp = bp_dp
    dlg = StudentPickerDialog(service, current_id=dp.id)
    dlg.ed_search.setText("nikdo takovy")
    assert dlg.table.rowCount() == 0 and not dlg.btn_ok.isEnabled()
    dlg._accept_selected()                                  # nic vybráno → nic
    assert dlg.result() != QDialog.DialogCode.Accepted
    assert dlg.btn_none is not None
    dlg._accept_none()
    assert dlg.selected_student_id is None
    assert StudentPickerDialog(service, allow_none=False).btn_none is None


def test_picker_followup_creates_new_record(qapp, service, bp_dp, monkeypatch) -> None:
    import bpdpmanager.ui.student_picker_dialog as spd

    bp, _ = bp_dp
    seen = {}

    class FakeStudentDialog:
        def __init__(self, service, student=None, parent=None, *, title=None):
            seen["title"] = title
            self.student = student
            self._service = service

        def exec(self):
            self.student.university_id = "A26009"
            self.student.obor = "NSWI-K"
            self._service.upsert_student(self.student)
            return QDialog.DialogCode.Accepted

    monkeypatch.setattr(spd, "StudentDialog", FakeStudentDialog)
    dlg = spd.StudentPickerDialog(service, current_id=bp.id)
    dlg.ed_search.setText("A20001")
    dlg._new_followup()
    new = next(s for s in service.list_students() if s.university_id == "A26009")
    assert new.id != bp.id and new.email == bp.email and seen["title"]
    assert dlg.changed and dlg.ed_search.text() == ""       # filtr zrušen
    assert dlg._current_id() == new.id and len(_row_ids(dlg)) == 4


# --- detail práce ------------------------------------------------------------------


def test_detail_keeps_selected_record_with_same_name(qapp, service, bp_dp) -> None:
    """Dřív se student dohledával podle textu jména → vzal se první shodný záznam."""
    from bpdpmanager.ui.thesis_detail import ThesisDetail

    bp, dp = bp_dp
    t = Thesis(type=ThesisType.DP, academic_year="2026/2027",
               status=ThesisStatus.LISTED)
    service.upsert_thesis(t)
    det = ThesisDetail(service)
    det.set_thesis(t)
    first, second = (det.cb_student.findData(bp.id), det.cb_student.findData(dp.id))
    assert first >= 0 and second >= 0
    # vyber ten záznam, který je v comboboxu později (texty jsou shodné)
    later_id = bp.id if first > second else dp.id
    det.cb_student.setCurrentIndex(max(first, second))
    det.flush()
    assert service.get_thesis(t.id).student_id == later_id


def test_detail_pick_student_button(qapp, service, bp_dp, monkeypatch) -> None:
    import bpdpmanager.ui.student_picker_dialog as spd
    from bpdpmanager.ui.thesis_detail import ThesisDetail

    _, dp = bp_dp
    t = Thesis(type=ThesisType.DP, academic_year="2026/2027", status=ThesisStatus.LISTED)
    service.upsert_thesis(t)
    det = ThesisDetail(service)
    det.set_thesis(t)

    class FakePicker:
        def __init__(self, service, parent=None, *, current_id=None, allow_none=True):
            self.selected_student_id = dp.id
            self.changed = False

        def exec(self):
            return QDialog.DialogCode.Accepted

    monkeypatch.setattr(spd, "StudentPickerDialog", FakePicker)
    det._pick_student()
    det.flush()
    saved = service.get_thesis(t.id)
    assert saved.student_id == dp.id
    assert det.cb_thesis_obor.currentText() == "NSWI-P"      # obor ze záznamu DP
