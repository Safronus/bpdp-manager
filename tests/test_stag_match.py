"""Přísné dohledání STAG ID (services.stag_match) — žádná cizí práce jmenovce."""

from __future__ import annotations

import pytest

from bpdpmanager.services.stag_api import StagThesisResult
from bpdpmanager.services.stag_csv_importer import ImportRole, ParsedRecord
from bpdpmanager.services.stag_match import (
    LocalWork,
    detail_matches,
    name_type_candidates,
    resolve_adipidno,
)


def _res(adip, surname="Novák", name="Jan", typ="Diplomová práce"):
    return StagThesisResult(adipidno=adip, surname=surname, name=name, type_label=typ)


def _rec(uid="A24002", year="2026/2027"):
    return ParsedRecord(role=ImportRole.SUPERVISOR, student_uni_id=uid, academic_year=year)


def test_candidates_need_exact_surname_first_name_and_type() -> None:
    results = [
        _res("1"),                                   # ✓
        _res("2", surname="Nováková"),               # dřív prošlo (podřetězec)
        _res("3", name="Petr"),                      # jiné křestní
        _res("4", typ="Bakalářská práce"),           # jiný typ
        _res("5", name="Jan Petr"),                  # dvojí křestní ⊃ Jan ✓
        _res("1"),                                   # duplicita ve výsledcích
    ]
    work = LocalWork(surname="Novak", type_code="DP", first_name="Jan")
    assert [r.adipidno for r in name_type_candidates(results, work)] == ["1", "5"]


@pytest.mark.parametrize(("work", "rec", "ok"), [
    (LocalWork("Novák", uni_id="A24002", academic_year="2026/2027"), _rec(), True),
    (LocalWork("Novák", uni_id="a24002"), _rec(), True),         # velikost písmen
    (LocalWork("Novák", uni_id="A20001"), _rec(), False),        # jiné os. číslo
    (LocalWork("Novák", academic_year="2025/2026"), _rec(), False),
    (LocalWork("Novák"), _rec(), True),                          # nic neznáme
    (LocalWork("Novák", uni_id="A1"), _rec(uid=""), True),       # CSV bez os. č.
])
def test_detail_matches(work, rec, ok) -> None:
    assert detail_matches(rec, work) is ok


def test_resolve_unique_match_by_uni_id() -> None:
    records = {"1": _rec(uid="A20001"), "2": _rec(uid="A24002")}
    adip, err = resolve_adipidno(
        LocalWork("Novák", "DP", "Jan", uni_id="A24002"), "supervisor", "Vedoucí",
        search=lambda *a: [_res("1"), _res("2")], fetch_record=records.get,
    )
    assert (adip, err) == ("2", "")


def test_resolve_ambiguous_and_not_found() -> None:
    adip, err = resolve_adipidno(
        LocalWork("Novák", "DP", "Jan"), "supervisor",
        search=lambda *a: [_res("1"), _res("2")], fetch_record=lambda a: _rec(),
    )
    assert adip == "" and "nejednoznačné" in err and "2" in err
    adip, err = resolve_adipidno(
        LocalWork("Novák", "DP", "Jan"), "supervisor",
        search=lambda *a: [], fetch_record=lambda a: _rec(),
    )
    assert adip == "" and "nenalezeno" in err


def test_resolve_errors_are_reported_not_raised() -> None:
    def boom(*a):
        raise OSError("offline")

    adip, err = resolve_adipidno(LocalWork("Novák", "DP"), "supervisor", search=boom)
    assert adip == "" and "offline" in err
    # detail kandidáta nejde stáhnout → kandidát není potvrzen
    adip, err = resolve_adipidno(
        LocalWork("Novák", "DP"), "supervisor",
        search=lambda *a: [_res("1")], fetch_record=boom,
    )
    assert adip == "" and "nenalezeno" in err
    assert resolve_adipidno(LocalWork(""), "supervisor")[1].startswith("nelze")
