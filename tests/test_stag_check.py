"""Testy tiché kontroly STAG (compute_stag_check) — počítání změn / nových prací."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import bpdpmanager.ui.stag_check as chk
from bpdpmanager.models import OpposingThesis, Student, Thesis
from bpdpmanager.models.enums import ThesisStatus, ThesisType
from bpdpmanager.services import ThesisService
from bpdpmanager.services.stag_api import StagThesisResult
from bpdpmanager.storage import JsonRepository


@pytest.fixture
def service(tmp_path: Path) -> ThesisService:
    repo = JsonRepository(path=tmp_path / "db.json", backup_path=tmp_path / "db.json.bak")
    return ThesisService(repo)


def _patch(monkeypatch, fetch_map: dict, search_results=None, search_raises=False):
    def fake_fetch(adip):
        return fetch_map.get(adip, ("", [], ""))

    monkeypatch.setattr(chk, "_fetch_target_state", fake_fetch)

    def fake_search(student, person, role):
        if search_raises:
            raise RuntimeError("offline")
        return search_results or []

    monkeypatch.setattr(chk.stag_api, "search_theses", fake_search)


def test_detects_status_change_and_new_works(service, monkeypatch) -> None:
    s = Student(first_name="Jan", last_name="Novák")
    service.upsert_student(s)
    # Vedená „V řešení" → STAG hlásí obhájeno (DUO) → změna stavu.
    led = Thesis(type=ThesisType.BP, status=ThesisStatus.IN_PROGRESS,
                 academic_year="2024/2025", student_id=s.id, adipidno="111")
    service.upsert_thesis(led)
    # Oponentura akt. roku bez kódu → STAG hlásí DUO → změna.
    op = OpposingThesis(type=ThesisType.DP, academic_year=service.current_academic_year(),
                        student_last_name="Dvořák", adipidno="222")
    service.upsert_opposing_thesis(op)

    _patch(
        monkeypatch,
        fetch_map={"111": ("DUO", [], ""), "222": ("DUO", [], "")},
        search_results=[
            StagThesisResult(adipidno="111", supervisor="Jan Novák"),   # už máš
            StagThesisResult(adipidno="999", supervisor="Jan Novák"),   # nová, moje
            StagThesisResult(adipidno="888", supervisor="Pavel Novák"),  # jmenovec
        ],
    )
    r = chk.compute_stag_check(service, "Jan Novák")
    assert r.ok
    assert r.supervised_changes == 1
    assert r.opposing_changes == 1
    # Jen 999 (111 už máš; 888 je jmenovec Pavel → odfiltrován dle celého jména).
    assert r.new_works == 1
    assert r.total_changes == 3
    # ID dotčených prací — pro tlačítka „Aktualizovat…" v náhledu (subset).
    assert r.supervised_ids == [led.id]
    assert r.opposing_ids == [op.id]


def test_no_changes_all_aktualni(service, monkeypatch) -> None:
    s = Student(first_name="A", last_name="B")
    service.upsert_student(s)
    led = Thesis(type=ThesisType.BP, status=ThesisStatus.IN_PROGRESS,
                 academic_year="2024/2025", student_id=s.id, adipidno="111")
    service.upsert_thesis(led)
    # STAG hlásí „R" (v řešení) = stejný stav, žádné soubory → beze změn.
    _patch(monkeypatch, fetch_map={"111": ("R", [], "")}, search_results=[
        StagThesisResult(adipidno="111"),
    ])
    r = chk.compute_stag_check(service, "Tester")
    assert r.ok
    assert r.total_changes == 0
    assert r.checked == 1
    # Pro debug: zkontrolovaná-a-aktuální práce je vypsaná jmenovitě.
    assert len(r.up_to_date) == 1
    assert "A B" in r.up_to_date[0] and "(vedená)" in r.up_to_date[0]


def test_missing_file_detail_names_kind(service, monkeypatch) -> None:
    """Náhled u nového souboru uvádí KTERÝ druh (ne generické „nový soubor")."""
    from bpdpmanager.services.stag_api import StagFile

    s = Student(first_name="A", last_name="B")
    service.upsert_student(s)
    led = Thesis(type=ThesisType.BP, status=ThesisStatus.IN_PROGRESS,
                 academic_year="2024/2025", student_id=s.id, adipidno="111")
    service.upsert_thesis(led)
    # STAG nabízí posudek oponenta (stejný stav „R") → chybějící druh.
    review = StagFile(soubidno="9", filename="posudek.pdf", download_path="/r",
                      section="opponent_review")
    _patch(monkeypatch, fetch_map={"111": ("R", [review], "")}, search_results=[])
    r = chk.compute_stag_check(service, "")
    assert r.supervised_changes == 1
    assert "Posudek oponenta" in r.supervised[0]
    assert "nový soubor" in r.supervised[0]


def test_missing_defense_record_offered(service, monkeypatch) -> None:
    """Kontrola hlásí i chybějící „Soubor s průběhem obhajoby" (defense_record)."""
    from bpdpmanager.services.stag_api import StagFile

    s = Student(first_name="A", last_name="B")
    service.upsert_student(s)
    led = Thesis(type=ThesisType.BP, status=ThesisStatus.IN_PROGRESS,
                 academic_year="2024/2025", student_id=s.id, adipidno="111")
    service.upsert_thesis(led)
    record = StagFile(soubidno="7", filename="prubeh_obhajoby.pdf",
                      download_path="/p", section="defense_record")
    _patch(monkeypatch, fetch_map={"111": ("R", [record], "")}, search_results=[])
    r = chk.compute_stag_check(service, "")
    assert r.supervised_changes == 1
    assert "Soubor s průběhem obhajoby" in r.supervised[0]


def test_preview_dialog_buttons(service) -> None:
    """Tlačítka náhledu: Aktualizovat vedené/oponované dle změn, Import jen pro nové."""
    from PySide6.QtWidgets import QApplication

    QApplication.instance() or QApplication([])

    r = chk.StagCheckResult(
        ok=True, checked=3,
        supervised=["X — BP · změna stavu"], supervised_ids=["t1"],
        opposing=[], opposing_ids=[],
        new=[],
    )
    dlg = chk.StagChangesPreviewDialog(r)
    assert dlg.btn_sync_sup.isEnabled()
    assert not dlg.btn_sync_opp.isEnabled()
    assert not dlg.btn_import.isEnabled()   # žádné nové práce → import nedává smysl
    dlg.btn_sync_sup.click()
    assert dlg.open_sync_supervised and not dlg.open_sync_opposing


def test_offline_marks_not_ok(service, monkeypatch) -> None:
    s = Student(first_name="A", last_name="B")
    service.upsert_student(s)
    service.upsert_thesis(Thesis(type=ThesisType.BP, status=ThesisStatus.IN_PROGRESS,
                                 academic_year="2024/2025", student_id=s.id, adipidno="111"))
    # Všechny pokusy selžou (fetch i search) → offline.
    _patch(monkeypatch, fetch_map={"111": ("", [], "síť")}, search_raises=True)
    r = chk.compute_stag_check(service, "Tester")
    assert r.ok is False
    assert r.error
