"""Import dat ze STAG CSV exportu (formát ``getKvalifikacniPrace*.csv``).

Parser pouze čte a normalizuje data do strukturovaných záznamů; samotný
import (vytvoření/aktualizace v databázi) provádí ImportDialog s pomocí
``ThesisService``.

Identifikuje per řádek **role uživatele**:
- pokud se ``user_name`` najde v ``vedouciJmeno`` → role *Vedoucí*
- pokud se ``user_name`` najde v ``oponentJmeno`` → role *Oponent*
- jinak → nelze určit (uživatel rozhodne ručně, default ``Vedoucí``)
"""

from __future__ import annotations

import csv
import html
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any

# ── Encoding ─────────────────────────────────────────────────────────────────
# STAG export typicky používá Windows-1250. Zkusíme i UTF-8.
_ENCODINGS = ("utf-8-sig", "utf-8", "cp1250", "windows-1250", "iso-8859-2")

# ── Delimiter ────────────────────────────────────────────────────────────────
_DELIMITER = ";"


class ImportRole(str, Enum):
    SUPERVISOR = "supervisor"  # já jsem vedoucí
    OPPONENT = "opponent"      # já jsem oponent
    UNKNOWN = "unknown"        # nelze určit z dat


@dataclass
class ParsedRecord:
    """Jeden řádek STAG CSV po normalizaci."""

    role: ImportRole

    # Student
    student_uni_id: str = ""        # osCislo.student (A24469)
    student_first: str = ""
    student_last: str = ""
    student_title_pre: str = ""
    student_title_post: str = ""
    student_obor_stag: str = ""     # např. "knIT-KYB"

    # Typ + identifikace práce
    type_code: str = "DP"           # "BP" / "DP"
    adipidno: str = ""              # interní STAG ID práce
    academic_year: str = ""         # derived: "2025/2026"

    # Téma
    title_cs: str = ""
    title_en: str = ""
    annotation_cs: str = ""
    annotation_en: str = ""
    objectives_text: str = ""       # plain text (každý bod na řádce)
    references_text: str = ""

    # Osoby
    supervisor_name: str = ""
    opponent_name: str = ""

    # Známky (jen pro oponentury, ale parsuje vždy)
    grade_supervisor: str = ""
    grade_opponent: str = ""

    # Datumy + stav
    date_assigned: date | None = None
    date_submitted: date | None = None
    date_defended: date | None = None
    stag_state_code: str = ""       # "DBPOO" atd.

    # Plné raw data (pro debugging / další pole)
    raw: dict[str, str] = field(default_factory=dict)

    # Zdrojové CSV (vyplní se při vícesouborovém stažení ze STAG — připojí se
    # pak právě tohle CSV ke správné práci). Prázdné = použij společný zdroj.
    source_csv: str = ""


@dataclass
class ImportFile:
    """Výsledek načtení CSV — řádky + meta info."""

    path: Path
    encoding: str
    records: list[ParsedRecord]
    skipped: int = 0  # počet řádků, které se nepodařilo parsovat


# ── Veřejné API ──────────────────────────────────────────────────────────────


def load_stag_csv(path: Path, user_name: str = "") -> ImportFile:
    """Načte STAG CSV, zkusí encoding, vrátí strukturované záznamy."""
    raw_rows, encoding = _read_csv_rows(path)
    records: list[ParsedRecord] = []
    skipped = 0
    for row in raw_rows:
        try:
            records.append(_parse_row(row, user_name=user_name))
        except Exception:  # noqa: BLE001
            skipped += 1
            continue
    return ImportFile(path=path, encoding=encoding, records=records, skipped=skipped)


def load_stag_csv_bytes(raw: bytes, user_name: str = "") -> ImportFile:
    """Jako :func:`load_stag_csv`, ale ze syrových bytů (přímé stažení ze STAG).

    Hodí se pro doplnění výsledků vyhledávání (akademický rok / obor), aniž by
    se CSV muselo ukládat na disk.
    """
    raw_rows, encoding = _read_csv_rows_from_bytes(raw)
    records: list[ParsedRecord] = []
    skipped = 0
    for row in raw_rows:
        try:
            records.append(_parse_row(row, user_name=user_name))
        except Exception:  # noqa: BLE001
            skipped += 1
            continue
    return ImportFile(
        path=Path("<bytes>"), encoding=encoding, records=records, skipped=skipped
    )


# ── Vnitřní implementace ─────────────────────────────────────────────────────


def _read_csv_rows(path: Path) -> tuple[list[dict[str, str]], str]:
    """Načte CSV s automatickým fallbackem mezi encodingy."""
    last_exc: Exception | None = None
    for enc in _ENCODINGS:
        try:
            with path.open("r", encoding=enc, newline="") as f:
                reader = csv.DictReader(f, delimiter=_DELIMITER)
                rows = [dict(r) for r in reader if r]
                if not rows:
                    continue
                return rows, enc
        except (UnicodeDecodeError, csv.Error) as exc:
            last_exc = exc
            continue
    if last_exc is not None:
        raise last_exc
    raise ValueError(f"Nepodařilo se přečíst CSV: {path}")


def _read_csv_rows_from_bytes(raw: bytes) -> tuple[list[dict[str, str]], str]:
    """Varianta :func:`_read_csv_rows` pro syrové byty (zkouší encodingy)."""
    import io

    last_exc: Exception | None = None
    for enc in _ENCODINGS:
        try:
            text = raw.decode(enc)
        except (UnicodeDecodeError, LookupError) as exc:
            last_exc = exc
            continue
        try:
            reader = csv.DictReader(io.StringIO(text), delimiter=_DELIMITER)
            rows = [dict(r) for r in reader if r]
        except csv.Error as exc:
            last_exc = exc
            continue
        if rows:
            return rows, enc
    if last_exc is not None:
        raise last_exc
    raise ValueError("Nepodařilo se přečíst CSV z dat (neznámý encoding).")


def _parse_row(row: dict[str, str], user_name: str = "") -> ParsedRecord:
    r = ParsedRecord(role=ImportRole.UNKNOWN, raw=dict(row))

    g = lambda k: (row.get(k) or "").strip()

    # Student
    r.student_uni_id = g("osCislo.student")
    r.student_first = g("jmeno.student")
    r.student_last = g("prijmeni.student")
    r.student_title_pre = g("titulPred.student")
    r.student_title_post = g("titulZa.student")
    r.student_obor_stag = g("oborKombinaceStudenta")

    # Typ + STAG ID
    type_raw = g("typPrace").lower()
    if "diplom" in type_raw:
        r.type_code = "DP"
    elif "bakalá" in type_raw or "bakala" in type_raw:
        r.type_code = "BP"
    else:
        r.type_code = "DP"  # default

    r.adipidno = g("adipidno")

    # Téma
    r.title_cs = g("temaHlavni") or g("nazevDleStud")
    r.title_en = g("temaHlavniAn")
    r.annotation_cs = g("vyjadreni")
    r.annotation_en = g("vyjadreniAn")
    r.objectives_text = _html_ol_to_text(g("zasady"))
    r.references_text = _html_ol_to_text(g("seznamLiter"))

    # Osoby
    r.supervisor_name = g("vedouciJmeno")
    r.opponent_name = g("oponentJmeno")

    # Známky
    r.grade_supervisor = g("znamkaVedouci")
    r.grade_opponent = g("znamkaOponent")

    # Datumy
    r.date_assigned = _parse_cz_date(g("datumZadani"))
    r.date_submitted = _parse_cz_date(g("datumOdevzdani"))
    r.date_defended = _parse_cz_date(g("datumObhajoby"))

    # Stav
    r.stag_state_code = g("stavPrace")

    # Academic year — z datumZadani (září = nový rok)
    r.academic_year = _academic_year_from(r.date_assigned)

    # Role detection
    r.role = _detect_role(
        user_name=user_name,
        supervisor_name=r.supervisor_name,
        opponent_name=r.opponent_name,
    )

    return r


def _html_ol_to_text(html_text: str) -> str:
    """Z HTML ``<ol><li>x</li>…</ol>`` vytáhne každý ``<li>`` na samostatný řádek.

    Také zvládá ``<ul>``, prostý text, dekoduje HTML entity.
    """
    if not html_text:
        return ""
    # Najdi všechny <li>...</li>
    items = re.findall(
        r"<li[^>]*>(.*?)</li>", html_text, flags=re.IGNORECASE | re.DOTALL
    )
    if not items:
        # není to seznam — vrať jen plain text bez tagů
        plain = re.sub(r"<[^>]+>", "", html_text)
        return _decode_entities(plain).strip()
    out_lines: list[str] = []
    for item in items:
        # odstraň vnořené tagy, dekoduj entity, sjednoť whitespace
        plain = re.sub(r"<[^>]+>", "", item)
        plain = _decode_entities(plain)
        plain = re.sub(r"\s+", " ", plain).strip()
        # odstraň úvodní číslici (kdyby STAG někdy přidal "1. ")
        plain = re.sub(r"^\d+\.\s+", "", plain)
        if plain:
            out_lines.append(plain)
    return "\n".join(out_lines)


def _decode_entities(text: str) -> str:
    """Dekóduje HTML entity (``&nbsp;``, ``&#x202f;`` atd.)."""
    text = html.unescape(text)
    # Speciální narrow no-break space   a   nahradit běžnou mezerou
    text = text.replace(" ", " ").replace(" ", " ")
    return text


def _parse_cz_date(s: str) -> date | None:
    """Parse 'D.M.YYYY' nebo 'DD.MM.YYYY' (české datum)."""
    if not s:
        return None
    s = s.strip()
    for fmt in ("%d.%m.%Y", "%d. %m. %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _academic_year_from(d: date | None) -> str:
    """Spočítá ak. rok z data — září je start nového roku."""
    if d is None:
        return ""
    start = d.year if d.month >= 9 else d.year - 1
    return f"{start}/{start + 1}"


def _detect_role(
    user_name: str, supervisor_name: str, opponent_name: str
) -> ImportRole:
    if not user_name.strip():
        return ImportRole.UNKNOWN
    user_norm = _normalize_name(user_name)
    sup_norm = _normalize_name(supervisor_name)
    opp_norm = _normalize_name(opponent_name)

    if user_norm and user_norm in sup_norm:
        return ImportRole.SUPERVISOR
    if user_norm and user_norm in opp_norm:
        return ImportRole.OPPONENT
    # Volnější — porovnání tokenů (kdyby v STAG bylo "Žáček Petr, Ing. Ph.D."
    # a uživatel zadal jen "Petr Žáček"):
    user_tokens = set(_tokens(user_name))
    sup_tokens = set(_tokens(supervisor_name))
    opp_tokens = set(_tokens(opponent_name))
    # match aspoň jméno + příjmení (2+ tokeny)
    if len(user_tokens & sup_tokens) >= 2:
        return ImportRole.SUPERVISOR
    if len(user_tokens & opp_tokens) >= 2:
        return ImportRole.OPPONENT
    return ImportRole.UNKNOWN


_TITLE_TOKENS = {
    "doc.", "prof.", "ing.", "mgr.", "mudr.", "rndr.", "judr.",
    "phdr.", "paeddr.", "bc.", "dis.", "ph.d.", "csc.", "dsc.",
    "th.d.", "mga.",
}


def _tokens(name: str) -> list[str]:
    """Rozdělí jméno na tokeny, odstraní tituly + interpunkci."""
    if not name:
        return []
    out: list[str] = []
    for raw in re.split(r"[\s,]+", name):
        token = raw.strip().lower()
        if not token:
            continue
        if token in _TITLE_TOKENS:
            continue
        if token.endswith("."):
            # zkrácený titul, který nepokrývá set
            continue
        out.append(token)
    return out


def _normalize_name(name: str) -> str:
    """Vrátí jméno jako lowercase string pro substring match (titulky odstraněny)."""
    return " ".join(_tokens(name))
