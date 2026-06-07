"""Test předvýběru šablony posudku podle oboru práce (SWI-P → SWI, ne ITA)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from bpdpmanager.models import Student, Thesis
from bpdpmanager.models.enums import ThesisType
from bpdpmanager.services import ThesisService
from bpdpmanager.storage import JsonRepository
from bpdpmanager.ui.review_templates_dialog import GenerateReviewDialog


@pytest.fixture(scope="module")
def qapp():
    yield QApplication.instance() or QApplication([])


@pytest.fixture
def service(tmp_path: Path) -> ThesisService:
    repo = JsonRepository(path=tmp_path / "db.json", backup_path=tmp_path / "db.json.bak")
    svc = ThesisService(repo)
    svc.seed_default_templates()
    return svc


def _selected_template(dlg: GenerateReviewDialog):
    item = dlg.tree.currentItem()
    assert item is not None, "Žádná šablona není předvybraná"
    tid = item.data(0, Qt.ItemDataRole.UserRole)
    return dlg.service.get_review_template(tid)


def _make_thesis(service: ThesisService, obor: str, ttype: ThesisType) -> Thesis:
    s = Student(first_name="Jan", last_name="Novák", obor=obor)
    service.upsert_student(s)
    t = Thesis(type=ttype, academic_year=service.current_academic_year(),
               student_id=s.id, title_cs="Práce")
    service.upsert_thesis(t)
    return t


def test_bp_swi_p_preselects_swi_not_ita(qapp, service) -> None:
    """U BP práce s oborem SWI-P se předvybere šablona SWI (ne abecedně první ITA)."""
    t = _make_thesis(service, "SWI-P", ThesisType.BP)
    dlg = GenerateReviewDialog(service, t)
    tmpl = _selected_template(dlg)
    assert tmpl.obor == "SWI"
    assert tmpl.role == "supervisor"
    assert "-P" not in tmpl.name and "-K" not in tmpl.name


def test_dp_nswi_p_preselects_swi_discipline(qapp, service) -> None:
    """U DP práce s oborem NSWI-P se obor normalizuje na SWI (jako u šablon)."""
    t = _make_thesis(service, "NSWI-P", ThesisType.DP)
    dlg = GenerateReviewDialog(service, t)
    tmpl = _selected_template(dlg)
    assert tmpl.obor == "SWI" and tmpl.type == ThesisType.DP
    assert tmpl.role == "supervisor"


def test_dp_nkyb_k_preselects_kyb(qapp, service) -> None:
    """Kombinovaná forma (-K) i N-prefix se normalizují: NKYB-K → KYB."""
    t = _make_thesis(service, "NKYB-K", ThesisType.DP)
    dlg = GenerateReviewDialog(service, t)
    tmpl = _selected_template(dlg)
    assert tmpl.obor == "KYB" and tmpl.type == ThesisType.DP
