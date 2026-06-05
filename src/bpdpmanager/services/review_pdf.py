"""Vyčtení navržené známky z PDF posudku.

Používá se u oponentur: když uživatel nahraje **PDF posudku vedoucího**
(externí vedoucí ho dodá hotové), zkusíme z něj přečíst navrženou známku
a doplnit ji do `grade_supervisor`. Funguje pro CZ i EN šablony FAI UTB.
"""

from __future__ import annotations

import re
from pathlib import Path

# „Navržená známka: D" / „Proposed grade: B" → A–F nebo FX (FX musí být první).
_GRADE_RE = re.compile(
    r"(?:navržená\s+známka|proposed\s+grade|suggested\s+grade)\s*[:\-]?\s*(FX|F|[A-E])\b",
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
