"""Testy evidence odmítnutých zájemců + promítnutí do statistik (odměny, kapacita)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from bpdpmanager.models import RejectedStudent, Thesis  # noqa: E402
from bpdpmanager.models.enums import ThesisStatus, ThesisType  # noqa: E402
from bpdpmanager.services import ThesisService  # noqa: E402
from bpdpmanager.storage import JsonRepository  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    yield QApplication.instance() or QApplication([])


@pytest.fixture
def service(tmp_path: Path) -> ThesisService:
    repo = JsonRepository(path=tmp_path / "db.json", backup_path=tmp_path / "db.json.bak")
    return ThesisService(repo)


def test_rejected_crud(service: ThesisService) -> None:
    r = RejectedStudent(name="Jan Novák", obor="ITA-P", academic_year="2025/2026")
    service.upsert_rejected_student(r)
    assert len(service.list_rejected_students()) == 1
    service.remove_rejected_student(r.id)
    assert service.list_rejected_students() == []


def test_finance_cap_and_opposing(qapp, service: ThesisService) -> None:
    from bpdpmanager.models import OpposingThesis
    from bpdpmanager.ui.stats_tab import _czk
    from bpdpmanager.ui.stats_tab import StatsTab

    # 13 obhájených v jednom roce → honoruje se jen 12 × 3000.
    for _ in range(13):
        service.upsert_thesis(Thesis(type=ThesisType.BP, academic_year="2024/2025",
                                     status=ThesisStatus.DEFENDED))
    service.upsert_opposing_thesis(
        OpposingThesis(type=ThesisType.BP, academic_year="2024/2025")
    )
    w = StatsTab(service)
    html = w.view.toHtml()
    assert _czk(12 * 3000) in html       # strop vedení
    assert _czk(600) in html             # jeden oponentský posudek
    assert "Kapacita vedení" in html


def test_rejected_in_stats(qapp, service: ThesisService) -> None:
    from bpdpmanager.ui.stats_tab import StatsTab
    service.upsert_rejected_student(
        RejectedStudent(name="X", obor="ITA-P", academic_year="2025/2026")
    )
    w = StatsTab(service)
    assert "Odmítnut" in w.view.toHtml()
