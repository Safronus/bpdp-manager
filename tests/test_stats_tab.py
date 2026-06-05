"""Test statistické záložky — render sekcí z dat."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from bpdpmanager.models import Student, Thesis  # noqa: E402
from bpdpmanager.models.enums import ThesisStatus, ThesisType  # noqa: E402
from bpdpmanager.services import ThesisService  # noqa: E402
from bpdpmanager.storage import JsonRepository  # noqa: E402
from bpdpmanager.ui.stats_tab import StatsTab  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    yield QApplication.instance() or QApplication([])


@pytest.fixture
def service(tmp_path: Path) -> ThesisService:
    repo = JsonRepository(path=tmp_path / "db.json", backup_path=tmp_path / "db.json.bak")
    return ThesisService(repo)


def test_stats_render(qapp, service: ThesisService) -> None:
    s = Student(first_name="A", last_name="B", obor="ITA-P")
    service.upsert_student(s)
    t1 = Thesis(type=ThesisType.BP, academic_year="2024/2025", student_id=s.id,
                status=ThesisStatus.DEFENDED, grade_supervisor="B")
    t2 = Thesis(type=ThesisType.DP, academic_year="2024/2025", student_id=s.id,
                status=ThesisStatus.IN_PROGRESS)
    t3 = Thesis(type=ThesisType.BP, academic_year="2023/2024", student_id=s.id,
                status=ThesisStatus.CANCELLED)
    for t in (t1, t2, t3):
        service.upsert_thesis(t)

    w = StatsTab(service)
    html = w.view.toHtml()
    assert "Souhrn" in html
    assert "Podle stavu" in html
    assert "akademického roku" in html
    assert "Úspěšnost" in html  # má obhájeno + nedokončeno
    assert "Známky" in html     # má obhájenou se známkou


def test_stats_empty(qapp, service: ThesisService) -> None:
    # Bez prací nesmí spadnout
    w = StatsTab(service)
    assert "Souhrn" in w.view.toHtml()
