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
    html = w.rendered_html()
    assert "Souhrn" in html
    assert "akademického roku" in html
    assert "Úspěšnost" in html  # má obhájeno + nedokončeno
    assert "Známky" in html     # má obhájenou se známkou


def test_stats_empty(qapp, service: ThesisService) -> None:
    # Bez prací nesmí spadnout
    w = StatsTab(service)
    assert "Souhrn" in w.rendered_html()


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
    # Známky jsou kompaktní karta s přepínačem 4 pohledů:
    # Vedu já / Jsem oponent / Oponent mých vedených / Vedoucí mých oponovaných.
    assert "Známky" in w.rendered_html()
    assert w._grade_combo.count() == 4
    labels = [w._grade_combo.itemText(i) for i in range(4)]
    assert "Vedu já" in labels and "Jsem oponent" in labels


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
    html = w.rendered_html()
    assert "Soubory (přílohy)" in html
    assert "Podle druhu dokumentu" in html
    assert "Největší práce" in html
    # bez souborů sekce zmizí
    service.delete_thesis(t.id)
    w2 = StatsTab(service)
    assert "Soubory (přílohy)" not in w2.rendered_html()


def test_dashboard_rows_and_no_duplication(qapp, service: ThesisService) -> None:
    """Sekce jsou v řádcích karet; přepočet neduplikuje řádky."""
    s = Student(first_name="A", last_name="B", obor="ITA-P")
    service.upsert_student(s)
    service.upsert_thesis(Thesis(type=ThesisType.BP, academic_year="2024/2025",
                                 student_id=s.id, status=ThesisStatus.DEFENDED,
                                 grade_supervisor="B"))
    w = StatsTab(service)
    assert "Souhrn" in w._kpi_banner.text()      # KPI banner přes celou šířku
    n = w._rows.count()
    assert n >= 3                                # několik řádků sekcí
    w.refresh()
    assert w._rows.count() == n                  # přepočet neduplikuje řádky


def test_dashboard_has_charts(qapp, service: ThesisService) -> None:
    """Grafy se vykreslí — vývoj + koláče (QtCharts) a obory (kreslené sloupce)."""
    from PySide6.QtCharts import QChartView

    from bpdpmanager.ui.stats_tab import _OborBars

    s = Student(first_name="A", last_name="B", obor="ITA-P")
    service.upsert_student(s)
    for yr in ("2024/2025", "2023/2024", "2022/2023"):
        service.upsert_thesis(Thesis(type=ThesisType.BP, academic_year=yr,
                                     student_id=s.id, status=ThesisStatus.DEFENDED,
                                     grade_supervisor="B"))
    service.upsert_thesis(Thesis(type=ThesisType.DP, academic_year="2024/2025",
                                 student_id=s.id, status=ThesisStatus.FAILED))
    w = StatsTab(service)
    charts = w.findChildren(QChartView)
    assert len(charts) >= 2                        # koláč roku + koláč známek
    # Kreslené sloupce: obory BP + DP + vývoj po letech.
    assert len(w.findChildren(_OborBars)) >= 3
    html = w.rendered_html()
    assert "Vývoj počtu" in html and "akademického roku" in html and "Úspěšnost" in html
    assert "Obory" in html                        # panel oborů
