"""Testy editoru posudku: nezaseknutí progresu generování + jazykové volby."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QPushButton

from bpdpmanager.models import Review, Student, Thesis
from bpdpmanager.models.enums import ThesisType
from bpdpmanager.services import ThesisService
from bpdpmanager.storage import JsonRepository
from bpdpmanager.ui.review_editor_dialog import ReviewEditorDialog


@pytest.fixture(scope="module")
def qapp():
    yield QApplication.instance() or QApplication([])


@pytest.fixture
def service(tmp_path: Path) -> ThesisService:
    repo = JsonRepository(path=tmp_path / "db.json", backup_path=tmp_path / "db.json.bak")
    return ThesisService(repo)


def _thesis(service: ThesisService, obor: str = "SWI-P") -> Thesis:
    s = Student(first_name="Jan", last_name="Novák", obor=obor)
    service.upsert_student(s)
    t = Thesis(type=ThesisType.BP, academic_year=service.current_academic_year(),
               student_id=s.id, title_cs="Práce")
    service.upsert_thesis(t)
    return t


def _review(role: str = "supervisor", language: str = "cs") -> Review:
    return Review(template_id="tid", template_name="Vedoucí BP — SWI",
                  role=role, language=language, type=ThesisType.BP, criteria=[])


def test_save_and_generate_closes_progress(qapp, service, tmp_path, monkeypatch) -> None:
    """Regrese: po vygenerování se progress ZAVŘE (dřív visel na reset())."""
    t = _thesis(service)
    fake_xlsx = tmp_path / "p.xlsx"
    fake_xlsx.write_bytes(b"x")
    fake_pdf = tmp_path / "p.pdf"
    fake_pdf.write_bytes(b"%PDF")

    # Generování zmockujeme (žádný LibreOffice) — vrátí hned.
    monkeypatch.setattr(
        service, "generate_review_files",
        lambda *a, **k: (fake_xlsx, fake_pdf),
    )
    dlg = ReviewEditorDialog(service, t.id, _review(), opposing=False)
    # Souhrnný dialog nahradíme no-opem, ať test neblokuje na modálu.
    dlg._show_done_dialog = lambda *a, **k: None

    # Když by se progress nezavřel, exec() by zde visel donekonečna
    # (a test by spadl na timeoutu CI). Doběhnutí = oprava funguje.
    dlg._save_and_generate()

    assert dlg.saved is True
    assert dlg.generated_xlsx == fake_xlsx
    assert dlg.generated_pdf == fake_pdf


def test_fulfilled_options_follow_template_language(qapp, service) -> None:
    """„Stav" nabízí jen volby dle jazyka šablony (ne všechny 4)."""
    t = _thesis(service)

    dlg_cs = ReviewEditorDialog(service, t.id, _review(language="cs"), opposing=False)
    cs_opts = [dlg_cs.cb_fulfilled.itemData(i) for i in range(dlg_cs.cb_fulfilled.count())]
    assert cs_opts == ["splnil(a)", "nesplnil(a)"]

    dlg_en = ReviewEditorDialog(service, t.id, _review(language="en"), opposing=False)
    en_opts = [dlg_en.cb_fulfilled.itemData(i) for i in range(dlg_en.cb_fulfilled.count())]
    assert en_opts == ["fulfilled", "not fulfilled"]


def test_build_review_skeleton_role_and_language() -> None:
    """Kostra se liší rolí (vedoucí má řádek o studentovi) a jazykem."""
    from bpdpmanager.ui.review_editor_dialog import build_review_skeleton

    sup_cs = build_review_skeleton("supervisor", "cs")
    opp_cs = build_review_skeleton("opponent", "cs")
    assert "Splnění bodů zadání:" in sup_cs and "Dotazy a připomínky:" in sup_cs
    assert "spolupráce studenta" in sup_cs            # jen u vedoucího
    assert "spolupráce studenta" not in opp_cs        # oponent ne
    en = build_review_skeleton("opponent", "en")
    assert "Questions and comments:" in en


def test_insert_skeleton_into_empty_overall(qapp, service) -> None:
    """Tlačítko vloží kostru do prázdného pole Celkové hodnocení."""
    t = _thesis(service)
    dlg = ReviewEditorDialog(service, t.id, _review(role="supervisor"), opposing=False)
    dlg.ed_overall.setPlainText("")
    dlg._insert_skeleton()
    assert "Splnění bodů zadání:" in dlg.ed_overall.toPlainText()


def test_editor_has_open_text_and_opposite_review_buttons(qapp, service) -> None:
    """Editor má tlačítka pro otevření textu práce a opačného posudku."""
    t = _thesis(service)
    dlg = ReviewEditorDialog(service, t.id, _review(role="supervisor"), opposing=False)
    labels = [b.text() for b in dlg.findChildren(QPushButton)]
    assert any("Otevřít text práce" in s for s in labels)
    # u posudku vedoucího je protější tlačítko „posudek oponenta"
    assert any("posudek oponenta" in s for s in labels)


def test_editor_height_fits_within_screen(qapp, service) -> None:
    """Výška okna se přizpůsobí obsahu, ale nepřekročí obrazovku."""
    t = _thesis(service)
    dlg = ReviewEditorDialog(service, t.id, _review(), opposing=False)
    screen = dlg.screen()
    if screen is not None:
        avail = screen.availableGeometry().height()
        assert dlg.height() <= int(avail * 0.95) + 1
    assert dlg.height() >= dlg.minimumHeight()
