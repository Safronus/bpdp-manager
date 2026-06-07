"""Testy oponentur: známka oponenta z PDF, sloupec Stav, indikace dle roku."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QTreeWidgetItem

import bpdpmanager.services.thesis_service as svc_mod
from bpdpmanager.models import OpposingThesis
from bpdpmanager.models.enums import AttachmentKind, ThesisType
from bpdpmanager.services import ThesisService
from bpdpmanager.storage import JsonRepository
from bpdpmanager.ui.opposing_tab import ROLE_ID, OpposingTab


@pytest.fixture(scope="module")
def qapp():
    yield QApplication.instance() or QApplication([])


@pytest.fixture
def service(tmp_path: Path) -> ThesisService:
    repo = JsonRepository(path=tmp_path / "db.json", backup_path=tmp_path / "db.json.bak")
    return ThesisService(repo)


def test_sync_opponent_grade_from_pdf(service, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(svc_mod, "extract_grade_from_file", lambda p: "B")
    op = OpposingThesis(type=ThesisType.BP, academic_year="2024/2025",
                        student_last_name="Novák")
    service.upsert_opposing_thesis(op)
    pdf = tmp_path / "posudek.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")
    service.opposing_attach_document(op.id, pdf, kind=AttachmentKind.OPPONENT_REVIEW)

    service.sync_opposing_grades(op.id)
    assert service.get_opposing_thesis(op.id).grade_opponent == "B"


def _leaf_for(tab: OpposingTab, op_id: str) -> QTreeWidgetItem | None:
    root = tab.tree.invisibleRootItem()
    for i in range(root.childCount()):
        year = root.child(i)
        for j in range(year.childCount()):
            leaf = year.child(j)
            if leaf.data(0, ROLE_ID) == op_id:
                return leaf
    return None


def test_opposing_grades_use_vo_delegate(qapp, service) -> None:
    """Sloupec V/O nese známky v datech (ROLE_GRADES), text buňky je prázdný."""
    from bpdpmanager.ui.opposing_tab import COL_GRADES
    from bpdpmanager.ui.theses_tree import ROLE_GRADES

    op = OpposingThesis(type=ThesisType.BP, academic_year=service.current_academic_year(),
                        student_last_name="Známkovaný",
                        grade_supervisor="A", grade_opponent="C")
    service.upsert_opposing_thesis(op)

    tab = OpposingTab(service)
    tab.refresh()
    leaf = _leaf_for(tab, op.id)
    assert leaf is not None
    assert tab.tree.headerItem().text(COL_GRADES) == "V/O"
    assert leaf.data(COL_GRADES, ROLE_GRADES) == ("A", "C")
    assert leaf.text(COL_GRADES) == ""


def test_opposing_status_column_and_year_gating(qapp, service) -> None:
    current = service.current_academic_year()
    past = "2018/2019"
    # Aktuální rok, nedokončená, bez posudku → puntík 🔴, stav „nedokončeno".
    cur = OpposingThesis(type=ThesisType.BP, academic_year=current,
                         student_last_name="Aktuální", stag_state_code="ND")
    service.upsert_opposing_thesis(cur)
    # Starší rok — indikace má být potlačená.
    old = OpposingThesis(type=ThesisType.DP, academic_year=past,
                         student_last_name="Stará", stag_state_code="DUO")
    service.upsert_opposing_thesis(old)

    tab = OpposingTab(service)
    tab.refresh()

    cur_leaf = _leaf_for(tab, cur.id)
    old_leaf = _leaf_for(tab, old.id)
    assert cur_leaf is not None and old_leaf is not None
    # Sloupec Stav (index 2) ukazuje krátký popis ze STAG kódu.
    assert "nedokončeno" in cur_leaf.text(2)
    assert "obhájeno" in old_leaf.text(2)
    # Aktuální rok má puntík stavu posudku v názvu, starší ne.
    assert cur_leaf.text(1).startswith("🔴")
    assert not old_leaf.text(1).startswith(("🔴", "🟡", "🟢"))
    # Odesláno (index 6) je u staršího roku prázdné.
    assert old_leaf.text(6) == ""


def test_opposing_previous_years_collapsed(qapp, service) -> None:
    """Aktuální rok rozbalený, starší roky defaultně sbalené."""
    current = service.current_academic_year()
    service.upsert_opposing_thesis(OpposingThesis(
        type=ThesisType.BP, academic_year=current, student_last_name="Cur"))
    service.upsert_opposing_thesis(OpposingThesis(
        type=ThesisType.BP, academic_year="2018/2019", student_last_name="Old"))

    tab = OpposingTab(service)
    tab.refresh()
    root = tab.tree.invisibleRootItem()
    for i in range(root.childCount()):
        year_item = root.child(i)
        if current in year_item.text(0):
            assert year_item.isExpanded()
        elif "2018/2019" in year_item.text(0):
            assert not year_item.isExpanded()
