"""Filtr stavů v záložce Historie — checkboxy + perzistence napříč restartem."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from bpdpmanager.models import Opponent, Student, Thesis
from bpdpmanager.models.enums import STATUSES_HISTORY, ThesisStatus, ThesisType
from bpdpmanager.services import ThesisService
from bpdpmanager.storage import JsonRepository
from bpdpmanager.ui.main_window import _ThesesTab


@pytest.fixture(scope="module")
def qapp():
    yield QApplication.instance() or QApplication([])


@pytest.fixture
def service(tmp_path: Path) -> ThesisService:
    repo = JsonRepository(path=tmp_path / "db.json", backup_path=tmp_path / "db.json.bak")
    return ThesisService(repo)


class FakePM:
    """Minimální náhrada ProfileManageru — drží UI předvolby v paměti."""

    def __init__(self) -> None:
        self.prefs: dict = {}

    def get_ui_pref(self, key, default=None):
        return self.prefs.get(key, default)

    def set_ui_pref(self, key, value) -> None:
        self.prefs[key] = value


def _history_tab(service, pm) -> _ThesesTab:
    from bpdpmanager.ui.theses_tree import ThesesTreeWidget

    return _ThesesTab(
        service,
        lambda t: t.status in STATUSES_HISTORY,
        profile_manager=pm,
        status_filter_choices=[
            ThesisStatus.DEFENDED, ThesisStatus.CANCELLED, ThesisStatus.FAILED,
        ],
        status_filter_pref_key="history_status_filter",
        enable_extra_filters=True,
        hidden_columns=[ThesesTreeWidget.COL_REVIEWS, ThesesTreeWidget.COL_SENT],
    )


def test_default_all_checked(qapp, service) -> None:
    tab = _history_tab(service, FakePM())
    assert all(cb.isChecked() for cb in tab._status_checks.values())


def test_failed_status_has_own_checkbox_and_filters(qapp, service) -> None:
    tab = _history_tab(service, FakePM())
    assert ThesisStatus.FAILED in tab._status_checks  # „Neobhájeno" má checkbox

    # Odškrtni vše kromě „Neobhájeno" → projde jen FAILED.
    tab._status_checks[ThesisStatus.DEFENDED].setChecked(False)
    tab._status_checks[ThesisStatus.CANCELLED].setChecked(False)
    pred = tab.tree._filter_predicate

    class T:
        def __init__(self, status):
            self.status = status
            self.opponent_id = None
            self.grade_supervisor = ""
            self.grade_opponent = ""

    assert pred(T(ThesisStatus.FAILED)) is True
    assert pred(T(ThesisStatus.CANCELLED)) is False
    assert pred(T(ThesisStatus.DEFENDED)) is False


def test_uncheck_persists_and_filters(qapp, service) -> None:
    pm = FakePM()
    tab = _history_tab(service, pm)
    # Odškrtni „Nedokončeno" → uloží se zbývající zaškrtnuté (Obhájeno + Neobhájeno).
    tab._status_checks[ThesisStatus.CANCELLED].setChecked(False)
    assert set(pm.prefs["history_status_filter"]) == {
        ThesisStatus.DEFENDED.value, ThesisStatus.FAILED.value,
    }

    # Filtr stromu nyní nepropustí „Nedokončeno".
    pred = tab.tree._filter_predicate

    class T:
        def __init__(self, status):
            self.status = status

    assert pred(T(ThesisStatus.DEFENDED)) is True
    assert pred(T(ThesisStatus.CANCELLED)) is False


def test_restore_from_saved_pref(qapp, service) -> None:
    pm = FakePM()
    pm.prefs["history_status_filter"] = [ThesisStatus.CANCELLED.value]
    tab = _history_tab(service, pm)
    assert tab._status_checks[ThesisStatus.DEFENDED].isChecked() is False
    assert tab._status_checks[ThesisStatus.CANCELLED].isChecked() is True


def test_history_hides_review_and_sent_columns(qapp, service) -> None:
    from bpdpmanager.ui.theses_tree import ThesesTreeWidget

    tab = _history_tab(service, FakePM())
    assert tab.tree.isColumnHidden(ThesesTreeWidget.COL_REVIEWS)
    assert tab.tree.isColumnHidden(ThesesTreeWidget.COL_SENT)
    # Sloupec V/O zůstává viditelný.
    assert not tab.tree.isColumnHidden(ThesesTreeWidget.COL_GRADES)


def _defended_with(service, opponent_id=None, gs="", go=""):
    s = Student(first_name="X", last_name="Y")
    service.upsert_student(s)
    t = Thesis(type=ThesisType.BP, status=ThesisStatus.DEFENDED,
               academic_year="2024/2025", student_id=s.id,
               opponent_id=opponent_id, grade_supervisor=gs, grade_opponent=go)
    service.upsert_thesis(t)
    return t


def test_opponent_filter(qapp, service) -> None:
    op_a = Opponent(name="Adam Aaa")
    op_b = Opponent(name="Bedřich Bbb")
    service.upsert_opponent(op_a)
    service.upsert_opponent(op_b)
    ta = _defended_with(service, opponent_id=op_a.id)
    tb = _defended_with(service, opponent_id=op_b.id)

    tab = _history_tab(service, FakePM())
    # Combo obsahuje oba oponenty (+ „Všichni").
    assert tab._cb_opponent.count() == 3
    idx = tab._cb_opponent.findData(op_a.id)
    tab._cb_opponent.setCurrentIndex(idx)

    pred = tab.tree._filter_predicate
    assert pred(ta) is True
    assert pred(tb) is False


def test_grade_filter_matches_supervisor_or_opponent(qapp, service) -> None:
    t_sup = _defended_with(service, gs="A", go="C")
    t_opp = _defended_with(service, gs="D", go="A")
    t_none = _defended_with(service, gs="B", go="C")

    tab = _history_tab(service, FakePM())
    idx = tab._cb_grade.findData("A")
    tab._cb_grade.setCurrentIndex(idx)

    pred = tab.tree._filter_predicate
    assert pred(t_sup) is True    # A u vedoucího
    assert pred(t_opp) is True    # A u oponenta
    assert pred(t_none) is False  # žádná A
