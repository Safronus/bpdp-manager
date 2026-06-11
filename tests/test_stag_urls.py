"""Odkaz na práci ve STAG — builder, backfill, kontextová akce."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from bpdpmanager.models import OpposingThesis, Student, Thesis
from bpdpmanager.models.enums import ThesisStatus, ThesisType
from bpdpmanager.services import ThesisService, stag_api
from bpdpmanager.storage import JsonRepository


@pytest.fixture
def service(tmp_path: Path) -> ThesisService:
    repo = JsonRepository(path=tmp_path / "db.json", backup_path=tmp_path / "db.bak")
    return ThesisService(repo)


def test_thesis_detail_url_builder() -> None:
    assert stag_api.thesis_detail_url("54424") == (
        "https://stag.utb.cz/StagPortletsJSR168/CleanUrl"
        "?urlid=prohlizeni-prace-detail&praceIdno=54424"
    )


def test_ensure_stag_urls_backfills(service: ThesisService) -> None:
    """Existující práce se STAG ID dostanou odkaz; bez ID / s odkazem se nemění."""
    t1 = Thesis(type=ThesisType.BP, academic_year="2023/2024",
                status=ThesisStatus.DEFENDED, adipidno="54424")
    t2 = Thesis(type=ThesisType.BP, academic_year="2023/2024",
                status=ThesisStatus.DEFENDED)                      # bez STAG ID
    t3 = Thesis(type=ThesisType.DP, academic_year="2023/2024",
                status=ThesisStatus.DEFENDED, adipidno="99",
                stag_url="https://example.com/custom")             # ruční odkaz
    for t in (t1, t2, t3):
        service.upsert_thesis(t)
    op = OpposingThesis(type=ThesisType.DP, academic_year="2024/2025",
                        student_last_name="X", adipidno="777")
    service.upsert_opposing_thesis(op)

    filled = service.ensure_stag_urls()
    assert filled == 2                                             # t1 + op
    assert service.get_thesis(t1.id).stag_url.endswith("praceIdno=54424")
    assert service.get_thesis(t2.id).stag_url == ""
    assert service.get_thesis(t3.id).stag_url == "https://example.com/custom"
    assert service.get_opposing_thesis(op.id).stag_url.endswith("praceIdno=777")
    assert service.ensure_stag_urls() == 0                         # idempotentní


def test_stag_action_in_menus(service: ThesisService) -> None:
    from PySide6.QtWidgets import QApplication

    QApplication.instance() or QApplication([])

    from bpdpmanager.ui.theses_tree import ROLE_THESIS_ID, ThesesTreeWidget

    s = Student(first_name="A", last_name="B")
    service.upsert_student(s)
    t = Thesis(type=ThesisType.BP, academic_year="2024/2025", student_id=s.id,
               status=ThesisStatus.IN_PROGRESS, adipidno="54424")
    service.upsert_thesis(t)
    tree = ThesesTreeWidget(service)
    tree.refresh()

    leaves = []

    def walk(item):
        for i in range(item.childCount()):
            walk(item.child(i))
        if item.data(0, ROLE_THESIS_ID):
            leaves.append(item)

    root = tree.invisibleRootItem()
    for i in range(root.childCount()):
        walk(root.child(i))
    leaves[0].setSelected(True)
    menu = tree._build_context_menu(leaves[0])
    labels = [a.text() for a in menu.actions() if not a.isSeparator()]
    assert any("Otevřít ve STAG" in x for x in labels)
    act = next(a for a in menu.actions() if "Otevřít ve STAG" in a.text())
    assert act.isEnabled()                       # má adipidno → aktivní
