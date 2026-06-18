"""Agregace průběhu SZZ pro statistiky (admin) — čistá logika nad cache.

Vstup: ``{os_cislo: SzzRecord}`` (z ``ThesisService.load_szz_results()``) +
komise v rozsahu (filtr dle výběru ve stromu). Výstup: agregace pro záložku
„Průběh SZZ" (per komise / per zkoušející / per předmět / rozložení známek /
neúspěšní). Vše klíčované **osobním číslem**; jméno je jen zobrazovací.

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


_PASS = ("A", "B", "C", "D", "E")


def _pass_fail_none(dist: dict, n: int) -> tuple:
    """(prospěl, neprospěl, bez známky) z rozložení A-F a počtu ``n``.

    Prospěl = A-E, neprospěl = F/FX, zbytek (n - ohodnocení) = bez známky.
    """
    passed = sum(dist.get(g, 0) for g in _PASS)
    failed = dist.get("F", 0)
    return passed, failed, max(0, n - passed - failed)


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

    Vrací ``{totals, by_komise, by_examiner, by_predmet, dist, fails}``.
    """
    in_scope = _scope_oscisla(committees)
    recs = [r for oc, r in (records or {}).items()
            if (not in_scope) or (oc or "").strip().upper() in in_scope]
    os_to_color = {}
    os_to_name = {}
    for c in committees:
        for s in c.slots:
            pn = (s.personal_number or "").strip().upper()
            if pn:
                os_to_color.setdefault(pn, c.color or "?")
                nm = (s.student_name or "").strip()
                if nm:
                    os_to_name.setdefault(pn, nm)

    komise: dict = {}
    examiner: dict = {}
    predmet: dict = {}
    dist_overall, dist_predmety, dist_defense, dist_subj = (
        _empty_dist(), _empty_dist(), _empty_dist(), _empty_dist())
    students = nedostupne = 0
    # Neúspěchy (F/FX) po dimenzích — kdo a v čem neuspěl. Vše dle os. čísla,
    # jméno jen pro zobrazení (z rozpisu komise nebo z parsed záznamu).
    fails: dict = {"subjects": [], "predmety": [], "defense": [], "overall": []}

    def _name(r) -> str:
        oc = (r.os_cislo or "").strip().upper()
        nm = os_to_name.get(oc)
        if nm:
            return nm
        full = " ".join(p for p in (getattr(r, "prijmeni", ""),
                                    getattr(r, "jmeno", "")) if p).strip()
        return full

    def _komise(color):
        return komise.setdefault(color, {"komise": color, "n": 0,
                                         "nedostupne": 0, "dist": _empty_dist()})

    for r in recs:
        students += 1
        if getattr(r, "unavailable", False):
            # Zatím nedostupné (komise neproběhla / nemáme přístup) — nepočítá se
            # do známek, jen se eviduje (i u komise, dle rozpisu).
            nedostupne += 1
            color = os_to_color.get((r.os_cislo or "").strip().upper())
            if color:
                _komise(color)["nedostupne"] += 1
            continue
        oc = (r.os_cislo or "").strip().upper()
        nm = _name(r)
        ov = getattr(r, "overall", None)
        if ov:
            kgrp = _komise(ov.komise or "?")
            kgrp["n"] += 1
            kl = _letter(ov.vysledek_zkousek)
            if kl:
                kgrp["dist"][kl] += 1
                dist_overall[kl] += 1
            klp = _letter(getattr(ov, "vysledek_predmety", ""))
            if klp:
                dist_predmety[klp] += 1
                if klp == "F":
                    fails["predmety"].append({"os": oc, "jmeno": nm})
            # „Neprospěl" = celková známka F NEBO výsledek studia začíná „neprospěl".
            # Počítá se LIVE z textu (ne ze stale uloženého ``prospel`` — ten u
            # nehodnocených s placeholderem „--- Nevyplněno ---" býval chybně False).
            # Nevyplněné/bez známky tu tedy NEjsou — jen skuteční neúspěšní.
            studia_l = (getattr(ov, "vysledek_studia", "") or "").strip().lower()
            if kl == "F" or studia_l.startswith("neprospěl"):
                fails["overall"].append({"os": oc, "jmeno": nm})

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
            if sl:
                dist_subj[sl] += 1
                if sl == "F":
                    fails["subjects"].append({
                        "os": oc, "jmeno": nm, "predmet": s.predmet or "?",
                        "zkousejici": (s.zkousejici or "").strip()})

        dfn = getattr(r, "defense", None)
        if dfn:
            dl = _letter(dfn.znamka)
            if dl:
                dist_defense[dl] += 1
                if dl == "F":   # neobhájil (předseda komise se neuvádí)
                    fails["defense"].append({"os": oc, "jmeno": nm})

    def _rows(d: dict, sort_key) -> list:
        rows = list(d.values())
        for row in rows:
            row["avg"] = _avg(row["dist"])
            row["pass"], row["fail"], row["none"] = _pass_fail_none(
                row["dist"], row["n"])
        rows.sort(key=sort_key)
        return rows

    for lst in fails.values():
        # Bez jména řadíme na konec (1), jinak abecedně dle jména, pak os. číslo.
        lst.sort(key=lambda f: (0, f["jmeno"]) if f.get("jmeno")
                 else (1, f.get("os") or ""))

    # Známky se počítají jen z dostupných (nedostupné jsou samostatná kategorie).
    t_pass, t_fail, t_none = _pass_fail_none(dist_overall, students - nedostupne)
    return {
        "totals": {"students": students, "prospel": t_pass,
                   "neprospel": t_fail, "bez_znamky": t_none,
                   "nedostupne": nedostupne, "avg": _avg(dist_overall)},
        "by_komise": _rows(komise, lambda r: r["komise"]),
        "by_examiner": _rows(examiner, lambda r: (-r["n"], r["jmeno"] or "")),
        "by_predmet": _rows(predmet, lambda r: r["predmet"]),
        "dist": {"overall": dist_overall, "predmety": dist_predmety,
                 "defense": dist_defense, "subjects": dist_subj},
        "fails": fails,
    }
