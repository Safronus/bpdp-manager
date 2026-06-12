"""Sbalitelný detail práce: skrytý bez výběru, lišta sbalí detail dolů.

Platí pro všechny záložky s pracemi (vedené/budoucí/historie/vše/oponované).
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from bpdpmanager.models import OpposingThesis, Student, Thesis
from bpdpmanager.models.enums import ThesisStatus, ThesisType
from bpdpmanager.services import ThesisService
from bpdpmanager.storage import JsonRepository


@pytest.fixture(scope="module")
def qapp():
    yield QApplication.instance() or QApplication([])


@pytest.fixture
def service(tmp_path) -> ThesisService:
    repo = JsonRepository(path=tmp_path / "db.json", backup_path=tmp_path / "db.json.bak")
    return ThesisService(repo)


def _make_thesis(service: ThesisService) -> Thesis:
    s = Student(first_name="J", last_name="N")
    service.upsert_student(s)
    t = Thesis(type=ThesisType.BP, status=ThesisStatus.IN_PROGRESS,
               academic_year=service.current_academic_year(), student_id=s.id)
    service.upsert_thesis(t)
    return t


def test_pane_hidden_until_selection_then_collapsible(qapp, service) -> None:
    from bpdpmanager.ui.main_window import _ThesesTab

    t = _make_thesis(service)
    tab = _ThesesTab(service, lambda x: True)
    tab.resize(1000, 800)
    tab.show()
    # Bez výběru: detail (celý panel) skrytý, vidět je jen seznam.
    assert not tab.detail_pane.isVisible()

    assert tab.tree.select_thesis(t.id)
    tab._on_thesis_selected(t.id)
    assert tab.detail_pane.isVisible()
    assert tab.detail.isVisible()

    # Sbalení lištou: detail zmizí, lišta (a panel) zůstane.
    tab.detail_pane.btn_toggle.setChecked(False)
    assert tab.detail_pane.collapsed
    assert not tab.detail.isVisible()
    assert tab.detail_pane.isVisible()

    # Přepnutí na jinou práci sbalení drží.
    tab._on_thesis_selected(t.id)
    assert tab.detail_pane.collapsed and not tab.detail.isVisible()

    # Rozbalení.
    tab.detail_pane.btn_toggle.setChecked(True)
    assert tab.detail.isVisible()
    tab.hide()


def test_opposing_pane_hidden_until_selection(qapp, service) -> None:
    from bpdpmanager.ui.opposing_tab import ROLE_ID, OpposingTab

    op = OpposingThesis(type=ThesisType.BP,
                        academic_year=service.current_academic_year(),
                        student_first_name="A", student_last_name="B")
    service.upsert_opposing_thesis(op)
    tab = OpposingTab(service)
    tab.resize(1000, 800)
    tab.show()
    assert not tab.detail_pane.isVisible()

    # Vyber oponenturu ve stromu (list se ROLE_ID, může být i hlouběji).
    def walk(item):
        if item.data(0, ROLE_ID):
            return item
        return next(
            (r for i in range(item.childCount()) if (r := walk(item.child(i)))),
            None,
        )

    leaf = next(
        (r for i in range(tab.tree.topLevelItemCount())
         if (r := walk(tab.tree.topLevelItem(i)))),
        None,
    )
    assert leaf is not None
    tab.tree.setCurrentItem(leaf)
    assert tab.detail_pane.isVisible()
    tab.hide()
