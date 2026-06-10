"""Přepínání jazyka CZ/EN — tr(), enumy, fallback, EN smoke hlavní plochy."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from bpdpmanager import i18n
from bpdpmanager.i18n import set_language, tr


@pytest.fixture(autouse=True)
def _reset_language():
    """Každý test začíná i končí v češtině (default; neovlivnit ostatní testy)."""
    set_language("cs")
    yield
    set_language("cs")


def test_default_is_czech_identity() -> None:
    assert i18n.get_language() == "cs"
    assert tr("Vedené práce") == "Vedené práce"


def test_english_translates() -> None:
    set_language("en")
    assert tr("Vedené práce") == "Supervised theses"
    assert tr("Historie") == "History"


def test_untranslated_falls_back_to_czech() -> None:
    set_language("en")
    assert tr("Tohle nikdo nepřeložil") == "Tohle nikdo nepřeložil"


def test_unknown_language_falls_back_to_czech() -> None:
    set_language("klingon")
    assert i18n.get_language() == "cs"


def test_enum_labels_translate() -> None:
    from bpdpmanager.models.enums import StudyForm, ThesisStatus, ThesisType

    assert ThesisStatus.IN_PROGRESS.label == "V řešení"
    set_language("en")
    assert ThesisStatus.IN_PROGRESS.label == "In progress"
    assert ThesisType.BP.label == "Bachelor's thesis"
    assert StudyForm.COMBINED.label == "Part-time"
    set_language("cs")
    assert ThesisStatus.IN_PROGRESS.label == "V řešení"   # zpět beze změny


def test_stats_tab_renders_english(tmp_path: Path) -> None:
    """EN smoke: dashboard Statistik se vykreslí anglicky (titulky panelů)."""
    from PySide6.QtWidgets import QApplication

    QApplication.instance() or QApplication([])

    from bpdpmanager.models import Student, Thesis
    from bpdpmanager.models.enums import ThesisStatus, ThesisType
    from bpdpmanager.services import ThesisService
    from bpdpmanager.storage import JsonRepository
    from bpdpmanager.ui.stats_tab import StatsTab

    repo = JsonRepository(path=tmp_path / "db.json", backup_path=tmp_path / "db.bak")
    service = ThesisService(repo)
    s = Student(first_name="A", last_name="B", obor="SWI-P")
    service.upsert_student(s)
    service.upsert_thesis(Thesis(type=ThesisType.BP, academic_year="2024/2025",
                                 student_id=s.id, status=ThesisStatus.DEFENDED,
                                 grade_supervisor="A"))
    set_language("en")
    w = StatsTab(service)
    html = w.rendered_html()
    assert "Summary" in html
    assert "By academic year" in html
    assert "Theses per year over time" in html
    assert "Souhrn" not in html


def test_theses_tree_headers_english(tmp_path: Path) -> None:
    from PySide6.QtWidgets import QApplication

    QApplication.instance() or QApplication([])

    from bpdpmanager.services import ThesisService
    from bpdpmanager.storage import JsonRepository
    from bpdpmanager.ui.theses_tree import ThesesTreeWidget

    repo = JsonRepository(path=tmp_path / "db.json", backup_path=tmp_path / "db.bak")
    set_language("en")
    tree = ThesesTreeWidget(ThesisService(repo))
    assert tree.headerItem().text(0) == "Student / Group"
    assert tree.headerItem().text(2) == "Status"


def test_thesis_detail_english(tmp_path: Path) -> None:
    """EN smoke vlny 2: detail práce má anglické záložky a tlačítka."""
    from PySide6.QtWidgets import QApplication

    QApplication.instance() or QApplication([])

    from bpdpmanager.services import ThesisService
    from bpdpmanager.storage import JsonRepository
    from bpdpmanager.ui.thesis_detail import ThesisDetail

    repo = JsonRepository(path=tmp_path / "db.json", backup_path=tmp_path / "db.bak")
    set_language("en")
    w = ThesisDetail(ThesisService(repo))
    titles = [w.tabs.tabText(i) for i in range(w.tabs.count())]
    assert "📋 Overview" in titles and "Notes" in titles
    assert w.btn_save.text() == "Save changes"
    assert w.btn_delete.text() == "Delete"
