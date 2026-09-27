"""Jednotný dialog „Nová práce" (dřív Nová práce / Zájemce / Minulá práce)."""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

from bpdpmanager.models import Student, Thesis
from bpdpmanager.models.enums import ThesisStatus, ThesisType
from bpdpmanager.services import ThesisService
from bpdpmanager.services import new_thesis as nt
from bpdpmanager.storage import JsonRepository

SEPT = date(2026, 9, 27)    # běžící rok 2026/2027, podzim
SPRING = date(2027, 3, 1)   # stále 2026/2027, jaro


@pytest.fixture(scope="module")
def qapp():
    yield QApplication.instance() or QApplication([])


@pytest.fixture
def service(tmp_path: Path) -> ThesisService:
    repo = JsonRepository(path=tmp_path / "db.json", backup_path=tmp_path / "db.json.bak")
    return ThesisService(repo)


@pytest.fixture
def today_sept(monkeypatch: pytest.MonkeyPatch) -> None:
    """Dialog volá ``default_year``/``year_choices`` bez data → zafixovat dnešek."""

    class _FixedDate(date):
        @classmethod
        def today(cls):
            return SEPT

    monkeypatch.setattr(nt, "date", _FixedDate)


# --- pravidla (služba) -----------------------------------------------------------


def test_year_choices_by_status() -> None:
    assert nt.year_choices(ThesisStatus.INTERESTED, SEPT) == [
        "2026/2027", "2027/2028", "2028/2029"]
    past = nt.year_choices(ThesisStatus.DEFENDED, SEPT)
    assert past[:2] == ["2026/2027", "2025/2026"] and past[-1] == "2009/2010"
    assert nt.year_choices(ThesisStatus.IN_PROGRESS, SEPT) == past


@pytest.mark.parametrize(("status", "today", "expected"), [
    (ThesisStatus.LISTED, SEPT, "2026/2027"),       # září až prosinec → letošní
    (ThesisStatus.INTERESTED, SPRING, "2027/2028"),  # leden až srpen → příští
    (ThesisStatus.RESERVED, date(2026, 8, 31), "2026/2027"),  # 31. 8. = jaro 25/26
    (ThesisStatus.IN_PROGRESS, SPRING, "2026/2027"),
    (ThesisStatus.DEFENDED, SEPT, "2025/2026"),
    (ThesisStatus.CANCELLED, SPRING, "2025/2026"),
])
def test_default_year(status, today, expected) -> None:
    assert nt.default_year(status, today) == expected
    assert expected in nt.year_choices(status, today)   # výchozí je vždy v nabídce


def test_tab_default_status() -> None:
    assert nt.tab_default_status(nt.TabKind.CURRENT) == ThesisStatus.IN_PROGRESS
    assert nt.tab_default_status(nt.TabKind.FUTURE) == ThesisStatus.LISTED
    assert nt.tab_default_status(nt.TabKind.HISTORY) == ThesisStatus.DEFENDED
    assert nt.tab_default_status(nt.TabKind.OTHER) == ThesisStatus.LISTED
    assert set(nt.CREATABLE_STATUSES) == set(ThesisStatus)


def _students(service: ThesisService) -> tuple[Student, Student]:
    bp = Student(first_name="Jan", last_name="Novák", obor="ITA-P", university_id="A20001")
    dp = Student(first_name="Jan", last_name="Novák", obor="NSWI-P", university_id="A24002")
    service.upsert_student(bp)
    service.upsert_student(dp)
    service.upsert_thesis(Thesis(type=ThesisType.BP, academic_year="2024/2025",
                                 status=ThesisStatus.DEFENDED, student_id=bp.id))
    service.upsert_thesis(Thesis(type=ThesisType.DP, academic_year="2026/2027",
                                 status=ThesisStatus.INTERESTED, student_id=dp.id))
    return bp, dp


def test_student_warnings(service) -> None:
    bp, dp = _students(service)
    kinds = lambda sid, t: [w.kind for w in nt.student_warnings(service, sid, t)]  # noqa: E731
    assert kinds(None, ThesisType.DP) == []
    assert kinds(bp.id, ThesisType.DP) == [nt.WarningKind.BP_RECORD_FOR_DP]
    assert kinds(bp.id, ThesisType.BP) == []                  # BP obhájená → OK
    assert kinds(dp.id, ThesisType.DP) == [nt.WarningKind.OPEN_SAME_TYPE]


def test_create_thesis_saves_and_updates_obor(service) -> None:
    _, dp = _students(service)
    t = nt.create_thesis(service, thesis_type=ThesisType.DP,
                         status=ThesisStatus.RESERVED, academic_year=" 2026/2027 ",
                         student_id=dp.id, obor=" NSWI-K ", title=" Téma ",
                         annotation=" Anotace ")
    saved = service.get_thesis(t.id)
    assert (saved.academic_year, saved.student_id, saved.title_cs, saved.annotation) == (
        "2026/2027", dp.id, "Téma", "Anotace")
    assert service.get_student(dp.id).obor == "NSWI-K"
    # na disku (batch uložil)
    assert ThesisService(service._repo).get_thesis(t.id) is not None


@pytest.mark.parametrize("year", ["2026-2027", "2026/2028", "", "rok"])
def test_create_thesis_rejects_bad_year(service, year) -> None:
    with pytest.raises(nt.NewThesisError):
        nt.create_thesis(service, thesis_type=ThesisType.BP,
                         status=ThesisStatus.LISTED, academic_year=year)
    assert service.list_theses() == []


def test_create_thesis_rejects_missing_student(service) -> None:
    with pytest.raises(nt.NewThesisError):
        nt.create_thesis(service, thesis_type=ThesisType.BP, status=ThesisStatus.LISTED,
                         academic_year="2026/2027", student_id="neexistuje")


# --- dialog ------------------------------------------------------------------------


def _years(dlg) -> list[str]:
    return [dlg.cb_year.itemText(i) for i in range(dlg.cb_year.count())]


def test_dialog_defaults_per_tab(qapp, service, today_sept) -> None:
    from bpdpmanager.ui.new_thesis_dialog import NewThesisDialog

    d = NewThesisDialog(service, tab=nt.TabKind.FUTURE)
    assert d.status == ThesisStatus.LISTED and d.cb_year.currentText() == "2026/2027"
    assert _years(d) == ["2026/2027", "2027/2028", "2028/2029"]
    d = NewThesisDialog(service, tab=nt.TabKind.CURRENT)
    assert d.status == ThesisStatus.IN_PROGRESS and d.cb_year.currentText() == "2026/2027"
    d = NewThesisDialog(service, tab=nt.TabKind.HISTORY)
    assert d.status == ThesisStatus.DEFENDED and d.cb_year.currentText() == "2025/2026"


def test_dialog_status_change_updates_years(qapp, service, today_sept) -> None:
    from bpdpmanager.ui.new_thesis_dialog import NewThesisDialog

    d = NewThesisDialog(service, tab=nt.TabKind.FUTURE)
    d._set_status(ThesisStatus.DEFENDED)            # rok neměněn → výchozí nového stavu
    assert d.cb_year.currentText() == "2025/2026" and "2028/2029" not in _years(d)
    d.cb_year.setCurrentText("2020/2021")
    d._on_year_activated(0)                          # ruční volba
    d._set_status(ThesisStatus.CANCELLED)
    assert d.cb_year.currentText() == "2020/2021"    # ruční volba zůstala
    d._set_status(ThesisStatus.INTERESTED)           # 2020/2021 v nabídce není
    assert d.cb_year.currentText() == "2026/2027"


def test_dialog_warnings_and_accept(qapp, service, today_sept) -> None:
    from bpdpmanager.ui.new_thesis_dialog import NewThesisDialog

    bp, dp = _students(service)
    d = NewThesisDialog(service, tab=nt.TabKind.FUTURE)
    d.rb_dp.setChecked(True)
    d._set_student(bp.id)                             # BP záznam pro DP → varování
    assert not d.lbl_warning.isHidden()
    assert "BP" in d.lbl_warning.text() and "href" in d.lbl_warning.text()
    assert "A20001" in d.ed_student.text() and d.cb_obor.currentText() == "ITA-P"
    d.rb_bp.setChecked(True)                          # typ BP → bez varování
    assert d.lbl_warning.isHidden()

    d.rb_dp.setChecked(True)
    d._set_student(dp.id)                             # DP záznam už má DP zájemce
    assert "neukončenou" in d.lbl_warning.text()
    d._set_student(None)
    assert d.lbl_warning.isHidden() and d.ed_student.text() == ""

    d._set_student(dp.id)
    d.ed_title.setText("Fiktivní téma")
    d._on_accept()
    assert d.result() == QDialog.DialogCode.Accepted and d.thesis is not None
    saved = service.get_thesis(d.thesis.id)
    assert (saved.type, saved.status, saved.academic_year, saved.student_id,
            saved.title_cs) == (ThesisType.DP, ThesisStatus.LISTED, "2026/2027",
                                dp.id, "Fiktivní téma")


def test_dialog_invalid_year_shows_warning(qapp, service, today_sept, monkeypatch) -> None:
    from bpdpmanager.ui.new_thesis_dialog import NewThesisDialog

    shown = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: shown.append(a[2]))
    d = NewThesisDialog(service)
    d.cb_year.clear()                                 # žádný rok → chyba validace
    d._on_accept()
    assert shown and d.thesis is None and service.list_theses() == []


def test_toolbar_has_single_create_action(qapp, service) -> None:
    from PySide6.QtGui import QAction

    from bpdpmanager.ui.main_window import MainWindow

    win = MainWindow(service)
    texts = [a.text() for a in win.findChildren(QAction)]
    assert "➕ Nová práce" in texts  # noqa: RUF001 — přesný text tlačítka
    assert not any(t in texts for t in ("🌱 Zájemce", "🕘 Minulá práce"))
