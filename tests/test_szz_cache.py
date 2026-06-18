"""Testy cache průběhu SZZ (ThesisService.load/save/upsert_szz_results).

Datový adresář izoluje autouse fixtura v conftest.py (env BPDPMANAGER_DATA_DIR),
takže ``_szz_results_path()`` ukazuje do per-test temp složky.
"""

from __future__ import annotations

import json

import pytest

from bpdpmanager.models.szz_result import SubjectExam, SzzOverall, SzzRecord


@pytest.fixture
def service(tmp_path):
    from bpdpmanager.services import ThesisService
    from bpdpmanager.storage import JsonRepository

    repo = JsonRepository(path=tmp_path / "db.json", backup_path=tmp_path / "db.bak")
    return ThesisService(repo)


def test_upsert_and_load_roundtrip(service) -> None:
    rec = SzzRecord(
        os_cislo="A99999",
        subjects=[SubjectExam(predmet="APRX", znamka="A", zkousejici="Jan Z.")],
        overall=SzzOverall(vysledek_zkousek="A", vysledek_studia="Prospěl",
                           komise="fialová"),
    )
    cache = service.upsert_szz_result(rec)
    assert "A99999" in cache
    assert service._szz_results_path().exists()

    r = service.load_szz_results()["A99999"]
    assert r.subjects[0].predmet == "APRX" and r.subjects[0].zkousejici == "Jan Z."
    assert r.overall.komise == "fialová"
    assert r.terminal is True          # má vysledek_studia → hotový
    assert r.fetched_at                # doplněn čas stažení


def test_not_terminal_without_overall(service) -> None:
    service.upsert_szz_result(
        SzzRecord(os_cislo="A11111", subjects=[SubjectExam(predmet="X")]))
    assert service.load_szz_results()["A11111"].terminal is False


def test_upsert_ignores_empty_oscislo(service) -> None:
    service.upsert_szz_result(SzzRecord(os_cislo=""))
    assert service.load_szz_results() == {}


def test_year_mismatch_returns_empty(service) -> None:
    service._szz_results_path().write_text(
        json.dumps({"academic_year": "1999/2000",
                    "results": {"A1": {"os_cislo": "A1"}}}),
        encoding="utf-8")
    assert service.load_szz_results() == {}


def test_corrupt_and_missing_return_empty(service) -> None:
    assert service.load_szz_results() == {}        # chybí soubor
    service._szz_results_path().write_text("{ not json", encoding="utf-8")
    assert service.load_szz_results() == {}        # poškozený


def test_second_upsert_keeps_previous(service) -> None:
    service.upsert_szz_result(SzzRecord(os_cislo="A1"))
    service.upsert_szz_result(SzzRecord(os_cislo="A2"))
    assert set(service.load_szz_results()) == {"A1", "A2"}
