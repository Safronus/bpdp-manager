"""Záložka „Vše": barevné roky (Budoucí/Aktuální/Minulé) + prázdné Posudky u budoucích."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from bpdpmanager.models import Student, Thesis
from bpdpmanager.models.enums import ThesisStatus, ThesisType
from bpdpmanager.services import ThesisService
from bpdpmanager.storage import JsonRepository
from bpdpmanager.ui.theses_tree import (
    _YEAR_CURRENT_COLOR,
    _YEAR_FUTURE_COLOR,
    _YEAR_PAST_COLOR,
    ROLE_REVIEWS,
    ROLE_THESIS_ID,
    ThesesTreeWidget,
)


@pytest.fixture(scope="module")
def qapp():
    yield QApplication.instance() or QApplication([])


def _years(current):
    y0, y1 = current.split("/")
    return f"{int(y1)}/{int(y1) + 1}", f"{int(y0) - 1}/{int(y0)}"


def test_year_colors_and_blank_future_reviews(qapp, tmp_path) -> None:
    repo = JsonRepository(path=tmp_path / "db.json", backup_path=tmp_path / "db.json.bak")
    service = ThesisService(repo)
    current = service.current_academic_year()
    future, past = _years(current)
    s = Student(first_name="J", last_name="N")
    service.upsert_student(s)
    # budoucí práce (INTERESTED) v budoucím roce; aktuální; minulá
    service.upsert_thesis(Thesis(type=ThesisType.BP, status=ThesisStatus.INTERESTED,
                                 academic_year=future, student_id=s.id))
    service.upsert_thesis(Thesis(type=ThesisType.DP, status=ThesisStatus.IN_PROGRESS,
                                 academic_year=current, student_id=s.id))
    service.upsert_thesis(Thesis(type=ThesisType.DP, status=ThesisStatus.DEFENDED,
                                 academic_year=past, student_id=s.id))

    tree = ThesesTreeWidget(service)
    tree.color_year_groups = True
    tree.blank_future_reviews = True
    tree.refresh()

    expected = {future: _YEAR_FUTURE_COLOR, current: _YEAR_CURRENT_COLOR,
                past: _YEAR_PAST_COLOR}
    seen = {}
    leaves = []
    for i in range(tree.topLevelItemCount()):
        yi = tree.topLevelItem(i)
        yr = yi.data(0, Qt.ItemDataRole.UserRole + 3)
        seen[yr] = yi.foreground(0).color().name().lower()

        def walk(it):
            for j in range(it.childCount()):
                walk(it.child(j))
            if it.data(0, ROLE_THESIS_ID):
                leaves.append(it)
        walk(yi)

    for yr, color in expected.items():
        assert seen[yr] == color.lower(), f"rok {yr}: {seen[yr]} != {color}"

    # budoucí práce (INTERESTED) → prázdný sloupec Posudky (ROLE_REVIEWS None)
    by_status = {lf.data(0, ROLE_THESIS_ID): lf for lf in leaves}
    future_thesis = next(
        t for t in service.list_theses() if t.status == ThesisStatus.INTERESTED
    )
    current_thesis = next(
        t for t in service.list_theses() if t.status == ThesisStatus.IN_PROGRESS
    )
    assert by_status[future_thesis.id].data(tree.COL_REVIEWS, ROLE_REVIEWS) is None
    assert by_status[current_thesis.id].data(tree.COL_REVIEWS, ROLE_REVIEWS) is not None


def test_year_colors_off_by_default(qapp, tmp_path) -> None:
    """Bez příznaku color_year_groups roky obarvené nejsou."""
    repo = JsonRepository(path=tmp_path / "db.json", backup_path=tmp_path / "db.json.bak")
    service = ThesisService(repo)
    s = Student(first_name="J", last_name="N")
    service.upsert_student(s)
    service.upsert_thesis(Thesis(type=ThesisType.BP, status=ThesisStatus.IN_PROGRESS,
                                 academic_year=service.current_academic_year(),
                                 student_id=s.id))
    tree = ThesesTreeWidget(service)
    tree.refresh()
    yi = tree.topLevelItem(0)
    # výchozí foreground (nenastaveno) → invalid barva
    assert not yi.foreground(0).color().isValid() or yi.foreground(0).style() == Qt.BrushStyle.NoBrush
