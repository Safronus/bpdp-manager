"""Přísné dohledání STAG ID (adipIdno) pro práci, která ho ještě nemá.

Dřív „Aktualizace práce ze STAG" hledala jen podle příjmení studenta a typu
a vzala **první** shodu — u častého příjmení tak mohla k práci natrvalo uložit
STAG ID cizí práce (jmenovce). Teď:

1. hledá se mezi pracemi uživatele (příjmení vedoucího/oponenta z profilu),
2. kandidát musí mít **přesně** stejné příjmení, křestní jméno (je-li známé)
   a typ (BP/DP),
3. každý kandidát se ověří z CSV detailu — **osobní číslo** a **akademický
   rok** (jsou-li u lokální práce známé) se nesmí lišit,
4. STAG ID se vrátí jen při **jediné** shodě; jinak chyba „nenalezeno" /
   „nejednoznačné" (spárovat pak jde importem ze STAG).
"""

from __future__ import annotations

import unicodedata
from collections.abc import Callable
from dataclasses import dataclass

from . import stag_api
from .stag_csv_importer import ParsedRecord, load_stag_csv_bytes


def _fold(s: str | None) -> str:
    nfd = unicodedata.normalize("NFD", s or "")
    return " ".join("".join(c for c in nfd if not unicodedata.combining(c)).casefold().split())


@dataclass(frozen=True)
class LocalWork:
    """Co o lokální práci víme (prázdné = neznámé, nekontroluje se)."""

    surname: str
    type_code: str = ""        # "BP" / "DP"
    first_name: str = ""
    uni_id: str = ""           # osobní číslo studenta
    academic_year: str = ""    # „RRRR/RRRR"


def _result_type(r: stag_api.StagThesisResult) -> str:
    label = (r.type_label or "").lower()
    if "diplom" in label:
        return "DP"
    if "bakal" in label:
        return "BP"
    return ""


def name_type_candidates(
    results: list[stag_api.StagThesisResult], work: LocalWork
) -> list[stag_api.StagThesisResult]:
    """Výsledky hledání se shodným příjmením, křestním jménem a typem."""
    surname = _fold(work.surname)
    first = _fold(work.first_name).split()
    out = []
    seen: set[str] = set()
    for r in results:
        if not r.adipidno or r.adipidno in seen:
            continue
        rtype = _result_type(r)
        if work.type_code and rtype and rtype != work.type_code:
            continue
        if not surname or _fold(r.surname) != surname:
            continue
        # Křestní: první jméno lokálně musí být mezi jmény ve STAG (Jan ⊂ Jan Petr).
        if first and first[0] not in _fold(r.name).split():
            continue
        seen.add(r.adipidno)
        out.append(r)
    return out


def detail_matches(record: ParsedRecord, work: LocalWork) -> bool:
    """CSV detail kandidáta nesmí odporovat známému os. číslu a roku."""
    if work.uni_id and record.student_uni_id.strip() and (
        record.student_uni_id.strip().casefold() != work.uni_id.strip().casefold()
    ):
        return False
    return not (
        work.academic_year and record.academic_year
        and record.academic_year != work.academic_year
    )


def _fetch_record(adipidno: str) -> ParsedRecord | None:
    imp = load_stag_csv_bytes(stag_api.download_csv(adipidno))
    return imp.records[0] if imp.records else None


def resolve_adipidno(
    work: LocalWork,
    person_role: str,
    person_surname: str = "",
    *,
    search: Callable[..., list[stag_api.StagThesisResult]] | None = None,
    fetch_record: Callable[[str], ParsedRecord | None] | None = None,
) -> tuple[str, str]:
    """Vrátí ``(adipidno, chyba)`` — právě jedno z nich je neprázdné."""
    search = search or stag_api.search_theses
    fetch_record = fetch_record or _fetch_record
    if not work.surname.strip():
        return "", "nelze dohledat ve STAG — chybí příjmení studenta"
    try:
        results = search(work.surname, person_surname, person_role)
    except Exception as exc:  # síť/parser → chyba pro uživatele
        return "", f"hledání ve STAG selhalo: {exc}"
    candidates = name_type_candidates(results, work)
    confirmed = []
    for r in candidates:
        try:
            rec = fetch_record(r.adipidno)
        except Exception:  # detail nejde ověřit → kandidát nepotvrzen
            continue
        if rec is not None and detail_matches(rec, work):
            confirmed.append(r)
    if len(confirmed) == 1:
        return confirmed[0].adipidno, ""
    if not confirmed:
        return "", "nenalezeno ve STAG (chybí STAG ID a žádná jednoznačná shoda)"
    return "", (f"nejednoznačné — ve STAG {len(confirmed)} odpovídající práce; "
                "STAG ID se neuložilo, spáruj práci importem ze STAG")
