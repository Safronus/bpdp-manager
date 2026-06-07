"""Kontrola pravopisu (čeština) přes spylls + přibalený hunspell slovník.

Je **volitelná a bezpečná**: když chybí balík ``spylls`` nebo slovníkové
soubory, funkce se ladně vypne (``is_available()`` vrátí ``False`` a
``check_word`` nic nepodtrhává). Nabízí jen **detekci** a **návrhy** —
žádná autokorekce.

Slovník je v ``resources/dictionaries/cs_CZ.{aff,dic}`` (LibreOffice, viz
``LICENSE_cs_CZ.txt``). Engine ``spylls`` je čistě pythonní (žádný systémový
balík / Homebrew).
"""

from __future__ import annotations

import functools
from pathlib import Path

_DICT_BASENAME = "cs_CZ"


def _dict_base() -> Path:
    # services/spellcheck.py → services → bpdpmanager → resources/dictionaries
    return (
        Path(__file__).resolve().parent.parent
        / "resources" / "dictionaries" / _DICT_BASENAME
    )


@functools.lru_cache(maxsize=1)
def _load():
    """Načte slovník jednou (cache). Vrátí spylls Dictionary nebo None."""
    try:
        from spylls.hunspell import Dictionary
    except Exception:  # noqa: BLE001 — spylls nemusí být nainstalován
        return None
    base = _dict_base()
    if not (base.with_suffix(".dic").is_file() and base.with_suffix(".aff").is_file()):
        return None
    try:
        return Dictionary.from_files(str(base))
    except Exception:  # noqa: BLE001 — vadný/nečitelný slovník není fatal
        return None


def is_available() -> bool:
    """True, když je kontrola pravopisu k dispozici (spylls + slovník)."""
    return _load() is not None


def unavailable_reason() -> str:
    """Lidsky čitelný důvod, proč kontrola pravopisu není dostupná."""
    try:
        import spylls  # noqa: F401
    except Exception:  # noqa: BLE001
        return "není nainstalován balík spylls (pip install spylls)."
    base = _dict_base()
    if not (base.with_suffix(".dic").is_file() and base.with_suffix(".aff").is_file()):
        return "chybí český slovník v resources/dictionaries/."
    return "slovník se nepodařilo načíst."


def check_word(word: str) -> bool:
    """True = slovo je správně (nebo není slovník → nic nehlásíme)."""
    d = _load()
    if d is None or not word:
        return True
    try:
        return bool(d.lookup(word))
    except Exception:  # noqa: BLE001
        return True


def suggest(word: str, limit: int = 7) -> list[str]:
    """Návrhy oprav pro slovo (max ``limit``). Prázdné, když nejsou / chybí slovník."""
    d = _load()
    if d is None or not word:
        return []
    out: list[str] = []
    try:
        for s in d.suggest(word):
            out.append(s)
            if len(out) >= limit:
                break
    except Exception:  # noqa: BLE001
        return []
    return out
