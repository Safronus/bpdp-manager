"""Testy parseru „Zapisovatel u státnic" nad SYNTETICKÝM HTML (fiktivní data)."""

from __future__ import annotations

from bpdpmanager.models.szz_result import SzzOverall, SzzRecord
from bpdpmanager.services.szz_parser import (
    detect_page_name,
    has_zapisovatel_role,
    is_logged_in,
    is_terminal,
    merge_pages,
    parse_page,
    szz_to_check,
)

# ── syntetické fixtures (struktura jako portál, data fiktivní) ─────────────
_ROLE = (
    '<select name="identifikatorRole">'
    '<option value="X" selected="selected">Zapisovatel státnic: AKAT: TESTUSER</option>'
    "</select>"
)
_SEARCH = '<input type="text" name="studentSearchOsCislo" value="">'


def _option(val, text, selected):
    sel = ' selected="selected"' if selected else ""
    return f'<option value="{val}"{sel}>{text}</option>'


def _subject_form(predmet, znamka_val, znamka_txt, examiner, ucitidno):
    fid = f"AKAT_{predmet}_2025_2025_LS_A99999"
    znamky = "".join(
        _option(v, t, v == znamka_val)
        for v, t in [("1", "A - výborně"), ("2", "B - velmi dobře")]
    )
    return (
        f'<form name="ZUSStatnicovePredmety{fid}">'
        f'<input type="hidden" name="FORM_INSTANCE_ID" value="{fid}">'
        '<input type="hidden" name="FORM_portlet_page_name" value="zaverecne-zkousky">'
        f'<select name="prZnamka">{znamky}</select>'
        f'<input type="text" name="prZkousejici" value="{examiner}">'
        f'<input type="hidden" name="prUcitidno" value="{ucitidno}">'
        '<input type="text" name="prZiskanychBodu" value="">'
        '<input type="text" name="prCisloPokusu" value="1">'
        '<input type="text" name="prDatum" value="15.6.2026">'
        '<select name="prJazyk"><option value="CZ" selected="selected">Čeština</option></select>'
        '<textarea name="prPrubeh">&lt;p&gt;Otázka 1. Co je to test?&lt;/p&gt;</textarea>'
        "</form>"
    )


PAGE_SUBJECTS = (
    '<input type="hidden" name="FORM_portlet_page_name" value="userInfoMain">'
    + _ROLE + _SEARCH
    + _subject_form("APRX", "1", "A - výborně", "Jan Zkoušející", "1001")
    + _subject_form("ABCD", "2", "B - velmi dobře", "Eva Druhá", "1002")
)

PAGE_DEFENSE = (
    '<input type="hidden" name="FORM_portlet_page_name" value="obhajoba-kv-prace">'
    + _ROLE + _SEARCH
    + '<input type="hidden" name="obhajobaAdipidno" value="55555">'
    '<select name="obhajobaZnamka"><option value="2" selected="selected">B - velmi dobře</option></select>'
    '<select name="znamkaVedouci"><option value="1" selected="selected">A - výborně</option></select>'
    '<select name="znamkaOponent"><option value="2" selected="selected">B - velmi dobře</option></select>'
    '<input type="text" name="obhajobaZkousejici" value="Petr Předseda">'
    '<input type="hidden" name="obhajobaUcitidno" value="2001">'
    '<input type="text" name="obhajobaCisloPokusu" value="1">'
    '<input type="text" name="obhajobaDatum" value="15.6.2026">'
    '<textarea name="obhajobaPrubeh">&lt;p&gt;Obhajoba proběhla dobře.&lt;/p&gt;</textarea>'
)

PAGE_OVERALL = (
    '<input type="hidden" name="FORM_portlet_page_name" value="celkova-klasifikace">'
    + _ROLE + _SEARCH
    + '<input type="text" name="ckOsCislo" value="A99999">'
    '<select name="ckVysledekZkousek"><option value="1" selected="selected">A - výborně</option></select>'
    '<select name="ckVysledekStudia"><option value="A" selected="selected">Prospěl</option></select>'
    '<select name="ckMisto"><option value="Z" selected="selected">Ve Zlíně</option></select>'
    '<input type="text" name="ckKomise" value="fialová">'
    '<input type="text" name="ckPokus" value="1">'
    '<input type="text" name="ckDatum" value="15.6.2026">'
    '<input type="text" name="ckCas" value="09:00">'
)


# ── testy ──────────────────────────────────────────────────────────────────
def test_detect_page_prefers_known_over_userinfo() -> None:
    assert detect_page_name(PAGE_SUBJECTS) == "zaverecne-zkousky"
    assert detect_page_name(PAGE_DEFENSE) == "obhajoba-kv-prace"
    assert detect_page_name(PAGE_OVERALL) == "celkova-klasifikace"


def test_login_and_role_detection() -> None:
    assert is_logged_in(PAGE_SUBJECTS)
    assert has_zapisovatel_role(PAGE_SUBJECTS)
    assert not is_logged_in("<html>login form <input type=password></html>")


def test_parse_subjects() -> None:
    rec = parse_page(PAGE_SUBJECTS)
    assert rec.os_cislo == "A99999"
    assert [s.predmet for s in rec.subjects] == ["APRX", "ABCD"]
    s0 = rec.subjects[0]
    assert s0.katedra == "AKAT"
    assert s0.znamka == "A" and s0.znamka_text == "A - výborně"
    assert s0.zkousejici == "Jan Zkoušející" and s0.ucitidno == "1001"
    assert s0.pokus == "1" and s0.datum == "15.6.2026" and s0.jazyk == "Čeština"
    # CKEditor HTML v průběhu se vyčistí (žádné <p>)
    assert "<p>" not in s0.prubeh and "Otázka 1" in s0.prubeh


def test_parse_defense() -> None:
    rec = parse_page(PAGE_DEFENSE)
    d = rec.defense
    assert d is not None
    assert d.znamka == "B"
    assert d.znamka_vedouci == "A - výborně"
    assert d.znamka_oponent == "B - velmi dobře"
    assert d.zkousejici == "Petr Předseda" and d.ucitidno == "2001"
    assert d.adipidno == "55555"
    assert "<p>" not in d.prubeh


def test_parse_overall_and_terminal() -> None:
    rec = parse_page(PAGE_OVERALL)
    o = rec.overall
    assert o is not None
    assert o.vysledek_zkousek == "A"
    assert o.vysledek_studia == "Prospěl" and o.prospel is True
    assert o.komise == "fialová" and o.misto == "Ve Zlíně"
    assert o.datum == "15.6.2026" and o.cas == "09:00"


def test_merge_pages_and_terminal_flag() -> None:
    merged = merge_pages(
        parse_page(PAGE_SUBJECTS),
        parse_page(PAGE_DEFENSE),
        parse_page(PAGE_OVERALL),
    )
    assert merged.os_cislo == "A99999"
    assert len(merged.subjects) == 2
    assert merged.defense is not None and merged.overall is not None
    # má vyplněný celkový výsledek studia → terminal
    assert is_terminal(merged) and merged.terminal


def test_not_terminal_without_overall() -> None:
    merged = merge_pages(parse_page(PAGE_SUBJECTS), parse_page(PAGE_DEFENSE))
    assert not is_terminal(merged) and not merged.terminal


def _terminal_rec(oc):
    return SzzRecord(os_cislo=oc, terminal=True,
                     overall=SzzOverall(vysledek_zkousek="A",
                                        vysledek_studia="Prospěl"))


def test_szz_to_check_skips_terminal_and_dedups() -> None:
    cache = {"A1": _terminal_rec("A1"),
             "A2": SzzRecord(os_cislo="A2", terminal=False)}
    # A1 hotový → přeskočit; A2 rozdělaný → kontrolovat; A3 neznámý → kontrolovat;
    # duplicitní A3 a prázdné se odfiltrují.
    got = szz_to_check(["A1", "A2", "A3", "A3", "", "  "], cache, force=False)
    assert got == ["A2", "A3"]


def test_szz_to_check_force_includes_all() -> None:
    cache = {"A1": _terminal_rec("A1")}
    assert szz_to_check(["A1", "A2", "A1"], cache, force=True) == ["A1", "A2"]


def test_placeholder_grade_not_terminal() -> None:
    # Nevyplněná celková známka má ve STAG text „--- Nevyplněno ---" (NE prázdný
    # řetězec). Nesmí se brát jako hotová — jinak „zbývající" ignoruje studenty
    # bez známky (platí i pro starší cache, kde je placeholder uložený).
    from bpdpmanager.services.szz_parser import _letter

    assert _letter("--- Nevyplněno ---") == "" and _letter("A - výborně") == "A"
    rec = SzzRecord(os_cislo="A8", overall=SzzOverall(
        vysledek_zkousek="--- Nevyplněno ---", vysledek_studia="Prospěl"))
    assert not is_terminal(rec)
    assert szz_to_check(["A8"], {"A8": rec}, force=False) == ["A8"]


def test_szz_to_check_rechecks_bez_znamky_and_unavailable() -> None:
    # „Bez známky" (text výsledku studia vyplněn, ale BEZ známky) NENÍ hotový →
    # musí se znovu zkontrolovat. Stejně tak „nedostupné". (Regrese: dřív se
    # „bez známky" přeskakoval, protože terminal se řídil textem výsledku.)
    bez = SzzRecord(os_cislo="A5", overall=SzzOverall(vysledek_studia="Prospěl"))
    nedostupny = SzzRecord(os_cislo="A6", unavailable=True)
    assert not is_terminal(bez)
    assert szz_to_check(["A5", "A6"], {"A5": bez, "A6": nedostupny},
                        force=False) == ["A5", "A6"]
