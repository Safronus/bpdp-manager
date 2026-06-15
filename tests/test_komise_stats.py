"""Statistika obhajob komisí — agregace a párování stavů ze STAG.

Pokrývá čistou logiku `services.komise_stats` (kategorie, agregace dle barvy
i členů) a párovací/časové helpery v `ui.stag_check` (bez sítě).
"""

from __future__ import annotations

import os
from datetime import datetime

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from bpdpmanager.models.komise import Committee, CommitteeMember, DefenseSlot
from bpdpmanager.services.komise_stats import (
    CAT_DEFENDED,
    CAT_FAILED,
    CAT_NONE,
    CAT_UNFINISHED,
    category_from_code,
    committee_defense_stats,
    czech_sort_key,
    member_surname,
    slot_key,
)


def test_category_from_code() -> None:
    assert category_from_code("DUO") == CAT_DEFENDED
    assert category_from_code("DBUO") == CAT_FAILED
    assert category_from_code("OPUNO") == CAT_FAILED
    assert category_from_code("ND") == CAT_UNFINISHED
    assert category_from_code("R") == CAT_NONE
    assert category_from_code("DBPOO") == CAT_NONE
    assert category_from_code("") == CAT_NONE
    assert category_from_code("XYZ") == CAT_NONE


def test_slot_key_prefers_personal_number() -> None:
    assert slot_key("a23625", "Marko Adámek") == "A23625"
    # Bez osobního čísla → foldované jméno (bez diakritiky, lowercase).
    assert slot_key("", "Marko Adámek") == "marko adamek"


def _committee(color, level, obor, members, slots) -> Committee:
    return Committee(
        academic_year="2025/2026", color=color, level=level, obor=obor,
        members=[CommitteeMember(role="Člen", name=m) for m in members],
        slots=[DefenseSlot(date="17. 6. 2026", time=t, personal_number=p,
                           student_name=n) for (t, p, n) in slots],
    )


def test_committee_defense_stats_by_color_and_member() -> None:
    c1 = _committee("modrá", "Mgr", "NSWI", ["Karel Předseda", "Eva Členka"], [
        ("09:00", "A1", "Anna Vedena"),
        ("10:00", "A2", "Petr Druhy"),
        ("11:00", "A3", "Jan Třetí"),
    ])
    c2 = _committee("červená", "Bc", "SWI", ["Karel Předseda"], [
        ("09:00", "A4", "Lucie Čtvrtá"),
    ])
    states = {
        "A1": CAT_DEFENDED,
        "A2": CAT_FAILED,
        # A3 nezadáno → none; A4 nezadáno → none
    }
    stats = committee_defense_stats([c1, c2], states)

    by_color = {(r["color"]): r for r in stats["by_color"]}
    assert by_color["modrá"][CAT_DEFENDED] == 1
    assert by_color["modrá"][CAT_FAILED] == 1
    assert by_color["modrá"][CAT_NONE] == 1
    assert by_color["modrá"]["total"] == 3
    assert by_color["červená"][CAT_NONE] == 1 and by_color["červená"]["total"] == 1

    assert stats["totals"][CAT_DEFENDED] == 1
    assert stats["totals"][CAT_FAILED] == 1
    assert stats["totals"][CAT_NONE] == 2

    # Karel je v obou komisích → součet 3+1 studentů; Eva jen v modré (3).
    by_member = {m["name"]: m for m in stats["by_member"]}
    assert by_member["Karel Předseda"]["total"] == 4
    assert by_member["Karel Předseda"][CAT_DEFENDED] == 1
    assert by_member["Karel Předseda"][CAT_NONE] == 2
    assert by_member["Eva Členka"]["total"] == 3


def test_member_surname_strips_titles() -> None:
    assert member_surname("prof. Ing. Jan Mareš, Ph.D.") == "Mareš"
    assert member_surname("Ing. et Ing. Erik Král, Ph.D.") == "Král"
    assert member_surname("prof. Ing. Zuzana Komínková Oplatková, Ph.D.") == "Oplatková"
    assert member_surname("Karel Novák") == "Novák"


def test_strip_academic_titles_and_key() -> None:
    from bpdpmanager.services.komise_stats import (
        strip_academic_titles,
        student_name_key,
    )

    assert strip_academic_titles("Ing. Matěj Suchánek") == "Matěj Suchánek"
    assert strip_academic_titles("doc. Ing. Bc. Jan Novák") == "Jan Novák"
    assert strip_academic_titles("Ing. et Ing. Erik Král") == "Erik Král"
    assert strip_academic_titles("Marko Vzorek") == "Marko Vzorek"
    # Klíč pro párování: bez titulů, bez diakritiky, lowercase.
    assert student_name_key("Ing. Matěj Suchánek") == "matej suchanek"
    assert student_name_key("Matěj Suchánek") == "matej suchanek"


def test_czech_sort_key_order() -> None:
    names = ["Žáček", "Čermák", "Adam", "Cibulka", "Drozd", "Šimek", "Sýkora"]
    # Č za C, Š za S, Ž poslední — česká abeceda.
    assert sorted(names, key=czech_sort_key) == [
        "Adam", "Cibulka", "Čermák", "Drozd", "Sýkora", "Šimek", "Žáček"]


def test_committee_defense_stats_members_sorted_by_surname() -> None:
    c = _committee("modrá", "Mgr", "NSWI",
                   ["prof. Ing. Petr Žáček, Ph.D.",
                    "doc. Ing. Petr Čermák, Ph.D.",
                    "Ing. Karel Adam, Ph.D."],
                   [("09:00", "A1", "Kdo Ví")])
    stats = committee_defense_stats([c], {})
    order = [member_surname(m["name"]) for m in stats["by_member"]]
    assert order == ["Adam", "Čermák", "Žáček"]


def test_committee_defense_stats_default_none() -> None:
    c = _committee("zelená", "Bc", "ITA", ["A B"], [("09:00", "A9", "Kdo Ví")])
    stats = committee_defense_stats([c], {})
    assert stats["totals"][CAT_NONE] == 1
    assert stats["totals"][CAT_DEFENDED] == 0


def test_needs_committee_query_timing() -> None:
    from bpdpmanager.ui.stag_check import _needs_committee_query

    slot = datetime(2026, 6, 17, 11, 0)
    # Před koncem (obhajoba + 30 min) se neptá.
    assert _needs_committee_query(slot, datetime(2026, 6, 17, 11, 20)) is False
    assert _needs_committee_query(slot, datetime(2026, 6, 17, 11, 29)) is False
    # Po čase obhajoby + 30 min se ptá.
    assert _needs_committee_query(slot, datetime(2026, 6, 17, 11, 31)) is True
    # Neznámý čas → ptáme se.
    assert _needs_committee_query(None, datetime(2026, 6, 17, 11, 0)) is True


def test_fetch_progress_total_counts_pending(monkeypatch) -> None:
    """Progress „total" = počet studentů ke kontrole (po čase obhajoby, bez výsledku)."""
    from bpdpmanager.services import stag_api
    from bpdpmanager.ui import stag_check

    # Komise se 2 sloty dnes dopoledne (čas + 30 min už uplynul).
    c = _committee("modrá", "Mgr", "NSWI", ["A B"], [
        ("09:00", "A1", "Anna Vedena"),
        ("10:00", "A2", "Petr Druhy"),
    ])
    for s in c.slots:
        s.date = "16. 6. 2026"
    monkeypatch.setattr(stag_api, "search_theses", lambda *a, **k: [])

    seen: list[tuple[int, int]] = []
    now = datetime(2026, 6, 16, 12, 0)  # dnes po obhajobách
    stag_check.fetch_committee_defense_states(
        None, [c], now, {}, progress=lambda d, t: seen.append((d, t)))
    assert seen and seen[-1] == (2, 2)        # oba zkontrolováni z 2
    assert seen[0][1] == 2                      # total = 2 hned na začátku


def test_committee_matches_filter() -> None:
    from bpdpmanager.services.komise_stats import fold_name
    from bpdpmanager.ui.komise_tab import KomiseTab

    c = _committee("modrá", "Mgr", "NSWI",
                   ["prof. Ing. Petr Žáček, Ph.D."],
                   [("09:00", "A23625", "Marko Adámek")])
    match = KomiseTab._committee_matches_filter
    # Část jména studenta, bez diakritiky, nezáleží na velikosti.
    assert match(c, fold_name("adamek"))
    assert match(c, fold_name("MARKO"))
    # Část jména člena (i bez diakritiky/titulů).
    assert match(c, fold_name("zacek"))
    # Osobní číslo.
    assert match(c, "a23625")
    # Nic neodpovídá.
    assert not match(c, fold_name("novak"))


def test_nice_step() -> None:
    from bpdpmanager.ui.komise_tab import _nice_step

    assert _nice_step(3, 4) == 1
    assert _nice_step(23, 4) == 10
    assert _nice_step(120, 4) == 50
    assert _nice_step(8, 4) == 2


def test_force_queries_before_defense_time(monkeypatch) -> None:
    """force=True (ruční Aktualizovat) dotáže i studenty PŘED časem obhajoby,
    ale terminální (z cache) přeskočí."""
    from bpdpmanager.services import stag_api
    from bpdpmanager.services.komise_stats import CAT_DEFENDED, slot_key
    from bpdpmanager.ui import stag_check

    c = _committee("modrá", "Bc", "SWI", ["A B"], [
        ("15:00", "A1", "Anna Vedena"),     # obhajoba dnes pozdě odpoledne
        ("15:00", "A2", "Petr Druhy"),
    ])
    for s in c.slots:
        s.date = "16. 6. 2026"
    monkeypatch.setattr(stag_api, "search_theses", lambda *a, **k: [])

    now = datetime(2026, 6, 16, 9, 0)   # ráno, PŘED obhajobami (15:00)
    # Tichá kontrola (force=False): nikoho se neptá (čas ještě nenastal).
    seen_quiet: list[tuple[int, int]] = []
    stag_check.fetch_committee_defense_states(
        None, [c], now, {}, progress=lambda d, t: seen_quiet.append((d, t)))
    assert seen_quiet[0][1] == 0

    # Ruční (force=True): dotáže oba, ale jeden už je v cache jako obhájeno.
    prior = {slot_key("A1", "Anna Vedena"): CAT_DEFENDED}
    seen_force: list[tuple[int, int]] = []
    stag_check.fetch_committee_defense_states(
        None, [c], now, prior, force=True,
        progress=lambda d, t: seen_force.append((d, t)))
    assert seen_force[0][1] == 1   # jen A2 (A1 terminální → přeskočen)


def test_quiet_check_only_current_day(monkeypatch) -> None:
    """Tichá kontrola (force=False) řeší jen AKTUÁLNÍ den — předchozí dny jsou
    v cache, takže se po startu nezatěžuje STAG kontrolou všech."""
    from bpdpmanager.services import stag_api
    from bpdpmanager.ui import stag_check

    c = _committee("modrá", "Bc", "SWI", ["A B"], [
        ("09:00", "A1", "Vcera Student"),   # včera
        ("09:00", "A2", "Dnes Student"),    # dnes
    ])
    c.slots[0].date = "15. 6. 2026"
    c.slots[1].date = "16. 6. 2026"
    monkeypatch.setattr(stag_api, "search_theses", lambda *a, **k: [])

    now = datetime(2026, 6, 16, 12, 0)   # dnes, po čase obhajoby
    seen: list[tuple[int, int]] = []
    stag_check.fetch_committee_defense_states(
        None, [c], now, {}, progress=lambda d, t: seen.append((d, t)))
    assert seen[0][1] == 1   # jen dnešní (A2); včerejší (A1) se neřeší


def test_force_skips_future_days(monkeypatch) -> None:
    """force=True kontroluje jen aktuální den a dříve, ne budoucí dny."""
    from bpdpmanager.services import stag_api
    from bpdpmanager.ui import stag_check

    c = _committee("modrá", "Bc", "SWI", ["A B"], [
        ("09:00", "A1", "Dnes Student"),
        ("09:00", "A2", "Zitra Student"),
    ])
    c.slots[0].date = "16. 6. 2026"   # dnes
    c.slots[1].date = "17. 6. 2026"   # zítra → přeskočit
    monkeypatch.setattr(stag_api, "search_theses", lambda *a, **k: [])

    now = datetime(2026, 6, 16, 12, 0)
    seen: list[tuple[int, int]] = []
    stag_check.fetch_committee_defense_states(
        None, [c], now, {}, force=True,
        progress=lambda d, t: seen.append((d, t)))
    assert seen[0][1] == 1   # jen dnešní slot (A1), zítřejší (A2) přeskočen


def test_match_committee_result() -> None:
    from bpdpmanager.services.stag_api import StagThesisResult
    from bpdpmanager.ui.stag_check import _match_committee_result

    c = Committee(academic_year="2025/2026", color="modrá", level="Mgr", obor="NSWI")
    slot = DefenseSlot(student_name="Anna Vedená", personal_number="A1")

    results = [
        # Jmenovec ze špatného roku → odmítnout.
        StagThesisResult(adipidno="1", surname="Vedená", name="Anna",
                         type_label="Diplomová práce", year="2022", status_code="DUO"),
        # Správná: jméno + typ (Mgr=diplomová) + rok obhajoby 2026.
        StagThesisResult(adipidno="2", surname="Vedená", name="Anna",
                         type_label="Diplomová práce", year="2026", status_code="DUO"),
    ]
    m = _match_committee_result(results, slot, c)
    assert m is not None and m.adipidno == "2"

    # Špatný typ (bakalářská u Mgr komise) → žádná shoda.
    bc_only = [StagThesisResult(adipidno="3", surname="Vedená", name="Anna",
                                type_label="Bakalářská práce", year="2026",
                                status_code="DUO")]
    assert _match_committee_result(bc_only, slot, c) is None

    # Jiné jméno → žádná shoda.
    other = [StagThesisResult(adipidno="4", surname="Nový", name="Pavel",
                              type_label="Diplomová práce", year="2026")]
    assert _match_committee_result(other, slot, c) is None


def test_match_disambiguates_namesake_by_academic_year() -> None:
    """Jmenovec z jiného roku se nesmí přiřadit (regrese: Kubíček 2019/2020
    vs. 2025/2026). Rok obhajoby musí spadat do akad. roku komise."""
    from bpdpmanager.services.stag_api import StagThesisResult
    from bpdpmanager.ui.stag_check import _match_committee_result

    c = Committee(academic_year="2025/2026", color="fialová", level="Mgr",
                  obor="NKYB")
    slot = DefenseSlot(student_name="Daniel Václav Kubíček", personal_number="A23259")

    # Starý jmenovec (2019/2020, obhájeno) + aktuální práce (2025/2026).
    results = [
        StagThesisResult(adipidno="old", surname="Kubíček", name="Daniel",
                         type_label="Diplomová práce", year="2020", status_code="ND"),
        StagThesisResult(adipidno="new", surname="Kubíček", name="Daniel Václav",
                         type_label="Diplomová práce", year="2026", status_code="R"),
    ]
    m = _match_committee_result(results, slot, c)
    assert m is not None and m.adipidno == "new"

    # Jen starý jmenovec z jiného roku → raději nic (ne špatný stav).
    only_old = [results[0]]
    assert _match_committee_result(only_old, slot, c) is None

    # Podzimní termín téhož akad. roku (rok obhajoby 2025) je platný.
    autumn = [StagThesisResult(adipidno="aut", surname="Kubíček",
                               name="Daniel Václav", type_label="Diplomová práce",
                               year="2025", status_code="DUO")]
    m2 = _match_committee_result(autumn, slot, c)
    assert m2 is not None and m2.adipidno == "aut"
