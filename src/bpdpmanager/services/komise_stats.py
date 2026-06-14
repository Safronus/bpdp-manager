"""Statistika obhajob komisí — agregace stavů studentů do 4 kategorií.

Čistá logika (bez sítě a UI) nad mapou ``states`` ``{klíč studenta: kategorie}``,
kde klíč je osobní číslo (Axxxxx, uppercase) nebo foldované jméno a kategorie je
jedna z :data:`CATEGORIES`. Síťové zjištění stavů ze STAG řeší
``ui.stag_check.fetch_committee_defense_states``.

Dvě statistiky:
- **podle barvy komise** — kolik studentů komise obhájilo/neobhájilo/…,
- **podle členů** — každému členovi součet studentů jeho komisí.
"""

from __future__ import annotations

import unicodedata

# 4 kategorie výsledku obhajoby.
CAT_DEFENDED = "defended"
CAT_FAILED = "failed"
CAT_UNFINISHED = "unfinished"
CAT_NONE = "none"  # bez obhajoby: čeká / v řešení / nenalezeno / dosud nezjištěno

CATEGORIES = (CAT_DEFENDED, CAT_FAILED, CAT_UNFINISHED, CAT_NONE)

CATEGORY_LABELS = {
    CAT_DEFENDED: "Obhájeno",
    CAT_FAILED: "Neobhájeno",
    CAT_UNFINISHED: "Nedokončeno",
    CAT_NONE: "Bez obhajoby",
}

# Stavy, které jsou „hotové" (znovu se ze STAG nedotazují).
TERMINAL = frozenset({CAT_DEFENDED, CAT_FAILED, CAT_UNFINISHED})

# STAG kód → kategorie.
_CODE_TO_CAT = {
    "DUO": CAT_DEFENDED,
    "DBUO": CAT_FAILED,
    "OPUNO": CAT_FAILED,
    "ND": CAT_UNFINISHED,
    "R": CAT_NONE,
    "DBPOO": CAT_NONE,
}


def category_from_code(code: str) -> str:
    """STAG kód stavu (DUO/DBUO/…) → kategorie (default ``CAT_NONE``)."""
    return _CODE_TO_CAT.get((code or "").strip().upper(), CAT_NONE)


def fold_name(s: str) -> str:
    """Jméno bez diakritiky, lowercase, ořezané — pro párování a klíče."""
    nfd = unicodedata.normalize("NFD", s or "")
    return "".join(c for c in nfd if not unicodedata.combining(c)).lower().strip()


def slot_key(personal_number: str, student_name: str) -> str:
    """Klíč studenta do ``states``: osobní číslo, jinak foldované jméno."""
    pn = (personal_number or "").strip().upper()
    return pn if pn else fold_name(student_name)


def _slot_category(slot, states: dict) -> str:
    pn = (slot.personal_number or "").strip().upper()
    if pn and pn in states:
        return states[pn]
    return states.get(fold_name(slot.student_name), CAT_NONE)


def _empty_counts() -> dict:
    return dict.fromkeys(CATEGORIES, 0)


def committee_defense_stats(committees, states: dict | None) -> dict:
    """Agregace stavů obhajob přes ``committees``.

    Vrací ``{"by_color": [...], "by_member": [...], "totals": {...}}``:
    - ``by_color`` — řádek na komisi (barva + stupeň + obor) s počty kategorií
      a ``total`` (počet slotů),
    - ``by_member`` — řádek na člena (dle jména, napříč komisemi) s počty
      studentů jeho komisí,
    - ``totals`` — souhrnné počty kategorií za celý rozsah.

    Bez napárovaného stavu spadne student do ``CAT_NONE`` (default „bez obhajoby").
    """
    states = states or {}
    by_color: list[dict] = []
    member_counts: dict[str, dict] = {}
    totals = _empty_counts()

    for c in committees:
        counts = _empty_counts()
        for s in c.slots:
            counts[_slot_category(s, states)] += 1
        total = sum(counts.values())
        for cat in CATEGORIES:
            totals[cat] += counts[cat]
        by_color.append({
            "color": c.color,
            "level": c.level,
            "obor": c.obor,
            "academic_year": c.academic_year,
            **counts,
            "total": total,
        })
        for m in c.members:
            key = fold_name(m.name)
            if not key:
                continue
            entry = member_counts.setdefault(
                key, {"name": m.name, **_empty_counts(), "total": 0})
            for cat in CATEGORIES:
                entry[cat] += counts[cat]
            entry["total"] += total

    by_color.sort(key=lambda e: (fold_name(e["color"]), fold_name(e["obor"] or "")))
    by_member = sorted(member_counts.values(), key=lambda e: fold_name(e["name"]))
    return {"by_color": by_color, "by_member": by_member, "totals": totals}
