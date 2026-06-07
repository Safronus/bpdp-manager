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
