"""Indikátor „Vytištěno" — service příznak + ✓/✗ badge ve stromech."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QTreeWidgetItem

from bpdpmanager.models import OpposingThesis, Student, Thesis
from bpdpmanager.models.enums import (
    SENT_BG,
    UNSENT_BG,
    AttachmentKind,
    ThesisStatus,
    ThesisType,
)
from bpdpmanager.services import ThesisService
from bpdpmanager.storage import JsonRepository
from bpdpmanager.ui.opposing_tab import COL_PRINTED as OP_COL_PRINTED
from bpdpmanager.ui.opposing_tab import OpposingTab
from bpdpmanager.ui.theses_tree import ROLE_PRINTED, ROLE_THESIS_ID, ThesesTreeWidget


@pytest.fixture(scope="module")
def qapp():
    yield QApplication.instance() or QApplication([])


@pytest.fixture
def service(tmp_path: Path) -> ThesisService:
    repo = JsonRepository(
        path=tmp_path / "db.json", backup_path=tmp_path / "db.json.bak"
    )
    return ThesisService(repo)


def test_service_toggle_supervisor_printed(service) -> None:
    t = Thesis(type=ThesisType.BP, status=ThesisStatus.IN_PROGRESS,
               academic_year=service.current_academic_year())
    service.upsert_thesis(t)
    assert service.get_thesis(t.id).supervisor_review_printed_at is None
    service.set_supervisor_review_printed(t.id, True)
    assert service.get_thesis(t.id).supervisor_review_printed_at is not None
    service.set_supervisor_review_printed(t.id, False)
    assert service.get_thesis(t.id).supervisor_review_printed_at is None


def test_service_toggle_opponent_printed(service) -> None:
    op = OpposingThesis(type=ThesisType.BP,
                        academic_year=service.current_academic_year(),
                        student_last_name="Novák")
    service.upsert_opposing_thesis(op)
    service.set_opponent_review_printed(op.id, True)
    assert service.get_opposing_thesis(op.id).opponent_review_printed_at is not None


def test_printed_column_position_after_sent() -> None:
    h = ThesesTreeWidget.HEADERS
    assert "Vytištěno" in h
    assert ThesesTreeWidget.COL_PRINTED == h.index("Vytištěno")
    # Vedle „Odesláno" (hned za ním).
    assert ThesesTreeWidget.COL_PRINTED == ThesesTreeWidget.COL_SENT + 1


def _leaf(tree: ThesesTreeWidget, tid: str) -> QTreeWidgetItem:
    found: list[QTreeWidgetItem] = []

    def walk(it: QTreeWidgetItem) -> None:
        for i in range(it.childCount()):
            walk(it.child(i))
        if it.data(0, ROLE_THESIS_ID) == tid:
            found.append(it)

    root = tree.invisibleRootItem()
    for i in range(root.childCount()):
        walk(root.child(i))
    return found[0]


def test_supervised_printed_badge(qapp, service, tmp_path) -> None:
    s = Student(first_name="Jan", last_name="Novák")
    service.upsert_student(s)
    t = Thesis(type=ThesisType.BP, status=ThesisStatus.IN_PROGRESS,
               academic_year=service.current_academic_year(), student_id=s.id)
    service.upsert_thesis(t)
    pdf = tmp_path / "pv.pdf"
    pdf.write_bytes(b"%PDF")
    service.attach_document(t.id, pdf, kind=AttachmentKind.SUPERVISOR_REVIEW)

    tree = ThesesTreeWidget(service)
    tree.refresh()
    col = ThesesTreeWidget.COL_PRINTED
    # nevytištěno → červená (✗)
    assert _leaf(tree, t.id).data(col, ROLE_PRINTED) == UNSENT_BG
    service.set_supervisor_review_printed(t.id, True)
    tree.refresh()
    # vytištěno → zelená (✓)
    assert _leaf(tree, t.id).data(col, ROLE_PRINTED) == SENT_BG


def test_opposing_printed_badge_current_year_only(qapp, service, tmp_path) -> None:
    from bpdpmanager.ui.opposing_tab import ROLE_ID

    year = service.current_academic_year()
    op = OpposingThesis(type=ThesisType.BP, academic_year=year,
                        student_first_name="Petr", student_last_name="Svoboda",
                        title_cs="X")
    service.upsert_opposing_thesis(op)
    pdf = tmp_path / "po.pdf"
    pdf.write_bytes(b"%PDF")
    service.opposing_attach_document(op.id, pdf, kind=AttachmentKind.OPPONENT_REVIEW)

    tab = OpposingTab(service)
    tab.refresh()

    def leaf():
        found = []

        def walk(it):
            for i in range(it.childCount()):
                walk(it.child(i))
            if it.data(0, ROLE_ID):
                found.append(it)

        root = tab.tree.invisibleRootItem()
        for i in range(root.childCount()):
            walk(root.child(i))
        return found[0]

    assert leaf().data(OP_COL_PRINTED, ROLE_PRINTED) == UNSENT_BG
    service.set_opponent_review_printed(op.id, True)
    tab.refresh()
    assert leaf().data(OP_COL_PRINTED, ROLE_PRINTED) == SENT_BG
