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


def test_export_import_roundtrip(service, tmp_path) -> None:
    service.upsert_szz_result(SzzRecord(
        os_cislo="A100",
        subjects=[SubjectExam(predmet="AZINF", znamka="A", zkousejici="Novák")],
        overall=SzzOverall(komise="fialová", vysledek_zkousek="A")))
    service.upsert_szz_result(SzzRecord(os_cislo="A101"))
    path = tmp_path / "export.szzenc"
    assert service.export_szz_results(path, "tajne") == 2
    assert path.exists() and b"AZINF" not in path.read_bytes()   # šifrované

    service.save_szz_results({})                 # vymaž cache
    assert service.load_szz_results() == {}
    n, year = service.import_szz_results(path, "tajne")
    assert n == 2 and year == service.current_academic_year()
    cache = service.load_szz_results()
    assert set(cache) == {"A100", "A101"}
    assert cache["A100"].subjects[0].predmet == "AZINF"


def test_import_wrong_password_raises(service, tmp_path) -> None:
    service.upsert_szz_result(SzzRecord(os_cislo="A1"))
    path = tmp_path / "e.szzenc"
    service.export_szz_results(path, "spravne")
    with pytest.raises(ValueError):
        service.import_szz_results(path, "spatne")


def test_export_empty_password_raises(service, tmp_path) -> None:
    service.upsert_szz_result(SzzRecord(os_cislo="A1"))
    with pytest.raises(ValueError):
        service.export_szz_results(tmp_path / "e.szzenc", "")


def _two_committees(service):
    from bpdpmanager.models.komise import Committee, DefenseSlot
    yr = service.current_academic_year()
    service._db.committees = [
        Committee(id="c1", color="fialová", academic_year=yr, slots=[
            DefenseSlot(personal_number="A100", student_name="Jan Novák"),
            DefenseSlot(personal_number="A200", student_name="Eva Malá")]),
        Committee(id="c2", color="modrá", academic_year=yr, slots=[
            DefenseSlot(personal_number="A200", student_name="Eva Malá")]),  # sdílí A200
    ]
    service.save()


def test_delete_committee_purges_stats(service) -> None:
    _two_committees(service)
    for oc in ("A100", "A200", "A300"):
        service.upsert_szz_result(SzzRecord(os_cislo=oc))
    service.save_komise_defense_states(
        {"A100": "defended", "A200": "defended", "A300": "none"})

    n = service.delete_committee("c1", purge_stats=True)
    assert n == 1                                       # jen A100 (A200 sdílí c2)
    assert set(service.load_szz_results()) == {"A200", "A300"}   # A100 pryč
    assert service.load_komise_defense_states() == {
        "A200": "defended", "A300": "none"}
    assert [c.id for c in service.list_committees()] == ["c2"]


def test_delete_committee_without_purge_keeps_stats(service) -> None:
    _two_committees(service)
    service.upsert_szz_result(SzzRecord(os_cislo="A100"))
    n = service.delete_committee("c1")                  # default = bez purge
    assert n == 0 and "A100" in service.load_szz_results()


def test_corrupt_and_missing_return_empty(service) -> None:
    assert service.load_szz_results() == {}        # chybí soubor
    service._szz_results_path().write_text("{ not json", encoding="utf-8")
    assert service.load_szz_results() == {}        # poškozený


def test_second_upsert_keeps_previous(service) -> None:
    service.upsert_szz_result(SzzRecord(os_cislo="A1"))
    service.upsert_szz_result(SzzRecord(os_cislo="A2"))
    assert set(service.load_szz_results()) == {"A1", "A2"}
