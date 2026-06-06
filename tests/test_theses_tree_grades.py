"""Test sloupce Známky (vedoucí / oponent) ve stromu vedených prací."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QTreeWidgetItem

from bpdpmanager.models import Student, Thesis
from bpdpmanager.models.enums import ThesisStatus, ThesisType
from bpdpmanager.services import ThesisService
from bpdpmanager.storage import JsonRepository
from bpdpmanager.ui.theses_tree import ROLE_THESIS_ID, ThesesTreeWidget


@pytest.fixture(scope="module")
def qapp():
    yield QApplication.instance() or QApplication([])


@pytest.fixture
def service(tmp_path: Path) -> ThesisService:
    repo = JsonRepository(path=tmp_path / "db.json", backup_path=tmp_path / "db.json.bak")
    return ThesisService(repo)


def _leaf_text(tree: ThesesTreeWidget, thesis_id: str, col: int) -> str | None:
    found: list[str] = []

    def walk(item: QTreeWidgetItem) -> None:
        for i in range(item.childCount()):
            walk(item.child(i))
        if item.data(0, ROLE_THESIS_ID) == thesis_id:
            found.append(item.text(col))

    root = tree.invisibleRootItem()
    for i in range(root.childCount()):
        walk(root.child(i))
    return found[0] if found else None


def test_grades_column_present_before_reviews(qapp, service) -> None:
    headers = ThesesTreeWidget.HEADERS
    assert "Známky" in headers
    assert headers.index("Známky") < headers.index("Posudky")


def test_grades_column_shows_both(qapp, service) -> None:
    s = Student(first_name="Jan", last_name="Novák")
    service.upsert_student(s)
    t = Thesis(type=ThesisType.BP, status=ThesisStatus.DEFENDED,
               academic_year="2024/2025", student_id=s.id,
               grade_supervisor="A", grade_opponent="B")
    service.upsert_thesis(t)

    tree = ThesesTreeWidget(service)
    tree.refresh()
    txt = _leaf_text(tree, t.id, ThesesTreeWidget.COL_GRADES)
    assert txt is not None
    assert "A" in txt and "B" in txt
    assert "V:" in txt and "O:" in txt


def test_grades_column_dash_when_empty(qapp, service) -> None:
    s = Student(first_name="A", last_name="B")
    service.upsert_student(s)
    t = Thesis(type=ThesisType.DP, status=ThesisStatus.IN_PROGRESS,
               academic_year="2024/2025", student_id=s.id)
    service.upsert_thesis(t)

    tree = ThesesTreeWidget(service)
    tree.refresh()
    txt = _leaf_text(tree, t.id, ThesesTreeWidget.COL_GRADES)
    assert txt == "—"
