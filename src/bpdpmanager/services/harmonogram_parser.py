"""Parser PDF harmonogramu výuky FAI UTB.

Vstup: text extrahovaný z PDF (pypdf). Výstup: seznam ``KeyDate`` záznamů.

Parser je naladěný na konzistentní formát rozhodnutí děkana FAI
(RD/MM/RR), ale snaží se být robustní vůči drobným změnám.
"""

from __future__ import annotations

import logging
import re
from datetime import date

from ..models import KeyDate, KeyDateCategory

# Ztlum neškodná pypdf varování „Ignoring wrong pointing object …".
logging.getLogger("pypdf").setLevel(logging.ERROR)

# 31. 8. 2026  |  1. 9. 2026 - 4. 2. 2027  |  10.05.2027
_DATE_RE = re.compile(r"(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})")
_RANGE_RE = re.compile(
    r"^\s*(\d{1,2}\.\s*\d{1,2}\.\s*\d{4})"
    r"(?:\s*[-–—]\s*(\d{1,2}\.\s*\d{1,2}\.\s*\d{4}))?"
    r"\s+(.+?)\s*$",
)
_MONTH_CS = {
    "leden": 1, "ledna": 1,
    "únor": 2, "února": 2, "unor": 2, "unora": 2,
    "březen": 3, "března": 3, "brezen": 3, "brezna": 3,
    "duben": 4, "dubna": 4,
    "květen": 5, "května": 5, "kveten": 5, "kvetna": 5,
    "červen": 6, "června": 6, "cerven": 6, "cervna": 6,
    "červenec": 7, "července": 7, "cervenec": 7, "cervence": 7,
    "srpen": 8, "srpna": 8,
    "září": 9, "zari": 9,
    "říjen": 10, "října": 10, "rijen": 10, "rijna": 10,
    "listopad": 11, "listopadu": 11,
    "prosinec": 12, "prosince": 12,
}

# Fuzzy řádky typu "Září 2026", "květen-červen 2027", "do konce září 2027"
_FUZZY_RE = re.compile(
    r"^\s*(?P<label>(?:do konce\s+|po\s+|v\s+)?"
    r"[A-Za-zÁ-Žá-ž]+(?:\s*[-–]\s*[A-Za-zÁ-Žá-ž]+)?\s+\d{4})"
    r"\s+(?P<desc>.+?)\s*$",
)

_SKIP_PREFIXES = (
    "Vnitřní normy",
    "RD/",
    "Kód:",
    "Druh:",
    "Číslo jednací:",
    "Klasifikace dokumentu:",
    "Název:",
    "Organizační závaznost:",
    "Datum vydání:",
    "Účinnost:",
    "Vydává:",
    "Zpracoval:",
    "Spolupracoval:",
    "Počet stran:",
    "Počet příloh:",
    "Rozdělovník:",
    "Podpis oprávněné",
    "osoby:",
    "Článek",
    "str.",
    "_",
    "(od",  # časy v závorkách
)

# Mezi-sekce, které ukončí joining předchozí položky (ale neukončí parsování).
_SECTION_HEADERS = (
    "Přijímací řízení",
    "Uzavření všech studijních povinností",
    "Výuka odpadá",
    "Bližší termíny",
)

# Sekce, za kterými nic dalšího neparsujeme.
_HARD_STOP_SECTIONS = (
    "Závěrečné ustanovení",
    "Verze dokumentu",
)

_KEYWORD_CATEGORIES: list[tuple[str, KeyDateCategory, bool]] = [
    # (keyword in lowercase, category, important)
    ("odevzdání bakalářské", KeyDateCategory.THESIS, True),
    ("odevzdání diplomové", KeyDateCategory.THESIS, True),
    ("odevzdání bakalářské / diplomové", KeyDateCategory.THESIS, True),
    ("odevzdani", KeyDateCategory.THESIS, True),
    ("szz", KeyDateCategory.THESIS, True),
    ("státní závěrečn", KeyDateCategory.THESIS, True),
    ("promoce", KeyDateCategory.THESIS, True),
    ("zahájení akademického", KeyDateCategory.SEMESTER, True),
    ("kontrola studia", KeyDateCategory.SEMESTER, False),
    ("výuka", KeyDateCategory.SEMESTER, False),
    ("zimní semestr", KeyDateCategory.SEMESTER, False),
    ("letní semestr", KeyDateCategory.SEMESTER, False),
    ("mezní termín", KeyDateCategory.EXAM, True),
    ("zkouškové", KeyDateCategory.EXAM, False),
    ("opravné zkouškové", KeyDateCategory.EXAM, False),
    ("předzápis", KeyDateCategory.ENROLLMENT, False),
    ("imatrikulace", KeyDateCategory.ENROLLMENT, False),
    ("prázdniny", KeyDateCategory.HOLIDAY, False),
    ("svátek", KeyDateCategory.HOLIDAY, False),
    ("velký pátek", KeyDateCategory.HOLIDAY, False),
    ("velikonoční", KeyDateCategory.HOLIDAY, False),
    ("rektorský den", KeyDateCategory.HOLIDAY, False),
    ("přijímací řízení", KeyDateCategory.ADMISSIONS, False),
    ("hodnocení kvality", KeyDateCategory.OTHER, False),
]


def _parse_date(token: str) -> date | None:
    m = _DATE_RE.match(token.strip())
    if not m:
        return None
    d, mo, y = (int(x) for x in m.groups())
    try:
        return date(y, mo, d)
    except ValueError:
        return None


def _categorize(description: str) -> tuple[KeyDateCategory, bool]:
    desc_lower = description.lower()
    for keyword, cat, important in _KEYWORD_CATEGORIES:
        if keyword in desc_lower:
            return cat, important
    return KeyDateCategory.OTHER, False


def _normalize_lines(text: str) -> list[str]:
    """Sloučí pokračování víceřádkových popisů do jednoho řádku.

    Řádek bez data na začátku se připojí k předchozímu (pokud existuje).
    Sekční nadpisy ukončí joining, hard-stop sekce ukončí celé parsování.
    """
    raw_lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    lines: list[str] = []
    for line in raw_lines:
        if any(line.startswith(p) for p in _HARD_STOP_SECTIONS):
            break
        if any(line.startswith(p) for p in _SKIP_PREFIXES):
            continue
        if any(line.startswith(p) for p in _SECTION_HEADERS):
            # přeruš joining — neuložíme jako data, jen tím končí předchozí položka
            lines.append("__SECTION_BREAK__")
            continue
        starts_with_date = _RANGE_RE.match(line) is not None
        starts_with_fuzzy = _FUZZY_RE.match(line) is not None
        if (starts_with_date or starts_with_fuzzy) or not lines:
            lines.append(line)
        elif lines[-1] == "__SECTION_BREAK__":
            # po sekčním předělu nic nejoinuj k němu, prostě skip
            continue
        else:
            lines[-1] = lines[-1].rstrip() + " " + line
    return [ln for ln in lines if ln != "__SECTION_BREAK__"]


def parse_harmonogram_text(text: str) -> list[KeyDate]:
    """Z extrahovaného textu PDF vytáhne strukturované klíčové termíny."""
    results: list[KeyDate] = []
    for line in _normalize_lines(text):
        m = _RANGE_RE.match(line)
        if m:
            d_start = _parse_date(m.group(1))
            d_end = _parse_date(m.group(2)) if m.group(2) else None
            desc = m.group(3).strip().rstrip(".").strip()
            if not desc or d_start is None:
                continue
            cat, important = _categorize(desc)
            results.append(
                KeyDate(
                    date_start=d_start,
                    date_end=d_end,
                    description=desc,
                    category=cat,
                    important=important,
                    source="imported",
                )
            )
            continue

        fm = _FUZZY_RE.match(line)
        if fm:
            label = fm.group("label").strip()
            desc = fm.group("desc").strip().rstrip(".").strip()
            if not desc:
                continue
            # u "(státní svátek)" a podobných nesmysl, přeskoč
            if desc.startswith("(") and desc.endswith(")"):
                continue
            cat, important = _categorize(desc)
            results.append(
                KeyDate(
                    date_start=None,
                    date_end=None,
                    fuzzy_label=label,
                    description=desc,
                    category=cat,
                    important=important,
                    source="imported",
                )
            )

    return _dedupe(results)


def _dedupe(items: list[KeyDate]) -> list[KeyDate]:
    seen: set[tuple] = set()
    out: list[KeyDate] = []
    for kd in items:
        key = (kd.date_start, kd.date_end, kd.fuzzy_label, kd.description)
        if key in seen:
            continue
        seen.add(key)
        out.append(kd)
    return out


def parse_pdf(path) -> list[KeyDate]:
    """Vrátí strukturované termíny z PDF souboru.

    Vyžaduje balíček ``pypdf``.
    """
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    text = "\n".join(p.extract_text() or "" for p in reader.pages)
    return parse_harmonogram_text(text)
