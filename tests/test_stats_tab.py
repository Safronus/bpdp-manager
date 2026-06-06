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


def test_stats_opponent_grades_and_opposing_summary(qapp, service: ThesisService) -> None:
    from bpdpmanager.models import OpposingThesis

    s = Student(first_name="A", last_name="B", obor="ITA-P")
    service.upsert_student(s)
    # Obhájená vedená práce se známkou vedoucího i oponenta.
    service.upsert_thesis(Thesis(
        type=ThesisType.BP, academic_year="2024/2025", student_id=s.id,
        status=ThesisStatus.DEFENDED, grade_supervisor="A", grade_opponent="B",
    ))
    # Oponentury (mnou hodnocené).
    service.upsert_opposing_thesis(OpposingThesis(
        type=ThesisType.DP, academic_year="2024/2025",
        student_last_name="Dvořák", grade_opponent="C",
    ))

    w = StatsTab(service)
    html = w.view.toHtml()
    assert "Navržené vedoucím" in html
    assert "Navržené oponentem" in html      # známky oponenta u vedených prací
    assert "Oponentury" in html              # souhrn oponovaných prací
    assert "Mnou navržené známky" in html     # moje známky jako oponent


def test_stats_palette_muted_color_set(qapp, service: ThesisService) -> None:
    w = StatsTab(service)
    assert w._muted and w._border  # barvy dle motivu nastaveny


def test_stats_files_section(qapp, service: ThesisService, tmp_path: Path) -> None:
    from bpdpmanager.models.enums import AttachmentKind

    s = Student(first_name="Jan", last_name="Novák")
    service.upsert_student(s)
    t = Thesis(type=ThesisType.BP, academic_year="2024/2025", student_id=s.id,
               status=ThesisStatus.IN_PROGRESS)
    service.upsert_thesis(t)
    src = tmp_path / "text.pdf"
    src.write_bytes(b"x" * 100_000)
    service.attach_document(t.id, src, kind=AttachmentKind.THESIS_TEXT)

    w = StatsTab(service)
    html = w.view.toHtml()
    assert "Soubory (přílohy)" in html
    assert "Podle druhu dokumentu" in html
    assert "Největší práce" in html
    # bez souborů sekce zmizí
    service.delete_thesis(t.id)
    w2 = StatsTab(service)
    assert "Soubory (přílohy)" not in w2.view.toHtml()
