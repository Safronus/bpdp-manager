"""Skládání jména s tituly před/za.

Tituly se ukládají jako volné stringy (např. ``"doc. Ing."`` a ``"Ph.D."``
nebo ``", Ph.D."``). ``compose_titled_name`` je poskládá do jednoho jména
``„doc. Ing. Petr Novák, Ph.D."`` — vkládá mezery, ale respektuje čárku na
začátku titulu za jménem (aby nevznikla mezera před čárkou).
"""

from __future__ import annotations

import re

# České akademické tituly. Klasifikace, KAM titul patří (před/za jménem).
# Porovnává se v normalizované podobě (malá písmena, bez teček/mezer).
_TITLES_BEFORE = {
    "prof", "doc",
    "bc", "bca",
    "mgr", "mga",
    "ing",                          # Ing. (arch. se připojí jako neznámý token)
    "mudr", "mddr", "mvdr",
    "judr", "phdr", "rndr", "pharmdr", "paeddr", "rsdr", "thlic", "thdr", "phmr",
    "dr", "ddr",
}
_TITLES_AFTER = {
    "phd", "thd",                   # Ph.D., PhD., Th.D.
    "csc", "drsc", "dsc",
    "dis",                          # DiS.
    "mba", "dba", "llm", "msc", "ma", "ba", "bba",
    "drhc",                         # dr. h. c.
}


def _norm_title(token: str) -> str:
    return re.sub(r"[.\s]", "", token or "").lower()


def compose_titled_name(
    title_before: str | None, name: str | None, title_after: str | None
) -> str:
    """Poskládá ``"titul_před Jméno, titul_za"`` (prázdné části vynechá).

    Tituly za jménem se vždy oddělují čárkou (``", Ph.D."``) — případnou čárku
    uloženou v ``title_after`` normalizuje, ať nevznikne dvojitá.
    """
    before = (title_before or "").strip()
    base = (name or "").strip()
    after = (title_after or "").strip().lstrip(",; ").strip()

    out = f"{before} {base}".strip() if before else base
    if after:
        out = f"{out}, {after}".strip() if out else after
    return out


def parse_titled_name(full: str) -> tuple[str, str, str]:
    """Rozparsuje celé jméno s tituly na ``(title_before, name, title_after)``.

    Cílí na formát ze STAG ``"Příjmení Jméno, T1 T2 …"`` (příjmení první, za
    čárkou všechny tituly smíchané), např. ``"Novák Jan, prof. Ing. Ph.D."``
    → ``("prof. Ing.", "Jan Novák", "Ph.D.")``. Tituly třídí podle známých
    seznamů (nehádá). Bez čárky bere řetězec jako čisté jméno (neparsuje).
    """
    full = (full or "").strip()
    if not full or "," not in full:
        return "", full, ""

    name_part, _, titles_part = full.partition(",")
    name_part = name_part.strip()
    # STAG dává „Příjmení Jméno" — u dvou tokenů přehodíme na „Jméno Příjmení".
    toks = name_part.split()
    name = f"{toks[1]} {toks[0]}" if len(toks) == 2 else name_part

    before: list[str] = []
    after: list[str] = []
    last: list[str] | None = None
    for tok in titles_part.replace(",", " ").split():
        norm = _norm_title(tok)
        if norm in _TITLES_BEFORE:
            before.append(tok)
            last = before
        elif norm in _TITLES_AFTER:
            after.append(tok)
            last = after
        else:
            # Neznámý token (např. „arch." u „Ing. arch.") → ke stejné skupině
            # jako předchozí titul (jinak před jméno).
            (last if last is not None else before).append(tok)
    return " ".join(before), name, ", ".join(after)


def split_first_surname(full: str) -> tuple[str, str]:
    """Heuristicky rozdělí celé jméno na ``(křestní, příjmení)``.

    Příjmení = poslední token, křestní = zbytek (``"Jan Petr Novák"`` →
    ``("Jan Petr", "Novák")``). Jen pro **předvyplnění** dvou polí profilu
    a fallback — u dvojího příjmení (``"Zuzana Komínková Oplatková"``) to
    rozdělí špatně (příjmení „Oplatková"), proto si to uživatel v profilu
    upraví; po uložení se už bere jeho explicitní volba.
    """
    toks = [t for t in (full or "").replace(",", " ").split() if t]
    if not toks:
        return "", ""
    if len(toks) == 1:
        return "", toks[0]   # jediný token bereme jako příjmení (pro hledání)
    return " ".join(toks[:-1]), toks[-1]
