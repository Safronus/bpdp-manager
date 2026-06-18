"""Testy agregace průběhu SZZ (services.szz_stats) na syntetických datech."""

from __future__ import annotations

from bpdpmanager.models.komise import Committee, DefenseSlot
from bpdpmanager.models.szz_result import (
    SubjectExam,
    SzzOverall,
    SzzRecord,
    ThesisDefense,
)
from bpdpmanager.services.szz_stats import _avg, _letter, szz_admin_stats


def _rec(oc, komise, vysl, prospel, subjects):
    return SzzRecord(
        os_cislo=oc,
        overall=SzzOverall(komise=komise, vysledek_zkousek=vysl, prospel=prospel),
        subjects=[SubjectExam(predmet=p, znamka=g, zkousejici=ex, ucitidno=uid,
                              prubeh=q)
                  for (p, g, ex, uid, q) in subjects],
    )


def _committee(color, oscisla):
    return Committee(color=color,
                     slots=[DefenseSlot(personal_number=oc) for oc in oscisla])


def test_szz_admin_stats_basic() -> None:
    records = {
        "A1": _rec("A1", "fialová", "A", True,
                   [("AZINF", "A", "Novák", "100", "Q1"),
                    ("AZKYB", "B", "Svoboda", "200", "")]),
        "A2": _rec("A2", "fialová", "C", True,
                   [("AZINF", "C", "Novák", "100", "Q2")]),
        "A3": _rec("A3", "zelená", "F", False,
                   [("AZINF", "FX", "Novák", "100", "")]),
    }
    c = _committee("x", ["A1", "A2", "A3"])
    st = szz_admin_stats(records, [c])

    assert st["totals"]["students"] == 3
    assert st["totals"]["prospel"] == 2 and st["totals"]["neprospel"] == 1

    km = {r["komise"]: r for r in st["by_komise"]}
    assert km["fialová"]["n"] == 2 and km["fialová"]["pass"] == 2
    assert km["fialová"]["dist"]["A"] == 1 and km["fialová"]["dist"]["C"] == 1
    assert km["zelená"]["fail"] == 1 and km["zelená"]["dist"]["F"] == 1

    ex = {r["ucitidno"]: r for r in st["by_examiner"]}
    # Novák: A, C, FX→F  → 3 zkoušení; průměr (1+3+6)/3 = 3.3
    assert ex["100"]["n"] == 3 and ex["100"]["dist"]["F"] == 1
    assert ex["100"]["avg"] == 3.3
    assert ex["200"]["n"] == 1
    # řazení zkoušejících: nejvíc zkoušení první
    assert st["by_examiner"][0]["ucitidno"] == "100"

    pm = {r["predmet"]: r for r in st["by_predmet"]}
    assert pm["AZINF"]["n"] == 3 and pm["AZKYB"]["n"] == 1
    # Otázky/průběh se agregovaně nepočítají (jen v souhrnu studenta).
    assert "questions" not in st


def test_bez_znamky() -> None:
    records = {
        "A1": _rec("A1", "fialová", "A", True, []),     # prospěl (A)
        "A2": _rec("A2", "fialová", "F", False, []),    # neprospěl (F)
        "A3": _rec("A3", "fialová", "", None, []),      # overall, ale bez známky
        "A4": SzzRecord(os_cislo="A4"),                  # vůbec bez overall
    }
    st = szz_admin_stats(records, [])
    t = st["totals"]
    assert t["students"] == 4
    assert t["prospel"] == 1 and t["neprospel"] == 1 and t["bez_znamky"] == 2

    km = {r["komise"]: r for r in st["by_komise"]}
    assert km["fialová"]["n"] == 3          # A1/A2/A3 mají overall
    assert km["fialová"]["pass"] == 1
    assert km["fialová"]["fail"] == 1
    assert km["fialová"]["none"] == 1       # A3 bez známky


def test_nedostupne() -> None:
    records = {
        "A1": _rec("A1", "fialová", "A", True, []),         # prospěl
        "A2": SzzRecord(os_cislo="A2", unavailable=True),    # zatím nedostupné
    }
    st = szz_admin_stats(records, [_committee("fialová", ["A1", "A2"])])
    t = st["totals"]
    assert t["students"] == 2
    assert t["prospel"] == 1 and t["nedostupne"] == 1
    assert t["bez_znamky"] == 0       # nedostupné NENÍ „bez známky"
    km = {r["komise"]: r for r in st["by_komise"]}
    assert km["fialová"]["n"] == 1 and km["fialová"]["nedostupne"] == 1


def test_scope_filters_records() -> None:
    records = {"A1": _rec("A1", "fialová", "A", True, []),
               "A9": _rec("A9", "zelená", "B", True, [])}
    st = szz_admin_stats(records, [_committee("x", ["A1"])])
    assert st["totals"]["students"] == 1   # A9 je mimo rozsah


def test_empty_committees_includes_all() -> None:
    records = {"A1": _rec("A1", "fialová", "A", True, [])}
    assert szz_admin_stats(records, [])["totals"]["students"] == 1


def test_letter_and_avg() -> None:
    assert _letter("FX") == "F" and _letter("A") == "A" and _letter("") == ""
    assert _avg({"A": 1, "F": 1, "B": 0, "C": 0, "D": 0, "E": 0}) == 3.5
    assert _avg(dict.fromkeys("ABCDEF", 0)) is None


def test_median() -> None:
    from bpdpmanager.services.szz_stats import _median

    assert _median(dict.fromkeys("ABCDEF", 0)) is None
    # liché n: A,B,D → prostřední B = 2
    assert _median({"A": 1, "B": 1, "C": 0, "D": 1, "E": 0, "F": 0}) == 2.0
    # sudé n: A,B,C,D → (2+3)/2 = 2.5
    assert _median({"A": 1, "B": 1, "C": 1, "D": 1, "E": 0, "F": 0}) == 2.5
    # odolnost vůči odlehlé F: 5x A + 1x F → medián A=1 (průměr by byl 1,8)
    assert _median({"A": 5, "B": 0, "C": 0, "D": 0, "E": 0, "F": 1}) == 1.0


def test_by_examiner_has_median() -> None:
    records = {
        "A1": _rec("A1", "x", "A", True,
                   [("AZINF", "A", "Novák", "100", ""),
                    ("AZKYB", "A", "Novák", "100", ""),
                    ("AZMAT", "F", "Novák", "100", "")]),
    }
    ex = {r["ucitidno"]: r for r in szz_admin_stats(records, [])["by_examiner"]}
    # Novák: A,A,F → medián A=1,0 (odolný), průměr (1+1+6)/3 = 2,7
    assert ex["100"]["median"] == 1.0 and ex["100"]["avg"] == 2.7


def test_defense_distribution() -> None:
    records = {
        "A1": SzzRecord(os_cislo="A1", defense=ThesisDefense(znamka="B")),
        "A2": SzzRecord(os_cislo="A2", defense=ThesisDefense(znamka="FX")),
    }
    dist = szz_admin_stats(records, [])["dist"]["defense"]
    assert dist["B"] == 1 and dist["F"] == 1   # FX → F


def test_fails_by_dimension() -> None:
    records = {
        "A1": SzzRecord(
            os_cislo="A1",
            overall=SzzOverall(komise="fialová", vysledek_zkousek="F",
                               vysledek_predmety="F", vysledek_studia="Neprospěl",
                               prospel=False),
            subjects=[SubjectExam(predmet="AZINF", znamka="FX", zkousejici="Novák")],
            defense=ThesisDefense(znamka="F", zkousejici="Vedoucí"),
        ),
        "A2": _rec("A2", "fialová", "A", True,
                   [("AZKYB", "A", "Svoboda", "200", "")]),
    }
    c = Committee(color="fialová", slots=[
        DefenseSlot(personal_number="A1", student_name="Jan Novotný"),
        DefenseSlot(personal_number="A2", student_name="Eva Malá"),
    ])
    fails = szz_admin_stats(records, [c])["fails"]

    assert [f["os"] for f in fails["subjects"]] == ["A1"]
    assert fails["subjects"][0]["jmeno"] == "Jan Novotný"   # z rozpisu komise
    assert fails["subjects"][0]["predmet"] == "AZINF"
    assert fails["subjects"][0]["zkousejici"] == "Novák"

    assert [f["os"] for f in fails["predmety"]] == ["A1"]
    assert [f["os"] for f in fails["defense"]] == ["A1"]
    assert [f["os"] for f in fails["overall"]] == ["A1"]
    # úspěšný student se v žádné dimenzi neobjeví
    assert all(f["os"] != "A2" for lst in fails.values() for f in lst)


def test_overall_fail_on_studia_neprospel_and_name_fallback() -> None:
    # Neprospěl bez známky F (jen výsledek studia) + jméno z parsed záznamu.
    records = {
        "A5": SzzRecord(
            os_cislo="A5", jmeno="Petr", prijmeni="Dvořák",
            overall=SzzOverall(vysledek_zkousek="", vysledek_studia="Neprospěl"),
        ),
    }
    fails = szz_admin_stats(records, [])["fails"]   # prázdné komise → vše
    assert [f["os"] for f in fails["overall"]] == ["A5"]
    assert fails["overall"][0]["jmeno"] == "Dvořák Petr"   # fallback z parsed
    assert not (fails["subjects"] or fails["predmety"] or fails["defense"])


def test_overall_fail_ignores_nevyplneno_placeholder() -> None:
    # KLÍČOVÉ: nehodnocený student (placeholder výsledku studia, případně stale
    # prospel=False v cache) NESMÍ být v „Celkově Neprospěl" — je jen bez známky.
    records = {
        "A6": SzzRecord(
            os_cislo="A6",
            overall=SzzOverall(vysledek_zkousek="", prospel=False,
                               vysledek_studia="--- Nevyplněno ---"),
        ),
    }
    fails = szz_admin_stats(records, [])["fails"]
    assert fails["overall"] == []
    assert szz_admin_stats(records, [])["totals"]["bez_znamky"] == 1
