"""Lehká vrstva překladu UI: čeština (zdroj) → angličtina (slovník).

Čeština je **zdrojový jazyk** — všechny texty v kódu zůstávají česky a default
chování se nemění. Angličtina je překladová vrstva: ``tr("Vedené práce")``
vrátí v CZ režimu text beze změny, v EN režimu anglický překlad ze slovníku
(:mod:`bpdpmanager.i18n.en`). Nepřeložený text **tiše zůstane česky** (žádné
pády, překlad lze doplňovat po vlnách).

Parametrizované texty používají ``str.format``::

    tr("Celkem {n} souborů").format(n=12)

Jazyk se nastavuje při startu (``set_language``) z předvolby profilu a změna
se projeví po restartu aplikace.
"""

from __future__ import annotations

LANG_CS = "cs"
LANG_EN = "en"

_language = LANG_CS


def set_language(lang: str) -> None:
    """Nastaví jazyk UI (``"cs"`` / ``"en"``); neznámý → čeština."""
    global _language
    _language = LANG_EN if (lang or "").lower() == LANG_EN else LANG_CS


def get_language() -> str:
    return _language


def tr(text: str) -> str:
    """Přeloží český zdrojový text dle aktivního jazyka (EN přes slovník)."""
    if _language == LANG_CS:
        return text
    from .en import EN

    return EN.get(text, text)
