"""Agregace průběhu SZZ pro statistiky (admin) — čistá logika nad cache.

Vstup: ``{os_cislo: SzzRecord}`` (z ``ThesisService.load_szz_results()``) +
komise v rozsahu (filtr dle výběru ve stromu). Výstup: agregace pro záložku
„Průběh SZZ" (per komise / per zkoušející / per předmět / rozložení známek +
otázky). Vše klíčované **osobním číslem**; jméno je jen zobrazovací.

Číselný průměr: A=1, B=2, C=3, D=4, E=5, F/FX=6 (nižší = lepší).
"""

from __future__ import annotations

GRADES = ("A", "B", "C", "D", "E", "F")   # FX se slučuje do F
_GRADE_NUM = {"A": 1, "B": 2, "C": 3, "D": 4, "E": 5, "F": 6}


def _letter(g: str) -> str:
    """Známku normalizuj na písmeno A-F (FX → F); jinak ``""``."""
    g = (g or "").strip().upper()
    if g.startswith("FX"):
        return "F"
    g = g[:1]
    return g if g in _GRADE_NUM else ""


def _empty_dist() -> dict:
    return dict.fromkeys(GRADES, 0)


def _avg(dist: dict):
    n = sum(dist.values())
    if not n:
        return None
    s = sum(_GRADE_NUM[g] * c for g, c in dist.items())
    return round(s / n, 1)


def _scope_oscisla(committees) -> set:
    out: set = set()
    for c in committees:
        for s in c.slots:
            pn = (s.personal_number or "").strip().upper()
            if pn:
                out.add(pn)
    return out


def szz_admin_stats(records: dict, committees) -> dict:
    """Agregace záznamů v rozsahu daném ``committees`` (prázdné → všechny).

    Vrací ``{totals, by_komise, by_examiner, by_predmet, dist, questions}``.
    """
    in_scope = _scope_oscisla(committees)
    recs = [r for oc, r in (records or {}).items()
            if (not in_scope) or (oc or "").strip().upper() in in_scope]

    komise: dict = {}
    examiner: dict = {}
    predmet: dict = {}
    questions: dict = {}
    dist_overall, dist_defense, dist_subj = _empty_dist(), _empty_dist(), _empty_dist()
    students = prospel = neprospel = 0

    for r in recs:
        students += 1
        ov = getattr(r, "overall", None)
        if ov:
            if ov.prospel is True:
                prospel += 1
            elif ov.prospel is False:
                neprospel += 1
            kgrp = komise.setdefault(ov.komise or "?", {
                "komise": ov.komise or "?", "n": 0, "pass": 0, "fail": 0,
                "dist": _empty_dist()})
            kgrp["n"] += 1
            if ov.prospel is True:
                kgrp["pass"] += 1
            elif ov.prospel is False:
                kgrp["fail"] += 1
            kl = _letter(ov.vysledek_zkousek)
            if kl:
                kgrp["dist"][kl] += 1
                dist_overall[kl] += 1

        for s in getattr(r, "subjects", []) or []:
            sl = _letter(s.znamka)
            ekey = (s.ucitidno or s.zkousejici or "").strip()
            if ekey:
                e = examiner.setdefault(ekey, {
                    "jmeno": s.zkousejici, "ucitidno": s.ucitidno, "n": 0,
                    "dist": _empty_dist()})
                e["n"] += 1
                if sl:
                    e["dist"][sl] += 1
            if s.predmet:
                p = predmet.setdefault(s.predmet, {
                    "predmet": s.predmet, "katedra": s.katedra, "n": 0,
                    "dist": _empty_dist()})
                p["n"] += 1
                if sl:
                    p["dist"][sl] += 1
                if s.prubeh:
                    questions.setdefault(s.predmet, []).append(s.prubeh)
            if sl:
                dist_subj[sl] += 1

        dfn = getattr(r, "defense", None)
        if dfn:
            dl = _letter(dfn.znamka)
            if dl:
                dist_defense[dl] += 1

    def _rows(d: dict, sort_key) -> list:
        rows = list(d.values())
        for row in rows:
            row["avg"] = _avg(row["dist"])
        rows.sort(key=sort_key)
        return rows

    return {
        "totals": {"students": students, "prospel": prospel,
                   "neprospel": neprospel, "avg": _avg(dist_overall)},
        "by_komise": _rows(komise, lambda r: r["komise"]),
        "by_examiner": _rows(examiner, lambda r: (-r["n"], r["jmeno"] or "")),
        "by_predmet": _rows(predmet, lambda r: r["predmet"]),
        "dist": {"overall": dist_overall, "defense": dist_defense,
                 "subjects": dist_subj},
        "questions": questions,
    }
