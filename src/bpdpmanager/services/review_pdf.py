"""Vyčtení navržené známky z PDF posudku.

Používá se u oponentur: když uživatel nahraje **PDF posudku vedoucího**
(externí vedoucí ho dodá hotové), zkusíme z něj přečíst navrženou známku
a doplnit ji do `grade_supervisor`. Funguje pro CZ i EN šablony FAI UTB.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

# pypdf u některých (mírně vadných) PDF spamuje varování „Ignoring wrong
# pointing object …" — pro nás neškodná, ztlumíme ji.
logging.getLogger("pypdf").setLevel(logging.ERROR)

# Navrženou známku hledáme u několika formulací (FAI UTB šablony, novější
# i historické). Záměrně NE u boilerplate „...v případě hodnocení stupněm
# F – nedostatečně...", které je v každém posudku — proto se vážeme na
# konkrétní návrhovou frázi (navrhuji / doporučuji hodnotit / navržená známka).
# FX musí být v alternaci první, jinak by „F" pohltilo „FX".
_GRADE_RE = re.compile(
    r"(?:"
    r"navržen[áé]\s+známka"                       # „Navržená známka: D"
    r"|navrhuji\s+hodnocení"                       # „navrhuji hodnocení B - velmi dobře"
    r"|navrhuji\s+(?:klasifikovat\s+stupněm|známku|hodnotit\s+stupněm)"
    r"|doporučuji\s+hodnotit\s+stupněm"            # „doporučuji hodnotit stupněm B"
    r"|hodnotit\s+stupněm"                         # „a doporučuji hodnotit stupněm B"
    r"|proposed\s+grade|suggested\s+grade"         # EN šablony
    r")"
    r"\s*[:\-]?\s*(FX|F|[A-E])\b",
    re.IGNORECASE,
)


def parse_grade_from_text(text: str) -> str | None:
    """Najde navrženou známku v textu posudku (CZ i EN). Vrací A–F / FX nebo None."""
    m = _GRADE_RE.search(text or "")
    return m.group(1).upper() if m else None


def extract_grade_from_pdf(path: Path) -> str | None:
    """Vrátí navrženou známku (A–F / FX) z PDF posudku, nebo ``None``."""
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception:  # noqa: BLE001 — PDF nemusí jít přečíst, to není fatal
        return None
    return parse_grade_from_text(text)
