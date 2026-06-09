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
    html = w.rendered_html()
    assert _czk(12 * 3000) in html       # strop vedení
    assert _czk(600) in html             # jeden oponentský posudek
    assert "Aktuálně vedených" in html   # kapacita (text vedle Souhrnu)


def test_rejected_in_stats(qapp, service: ThesisService) -> None:
    from bpdpmanager.ui.stats_tab import StatsTab
    service.upsert_rejected_student(
        RejectedStudent(name="X", obor="ITA-P", academic_year="2025/2026")
    )
    w = StatsTab(service)
    assert "Odmítnut" in w.rendered_html()


def test_dialog_groups_by_academic_year(qapp, service: ThesisService) -> None:
    """Manažer odmítnutých seskupuje podle akademického roku (sestupně)."""
    from bpdpmanager.ui.rejected_students_dialog import RejectedStudentsDialog

    service.upsert_rejected_student(RejectedStudent(name="A", academic_year="2024/2025"))
    service.upsert_rejected_student(RejectedStudent(name="B", academic_year="2026/2027"))
    service.upsert_rejected_student(RejectedStudent(name="C", academic_year="2026/2027"))
    service.upsert_rejected_student(RejectedStudent(name="D", academic_year=""))

    dlg = RejectedStudentsDialog(service)
    tree = dlg.tree
    # Top-level = roky, sestupně, „bez roku" na konci.
    years = [tree.topLevelItem(i).text(0) for i in range(tree.topLevelItemCount())]
    assert tree.topLevelItemCount() == 3
    assert "2026/2027" in years[0] and "(2)" in years[0]   # 2 odmítnutí
    assert "2024/2025" in years[1]
    assert "(bez roku)" in years[2]
    # Děti nesou ID odmítnutého (skupinový řádek ne).
    head_2026 = tree.topLevelItem(0)
    assert head_2026.childCount() == 2
    from PySide6.QtCore import Qt
    assert head_2026.child(0).data(0, Qt.ItemDataRole.UserRole)  # má ID
    assert head_2026.data(0, Qt.ItemDataRole.UserRole) is None   # hlavička bez ID
