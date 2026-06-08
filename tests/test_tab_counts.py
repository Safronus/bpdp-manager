"""Test barev a počtů v titulcích záložek."""

from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from bpdpmanager.models import Student, Thesis
from bpdpmanager.models.enums import ThesisStatus, ThesisType
from bpdpmanager.models.thesis_proposal import ThesisProposal
from bpdpmanager.services import ThesisService
from bpdpmanager.storage import JsonRepository
from bpdpmanager.ui.main_window import (
    _FUTURE_CAPACITY,
    _TAB_AMBER,
    _TAB_GREEN,
    _TAB_RED,
    MainWindow,
    _future_count_color,
    _reviews_complete_color,
)


@pytest.fixture(scope="module")
def qapp():
    yield QApplication.instance() or QApplication([])


@pytest.fixture
def service(tmp_path: Path) -> ThesisService:
    repo = JsonRepository(path=tmp_path / "db.json", backup_path=tmp_path / "db.json.bak")
    return ThesisService(repo)


def _add_thesis(service: ThesisService, status: ThesisStatus) -> None:
    s = Student(first_name="X", last_name=f"Y{status.value}")
    service.upsert_student(s)
    t = Thesis(type=ThesisType.BP, status=status,
               academic_year="2025/2026", student_id=s.id)
    service.upsert_thesis(t)


def _count_in_title(win: MainWindow, tab) -> int:
    text = win.tabs.tabText(win.tabs.indexOf(tab))
    m = re.search(r"\((\d+)\)", text)
    return int(m.group(1)) if m else -1


def test_history_all_proposals_counts_in_titles(qapp, service) -> None:
    _add_thesis(service, ThesisStatus.IN_PROGRESS)
    _add_thesis(service, ThesisStatus.DEFENDED)
    _add_thesis(service, ThesisStatus.FAILED)        # historie
    service.upsert_proposal(ThesisProposal(type=ThesisType.BP, title_cs="Nápad 1"))
    service.upsert_proposal(ThesisProposal(type=ThesisType.DP, title_cs="Nápad 2"))

    win = MainWindow(service)
    win._refresh_tab_labels()

    assert _count_in_title(win, win.tab_history) == 2   # DEFENDED + FAILED
    assert _count_in_title(win, win.tab_all) == 3       # všechny práce
    assert _count_in_title(win, win.tab_proposals) == 2  # návrhy
    assert "Historie (" in win.tabs.tabText(win.tabs.indexOf(win.tab_history))
    assert "Vše (" in win.tabs.tabText(win.tabs.indexOf(win.tab_all))
    assert "Návrhy témat (" in win.tabs.tabText(win.tabs.indexOf(win.tab_proposals))


def test_future_count_color_thresholds() -> None:
    assert _future_count_color(0) == _TAB_GREEN
    assert _future_count_color(_FUTURE_CAPACITY - 1) == _TAB_GREEN
    assert _future_count_color(_FUTURE_CAPACITY) == _TAB_AMBER
    assert _future_count_color(_FUTURE_CAPACITY + 1) == _TAB_RED


def test_reviews_complete_color() -> None:
    assert _reviews_complete_color([]) is None              # žádné práce
    assert _reviews_complete_color([True, True]) == _TAB_GREEN   # vše hotové+odeslané
    assert _reviews_complete_color([True, False]) == _TAB_AMBER  # něco chybí
    assert _reviews_complete_color([False]) == _TAB_AMBER
