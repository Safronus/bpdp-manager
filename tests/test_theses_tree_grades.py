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
from bpdpmanager.ui.theses_tree import (
    ROLE_GRADES,
    ROLE_REVIEWS,
    ROLE_STATUS,
    ROLE_THESIS_ID,
    ThesesTreeWidget,
    _contrast_text,
)


@pytest.fixture(scope="module")
def qapp():
    yield QApplication.instance() or QApplication([])


@pytest.fixture
def service(tmp_path: Path) -> ThesisService:
    repo = JsonRepository(path=tmp_path / "db.json", backup_path=tmp_path / "db.json.bak")
    return ThesisService(repo)


def _leaf(tree: ThesesTreeWidget, thesis_id: str) -> QTreeWidgetItem | None:
    found: list[QTreeWidgetItem] = []

    def walk(item: QTreeWidgetItem) -> None:
        for i in range(item.childCount()):
            walk(item.child(i))
        if item.data(0, ROLE_THESIS_ID) == thesis_id:
            found.append(item)

    root = tree.invisibleRootItem()
    for i in range(root.childCount()):
        walk(root.child(i))
    return found[0] if found else None


def test_grades_column_header_is_vo(qapp, service) -> None:
    headers = ThesesTreeWidget.HEADERS
    assert "Známky V/O" in headers
    assert headers.index("Známky V/O") < headers.index("Posudky")


def test_grades_column_stores_pair(qapp, service) -> None:
    s = Student(first_name="Jan", last_name="Novák")
    service.upsert_student(s)
    t = Thesis(type=ThesisType.BP, status=ThesisStatus.DEFENDED,
               academic_year="2024/2025", student_id=s.id,
               grade_supervisor="A", grade_opponent="B")
    service.upsert_thesis(t)

    tree = ThesesTreeWidget(service)
    tree.refresh()
    leaf = _leaf(tree, t.id)
    assert leaf is not None
    # Delegát kreslí dvojici z dat ROLE_GRADES (text buňky je prázdný).
    assert leaf.data(ThesesTreeWidget.COL_GRADES, ROLE_GRADES) == ("A", "B")
    assert leaf.text(ThesesTreeWidget.COL_GRADES) == ""


def test_grades_column_dash_when_empty(qapp, service) -> None:
    s = Student(first_name="A", last_name="B")
    service.upsert_student(s)
    t = Thesis(type=ThesisType.DP, status=ThesisStatus.IN_PROGRESS,
               academic_year="2024/2025", student_id=s.id)
    service.upsert_thesis(t)

    tree = ThesesTreeWidget(service)
    tree.refresh()
    leaf = _leaf(tree, t.id)
    assert leaf is not None
    assert leaf.data(ThesesTreeWidget.COL_GRADES, ROLE_GRADES) is None
    assert leaf.text(ThesesTreeWidget.COL_GRADES) == "—"


def test_reviews_badge_data(qapp, service, tmp_path) -> None:
    """Sloupec Posudky nese (má_vedoucího, má_oponenta) pro V/O badge."""
    from bpdpmanager.models.enums import AttachmentKind

    s = Student(first_name="Jan", last_name="Novák")
    service.upsert_student(s)
    t = Thesis(type=ThesisType.BP, status=ThesisStatus.IN_PROGRESS,
               academic_year="2024/2025", student_id=s.id)
    service.upsert_thesis(t)
    src = tmp_path / "pv.pdf"
    src.write_bytes(b"%PDF dummy")
    service.attach_document(t.id, src, kind=AttachmentKind.SUPERVISOR_REVIEW)

    tree = ThesesTreeWidget(service)
    tree.refresh()
    leaf = _leaf(tree, t.id)
    # Má posudek vedoucího, nemá oponenta.
    assert leaf.data(ThesesTreeWidget.COL_REVIEWS, ROLE_REVIEWS) == (True, False)
    assert leaf.text(ThesesTreeWidget.COL_REVIEWS) == ""  # kreslí delegát


def test_status_badge_data_and_contrast(qapp, service) -> None:
    """Stav je zaoblený badge (ROLE_STATUS = (label, barva)); světlá → tmavý text."""
    s = Student(first_name="Jan", last_name="Novák")
    service.upsert_student(s)
    t = Thesis(type=ThesisType.BP, status=ThesisStatus.CANCELLED,
               academic_year="2024/2025", student_id=s.id)
    service.upsert_thesis(t)

    tree = ThesesTreeWidget(service)
    tree.refresh()
    leaf = _leaf(tree, t.id)
    label, color = leaf.data(ThesesTreeWidget.COL_STATUS, ROLE_STATUS)
    assert label == "Nedokončeno"
    assert color == "#d6d6d6"                 # světle šedá
    assert _contrast_text(color) == "#212121"  # tmavý text na světlém
    assert leaf.text(ThesesTreeWidget.COL_STATUS) == ""  # kreslí delegát
