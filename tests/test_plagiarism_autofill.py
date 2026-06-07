"""Test automatického předvyplnění komentáře plagiátorství (verdikt + %)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from bpdpmanager.models import Thesis
from bpdpmanager.models.enums import ThesisStatus, ThesisType
from bpdpmanager.services import ThesisService
from bpdpmanager.storage import JsonRepository
from bpdpmanager.ui.thesis_detail import ThesisDetail


@pytest.fixture(scope="module")
def qapp():
    yield QApplication.instance() or QApplication([])


@pytest.fixture
def service(tmp_path: Path) -> ThesisService:
    repo = JsonRepository(path=tmp_path / "db.json", backup_path=tmp_path / "db.json.bak")
    return ThesisService(repo)


def _detail_with_thesis(service):
    t = Thesis(type=ThesisType.BP, academic_year="2024/2025",
               status=ThesisStatus.IN_PROGRESS, title_cs="P")
    service.upsert_thesis(t)
    det = ThesisDetail(service)
    det.set_thesis(t)
    return det


def test_verdict_click_autofills_comment(qapp, service) -> None:
    det = _detail_with_thesis(service)
    det.ed_plag_pct.setText("12.3")
    det.rb_verdict_np.click()
    txt = det.ed_plag_comment.toPlainText()
    assert "12,3 %" in txt and "nejedná se o plagiát" in txt


def test_pct_change_refreshes_auto_comment(qapp, service) -> None:
    det = _detail_with_thesis(service)
    det.ed_plag_pct.setText("12")
    det.rb_verdict_np.click()
    det.ed_plag_pct.setText("15")
    assert "15 %" in det.ed_plag_comment.toPlainText()


def test_manual_comment_not_overwritten(qapp, service) -> None:
    det = _detail_with_thesis(service)
    det.ed_plag_pct.setText("12")
    det.rb_verdict_np.click()
    det.ed_plag_comment.setPlainText("Můj vlastní komentář.")
    det.rb_verdict_pl.click()  # změna verdiktu
    assert det.ed_plag_comment.toPlainText() == "Můj vlastní komentář."


def test_not_assessed_does_not_autofill(qapp, service) -> None:
    det = _detail_with_thesis(service)
    det.ed_plag_pct.setText("12")
    det.rb_verdict_na.click()  # „Neposouzen" → negeneruje
    assert det.ed_plag_comment.toPlainText() == ""
