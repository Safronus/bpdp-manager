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
    # Strom: rok → podskupina BP/DP → list. Projdeme do hloubky.
    stack = [tab.tree.invisibleRootItem().child(i)
             for i in range(tab.tree.invisibleRootItem().childCount())]
    while stack:
        item = stack.pop()
        if item.data(0, ROLE_ID) == op_id:
            return item
        for j in range(item.childCount()):
            stack.append(item.child(j))
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
    assert tab.tree.headerItem().text(COL_GRADES) == "Známky V/O"
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
    # Sloupec Stav (index 2) je zaoblený badge — popisek je v datech ROLE_STATUS,
    # text buňky je prázdný (stejný styl jako v ostatních záložkách).
    from bpdpmanager.ui.theses_tree import ROLE_STATUS

    assert cur_leaf.text(2) == "" and old_leaf.text(2) == ""
    assert cur_leaf.data(2, ROLE_STATUS)[0] == "Nedokončeno"
    assert old_leaf.data(2, ROLE_STATUS)[0] == "Obhájeno"
    # Aktuální rok má puntík stavu posudku v názvu, starší ne.
    assert cur_leaf.text(1).startswith("🔴")
    assert not old_leaf.text(1).startswith(("🔴", "🟡", "🟢"))
    # Odesláno je u staršího roku prázdné; Obor je poslední sloupec (index 7).
    from bpdpmanager.ui.opposing_tab import COL_OBOR, COL_SENT

    assert old_leaf.text(COL_SENT) == ""
    # Obor je poslední sloupec (za Posudky + Odesláno + Vytištěno).
    assert COL_OBOR == 8


def test_opposing_context_menu_has_write_review(qapp, service) -> None:
    """Kontextové menu oponentur obsahuje akci „Napsat posudek" (role oponent)."""
    op = OpposingThesis(type=ThesisType.BP, academic_year=service.current_academic_year(),
                        student_last_name="Aktuální")
    service.upsert_opposing_thesis(op)
    tab = OpposingTab(service)
    tab.refresh()

    # Sestavíme menu přímo (bez exec, ať test neblokuje na modálu).
    menu = tab._build_context_menu(op.id)
    assert menu is not None
    actions = menu.actions()
    texts = [a.text() for a in actions]
    write = [a for a in actions if "Napsat posudek" in a.text()]
    assert write, f"Akce 'Napsat posudek' chybí v menu: {texts}"
    assert write[0].isEnabled()


def test_opposing_summary_excludes_archived_attachments(qapp, service, tmp_path) -> None:
    """Souhrn oponentury ukazuje jen AKTUÁLNÍ přílohy, ne archiv starších verzí."""
    from bpdpmanager.ui.opposing_detail import OpposingDetail

    op = OpposingThesis(type=ThesisType.BP, academic_year=service.current_academic_year(),
                        student_last_name="Novák")
    service.upsert_opposing_thesis(op)
    # Dvojí nahrání posudku → první se zarchivuje (is_current=False).
    for i in (1, 2):
        f = tmp_path / f"p{i}.pdf"
        f.write_bytes(b"%PDF")
        service.opposing_attach_document(op.id, f, kind=AttachmentKind.OPPONENT_REVIEW)
    op = service.get_opposing_thesis(op.id)
    archived = [a for a in op.attachments if not a.is_current]
    current = [a for a in op.attachments if a.is_current]
    assert len(archived) == 1 and len(current) == 1

    det = OpposingDetail(service)
    html = det._build_summary_html(op)
    assert current[0].label in html          # aktuální posudek je v souhrnu
    assert archived[0].label not in html      # archivovaná verze NE


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
