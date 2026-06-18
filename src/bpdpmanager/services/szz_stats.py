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


def _median(dist: dict):
    """Medián známek (číselně 1-6) z rozložení A-F; ``None`` když prázdné.

    Odolnější vůči počtu/odlehlým hodnotám než průměr. Pro sudé ``n`` průměr
    dvou prostředních (může vyjít x,5). GRADES je seřazené A→F, takže stačí
    projít kumulativní počty.
    """
    n = sum(dist.values())
    if not n:
        return None
    lo_pos, hi_pos = (n + 1) // 2, (n + 2) // 2   # 1-based pozice mediánu
    lo_val = hi_val = None
    cum = 0
    for g in GRADES:
        cum += dist.get(g, 0)
        if lo_val is None and cum >= lo_pos:
            lo_val = _GRADE_NUM[g]
        if cum >= hi_pos:
            hi_val = _GRADE_NUM[g]
            break
    return round((lo_val + hi_val) / 2, 1)


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


def _name_set(name: str) -> frozenset:
    """Množina tokenů jména bez titulů/diakritiky (na párování nezávisí pořadí).

    ``doc. Ing. Jan Mareš, Ph.D.`` → ``{jan, mares}``. Pro spárování zkoušejícího
    (jméno z portálu) s členem komise (jméno s tituly v seedu).
    """
    from .komise_stats import student_name_key

    return frozenset(student_name_key(name).split())


def _norm_date(s: str) -> str:
    """Datum na kanonický tvar ``D.M.RRRR`` — sjednotí „15. 6. 2026" (rozpis PDF)
    a „15.6.2026" (portál), ať se dají dny porovnávat/sjednocovat."""
    import re

    m = re.match(r"\s*(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{2,4})", s or "")
    return f"{int(m.group(1))}.{int(m.group(2))}.{m.group(3)}" if m else (s or "").strip()


def szz_admin_stats(records: dict, committees, all_committees=None) -> dict:
    """Agregace záznamů v rozsahu daném ``committees`` (prázdné → všechny).

    ``all_committees`` (nepovinné) slouží k určení **„svojí" komise zkoušejícího**
    napříč celým rokem (členství je nezávislé na výběru); když chybí, použije se
    ``committees``. Vrací ``{totals, by_komise, by_examiner, by_predmet, dist,
    fails}``.
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

    # Členství zkoušejících → barvy „jejich" komisí + DNY těch komisí (na „za den":
    # člen je v komisi všechny její dny, i když zrovna nezkouší). Jméno bez titulů.
    member_colors: dict = {}
    member_dates: dict = {}
    for c in (all_committees if all_committees is not None else committees):
        col = (c.color or "").strip().lower()
        cdates = {_norm_date(d) for d in (getattr(c, "dates", []) or []) if d}
        for m in getattr(c, "members", []) or []:
            k = _name_set(m.name)
            if not k:
                continue
            if col:
                member_colors.setdefault(k, set()).add(col)
            if cdates:
                member_dates.setdefault(k, set()).update(cdates)

    komise: dict = {}
    examiner: dict = {}
    predmet: dict = {}
    # Rozdělení „Celkového výsledku studia" (ckVysledekStudia) na graf pod titulkem.
    studia = {"vyznamenani": 0, "prospel": 0, "neprospel": 0, "nevyplneno": 0}
    dist_overall, dist_predmety, dist_defense, dist_subj = (
        _empty_dist(), _empty_dist(), _empty_dist(), _empty_dist())
    students = nedostupne = 0
    # Neúspěchy (F/FX) po dimenzích — kdo a v čem neuspěl. Vše dle os. čísla,
    # jméno jen pro zobrazení (z rozpisu komise nebo z parsed záznamu).
    fails: dict = {"subjects": [], "predmety": [], "defense": [], "overall": []}
    # Záznamy s overall, ale BEZ komise (skupina „?") — kdo to je (na doptání).
    no_komise: list = []

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
        # Barva komise studenta = komise, kde proběhly jeho dílčí zkoušky.
        komise_color = (ov.komise or "").strip().lower() if ov else ""
        # Celkový výsledek studia → kategorie pro graf (vyznamenání před prospěl!).
        sv = (getattr(ov, "vysledek_studia", "") or "").strip().lower() if ov else ""
        if "vyznamenán" in sv:
            studia["vyznamenani"] += 1
        elif sv.startswith("neprospěl"):
            studia["neprospel"] += 1
        elif sv.startswith("prospěl"):
            studia["prospel"] += 1
        else:
            studia["nevyplneno"] += 1
        if ov:
            if not komise_color:   # „?" skupina — eviduj kdo to je
                no_komise.append({"os": oc, "jmeno": nm})
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
                    "dist": _empty_dist(), "days": set(),
                    "colors": {}, "own": 0, "foreign": 0, "own_colors": set()})
                e["n"] += 1
                if sl:
                    e["dist"][sl] += 1
                d = _norm_date(s.datum)   # dny, kdy zkoušel (kanonicky)
                if d:
                    e["days"].add(d)
                if komise_color:   # rozpad dle barvy komise + doma/cizí
                    e["colors"][komise_color] = e["colors"].get(komise_color, 0) + 1
                    own = member_colors.get(_name_set(s.zkousejici), set())
                    e["own_colors"] = own   # barvy „jeho" komisí (na domeček ⌂)
                    if komise_color in own:
                        e["own"] += 1
                    else:
                        e["foreign"] += 1
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

    # „Za den": ke dnům, kdy zkoušející zkoušel, přidej VŠECHNY dny komisí, kde je
    # členem (byl tam celé období, i když daný den nezkoušel). Bez členství zůstanou
    # jen dny, kdy zkoušel (nemáme jak zjistit jeho přítomnost).
    for e in examiner.values():
        md = member_dates.get(_name_set(e["jmeno"]))
        if md:
            e["days"] |= md

    def _rows(d: dict, sort_key) -> list:
        rows = list(d.values())
        for row in rows:
            row["avg"] = _avg(row["dist"])
            row["median"] = _median(row["dist"])
            row["pass"], row["fail"], row["none"] = _pass_fail_none(
                row["dist"], row["n"])
            days = row.pop("days", None)   # jen u zkoušejících
            if days is not None:
                row["dni"] = len(days)
                row["per_day"] = round(row["n"] / len(days), 1) if days else None
        rows.sort(key=sort_key)
        return rows

    for lst in fails.values():
        # Bez jména řadíme na konec (1), jinak abecedně dle jména, pak os. číslo.
        lst.sort(key=lambda f: (0, f["jmeno"]) if f.get("jmeno")
                 else (1, f.get("os") or ""))

    no_komise.sort(key=lambda f: (0, f["jmeno"]) if f.get("jmeno")
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
        "no_komise": no_komise,
        "studia": studia,
    }
