# ruff: noqa: RUF001 — testovací data zrcadlí reálná PDF (obsahují EN DASH)
"""Komise SZZ — parser (složení/rozpis/barvy), merge ve službě, UI smoke."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from bpdpmanager.services.komise_parser import (
    ParsedCommittee,
    ParsedSchedule,
    academic_year_from_date,
    canonical_date,
    classify_color,
    obor_from_program,
    parse_composition,
    parse_schedule_page,
)


def test_classify_color() -> None:
    assert classify_color((1.0, 0.0, 0.0)) == "červená"
    assert classify_color((0.0, 0.0, 1.0)) == "modrá"
    assert classify_color((0.6, 0.8, 0.0)) == "zelená"
    assert classify_color((1.0, 0.78, 0.0)) == "žlutá"
    assert classify_color((0.5, 0.0, 0.5)) == "fialová"
    assert classify_color((0.5, 0.5, 0.5)) == "šedá"


def test_canonical_date_and_year() -> None:
    assert canonical_date("15.06.2026") == "15. 6. 2026"
    assert canonical_date("15. 6. 2026") == "15. 6. 2026"
    assert academic_year_from_date("15. 6. 2026") == "2025/2026"
    assert academic_year_from_date("1. 10. 2026") == "2026/2027"


_COMPOSITION_A = """Komise pro státní závěrečné zkoušky 2025/2026
Bc. – SWI, SWE: 15. - 16. 6. 2026
Komise červená
Předseda: prof. Ing. Jan Vzor, Ph.D.
Místopředseda: doc. Ing. Petr Druhý, Ph.D.
Tajemník: Ing. Karel Třetí, Ph.D.
Členové: Ing. Jiří Čtvrtý, Ph.D.
Ing. Pavel Pátý, Ph.D.
Komise fialová (15.06.2026)
Předseda: prof. Ing. Jiná Osoba, Ph.D.
Členové: Ing. Další Člen
"""


def test_parse_composition_variant_a() -> None:
    out = parse_composition(_COMPOSITION_A)
    assert [c.color for c in out] == ["červená", "fialová"]
    c = out[0]
    assert c.academic_year == "2025/2026"
    assert c.level == "Bc"
    assert c.program_label == "SWI, SWE"
    assert c.dates == ["15. 6. 2026", "16. 6. 2026"]
    assert ("Předseda", "prof. Ing. Jan Vzor, Ph.D.") in c.members
    assert ("Člen", "Ing. Pavel Pátý, Ph.D.") in c.members   # pokračovací řádek
    assert out[1].dates == ["15. 6. 2026"]                    # z poznámky v závorce


_COMPOSITION_B = """Komise pro státní závěrečné zkoušky 2025/2026
magisterský studijní program – Informační technologie
SP / SO/ specializace Informační technologie - specializace SWI
Komise červená 17.06.2026 - 18.06.2026
Komise: červená
Předseda: prof. Ing. Jan Vzor, Ph.D.
Členové: Ing. Jiří Čtvrtý, Ph.D.
"""


def test_parse_composition_variant_b_dedups_heading() -> None:
    out = parse_composition(_COMPOSITION_B)
    assert len(out) == 1                       # nadpis + „Komise:" = jeden blok
    assert out[0].color == "červená"
    assert out[0].level == "Mgr"
    assert len(out[0].members) == 2


def test_composition_header_before_komise_assigns_to_right_committee() -> None:
    """Datum/specializace stojí PŘED řádkem „Komise:" — parser je nesmí vzít
    z NÁSLEDUJÍCÍ komise. Dvě stejně barevné komise s jiným dnem a jiným
    složením: člen jen z 19.6 nesmí skončit u té 17.-18. (a naopak). (Fiktivní
    jména, reálná do gitu nepatří.)"""
    text = (
        "magisterský studijní program 2025/2026\n"
        "SP / SO/ specializace Informatika - specializace SWI\n"
        "Datum: 17.06.2026 - 18.6.2026\n"
        "Komise: zelená\n"
        "Předseda: doc. Ing. Alfa Alfová, Ph.D.\n"
        "Členové: Ing. Beta Betová, Ph.D.\n"
        " Ing. Gama Gamová, Ph.D.\n"
        "SP / SO/ specializace Informatika - specializace SWI\n"
        "Datum: 19.06.2026\n"
        "Komise: zelená\n"
        "Předseda: prof. Ing. Delta Deltová, Ph.D.\n"
        "Členové: Ing. Beta Betová, Ph.D.\n"
        " Ing. Epsilon Epsilonová, Ph.D.\n"
    )
    greens = [c for c in parse_composition(text) if c.color == "zelená"]
    assert len(greens) == 2
    g1718 = next(c for c in greens if c.dates == ["17. 6. 2026", "18. 6. 2026"])
    g19 = next(c for c in greens if c.dates == ["19. 6. 2026"])
    n1718 = [n for _, n in g1718.members]
    n19 = [n for _, n in g19.members]
    # 19.6 komise = Delta + Epsilon (správné datum i složení).
    assert any("Delta" in n for n in n19)
    assert any("Epsilon" in n for n in n19)
    # Člen jen z 19.6 (Epsilon) NESMÍ být u 17.-18.; ta má Alfa, ne Delta.
    assert not any("Epsilon" in n for n in n1718)
    assert any("Alfa" in n for n in n1718)
    assert not any("Delta" in n for n in n1718)


def test_composition_variant_a_inline_date_without_parens() -> None:
    """Varianta A s datem ZA barvou bez závorek („Komise zelená 17.06.2026 -
    18.06.2026") se zachytí jako datum komise."""
    text = (
        "magisterský 2025/2026\n"
        "SP / SO/ specializace X - specializace SWI\n"
        "Komise zelená 17.06.2026 - 18.06.2026\n"
        "Komise: zelená\n"
        "Předseda: doc. Alfa Alfová\n"
        "Členové: Ing. Beta Betová\n"
    )
    g = next(c for c in parse_composition(text) if c.color == "zelená")
    assert g.dates == ["17. 6. 2026", "18. 6. 2026"]


_SCHEDULE = """STÁTNÍ ZÁVĚREČNÉ ZKOUŠKY
v bakalářském studijním programu
Softwarové inženýrství
specializace:
Softwarové inženýrství
ZLÍN 15. 6. 2026
16. 6. 2026
Časový rozvrh obhajob a státních závěrečných zkoušek:
15. 6. 2026 16. 6. 2026
09:00 A23625 Marko Vzorek 08:00 A23618 Pranav Druhý
09:45 A23236 Lilyan Třetí 08:45 A23474 David Čtvrtý
14:45 A24837 Ondřej Pátý
"""


def test_parse_schedule_two_columns() -> None:
    ps = parse_schedule_page(_SCHEDULE, "červená")
    assert ps is not None
    assert ps.color == "červená"
    assert ps.level == "Bc"
    assert ps.academic_year == "2025/2026"
    assert ps.dates == ["15. 6. 2026", "16. 6. 2026"]
    # 1. sloupec → 1. datum, 2. sloupec → 2. datum
    assert ("15. 6. 2026", "09:00", "A23625", "Marko Vzorek") in ps.slots
    assert ("16. 6. 2026", "08:00", "A23618", "Pranav Druhý") in ps.slots
    # řádek s jediným zápisem patří 1. sloupci
    assert ("15. 6. 2026", "14:45", "A24837", "Ondřej Pátý") in ps.slots
    assert len(ps.slots) == 5


_SCHEDULE_ABUT = """STÁTNÍ ZÁVĚREČNÉ ZKOUŠKY
v magisterském studijním programu
Informační technologie (Mgr)
specializace:
Softwarové inženýrství (Mgr)
ZLÍN 17. 6. 2026
18. 6. 2026
Časový rozvrh obhajob a státních závěrečných zkoušek:
17. 6. 2026 18. 6. 2026
11:00 A25626 Layth Salah Yahyah Al-Zamili11:00 A24397 Bc. Veronika Krajanová
"""


def test_parse_schedule_long_name_abuts_next_column() -> None:
    """Dlouhé jméno dotýkající se času dalšího sloupce („…Al-Zamili11:00 A…")
    se nesmí slít — oba studenti zvlášť, každý ve svém sloupci/datu."""
    ps = parse_schedule_page(_SCHEDULE_ABUT, "žlutá")
    assert ps is not None
    assert ("17. 6. 2026", "11:00", "A25626", "Layth Salah Yahyah Al-Zamili") in ps.slots
    assert ("18. 6. 2026", "11:00", "A24397", "Bc. Veronika Krajanová") in ps.slots
    assert len(ps.slots) == 2


@pytest.fixture
def service(tmp_path: Path):
    from bpdpmanager.services import ThesisService
    from bpdpmanager.storage import JsonRepository

    repo = JsonRepository(path=tmp_path / "db.json", backup_path=tmp_path / "db.bak")
    return ThesisService(repo)


def test_apply_import_merges_by_year_color_level(service) -> None:
    pc = ParsedCommittee(color="červená", academic_year="2025/2026", level="Bc",
                         program_label="SWI", dates=["15. 6. 2026"],
                         members=[("Předseda", "prof. Jan Vzor")])
    ps = ParsedSchedule(color="červená", academic_year="2025/2026", level="Bc",
                        program_label="Softwarové inženýrství",
                        dates=["15. 6. 2026"],
                        slots=[("15. 6. 2026", "09:00", "A11111", "Jan Test")])
    stats = service.apply_komise_import([pc], [ps], ["2025-2026/a.pdf"])
    assert stats == {"created": 1, "updated": 0, "slots": 1}
    committees = service.list_committees()
    assert len(committees) == 1                # rozpis se sloučil do komise
    c = committees[0]
    assert c.members[0].name == "prof. Jan Vzor"
    assert c.slots[0].personal_number == "A11111"
    assert c.program_label == "Softwarové inženýrství"   # delší label vyhrál
    # Opakovaný import nepřidá duplicity.
    stats2 = service.apply_komise_import([pc], [ps], ["2025-2026/a.pdf"])
    assert stats2["created"] == 0 and stats2["slots"] == 0
    assert len(service.list_committees()) == 1
    assert len(service.list_committees()[0].slots) == 1


@pytest.mark.parametrize(
    "program,level,expected",
    [
        ("Softwarové inženýrství", "Bc", "SWI"),
        ("SWI, SWE", "Bc", "SWI"),
        ("Informační technologie — specializace Softwarové inženýrství", "Mgr", "NSWI"),
        ("Information Technologies - specialization Software Engineering", "Mgr", "NSWI"),
        ("Informační technologie — specializace Kybernetická bezpečnost", "Mgr", "NKYB"),
        ("Učitelství informatiky pro základní a střední školy", "Mgr", "NUI"),
        ("UI", "Mgr", "NUI"),
        ("něco úplně jiného", "Bc", ""),
    ],
)
def test_obor_from_program(program, level, expected) -> None:
    assert obor_from_program(program, level) == expected


def test_load_komise_seed_from_json(service) -> None:
    """Kurátorovaný JSON v gitu se načte; idempotentní; obě Mgr fialová zvlášť."""
    stats = service.load_komise_seed()
    assert stats["created"] == 11 and stats["updated"] == 0
    # Druhé načtení nepřidá duplicity (jen aktualizuje).
    stats2 = service.load_komise_seed()
    assert stats2["created"] == 0 and stats2["updated"] == 11
    cs = service.list_committees()
    assert len(cs) == 11
    assert all(c.from_seed for c in cs)
    # Klíčová kolize: Mgr fialová je NKYB i NUI — dvě různé komise.
    mgr_fialova = sorted(
        c.obor for c in cs if c.level == "Mgr" and c.color == "fialová"
    )
    assert mgr_fialova == ["NKYB", "NUI"]
    # Petr Žáček je v Bc žluté i Mgr žluté.
    zluta = [c for c in cs if c.color == "žlutá"]
    assert all(any("Žáček" in m.name for m in c.members) for c in zluta)


def test_schedule_attaches_by_obor_not_just_color(service) -> None:
    """Rozpis fialová-NUI a fialová-NKYB se napojí na SPRÁVNÉ komise (ne zmíchané)."""
    service.load_komise_seed()
    before = len(service.list_committees())
    nkyb = ParsedSchedule(
        color="fialová", academic_year="2025/2026", level="Mgr", obor="NKYB",
        program_label="Kybernetická bezpečnost", dates=["16. 6. 2026"],
        slots=[("16. 6. 2026", "09:00", "A90001", "Kyb Student")],
    )
    nui = ParsedSchedule(
        color="fialová", academic_year="2025/2026", level="Mgr", obor="NUI",
        program_label="Učitelství informatiky", dates=["19. 6. 2026"],
        slots=[("19. 6. 2026", "08:00", "A90002", "Uci Student")],
    )
    stats = service.apply_komise_import([], [nkyb, nui], ["x.pdf"])
    # Žádná nová komise — obě se napojily na seed komise.
    assert stats["created"] == 0 and stats["slots"] == 2
    assert len(service.list_committees()) == before
    by = {(c.obor): c for c in service.list_committees()
          if c.level == "Mgr" and c.color == "fialová"}
    assert by["NKYB"].slots[0].personal_number == "A90001"
    assert by["NUI"].slots[0].personal_number == "A90002"


def test_reset_committees_clears_old_and_reloads_seed(service) -> None:
    """Reset smaže staré (bez oboru) komise a načte čistý seed; sloty zmizí."""
    # Stará pre-2.5.0 komise bez oboru + slot (simulace „nesedících" dat).
    service.apply_komise_import(
        [],
        [ParsedSchedule(color="fialová", academic_year="2025/2026", level="Mgr",
                        program_label="cosi",
                        slots=[("19. 6. 2026", "08:00", "A99999", "Old")])],
        ["old.pdf"],
    )
    assert any(not c.obor for c in service.list_committees())
    stats = service.reset_committees_from_seed()
    cs = service.list_committees()
    assert stats["created"] == 11 and len(cs) == 11
    assert all(c.from_seed and c.obor for c in cs)
    assert sum(len(c.slots) for c in cs) == 0   # rozpisy se musí naimportovat znovu


def test_highlighting_works_on_seed_committee(service) -> None:
    """Po resetu + importu rozpisu se vedený student zvýrazní (🎓) na seed komisi."""
    from PySide6.QtWidgets import QApplication

    from bpdpmanager.models import Student, Thesis
    from bpdpmanager.models.enums import ThesisStatus, ThesisType
    from bpdpmanager.ui.komise_tab import KomiseTab

    QApplication.instance() or QApplication([])
    service.load_komise_seed()
    s = Student(first_name="Marko", last_name="Test", university_id="A55501")
    service.upsert_student(s)
    service.upsert_thesis(Thesis(type=ThesisType.BP, academic_year="2025/2026",
                                 student_id=s.id, status=ThesisStatus.IN_PROGRESS))
    # Rozpis Bc SWI červená se napojí na seed komisi.
    service.apply_komise_import(
        [],
        [ParsedSchedule(color="červená", academic_year="2025/2026", level="Bc",
                        obor="SWI", program_label="Softwarové inženýrství",
                        dates=["15. 6. 2026"],
                        slots=[("15. 6. 2026", "09:00", "A55501", "Marko Test")])],
        ["rozpis.pdf"],
    )
    roles = service.komise_student_roles()
    assert roles.get("A55501") == "led"      # zvýraznění funguje dál
    cervena = next(c for c in service.list_committees()
                   if c.color == "červená" and c.level == "Bc")
    assert any(s_.personal_number == "A55501" for s_ in cervena.slots)
    # Tab se vykreslí se seed komisemi (rok → Bc/Mgr → 11 komisí celkem).
    from bpdpmanager.ui.komise_tab import ROLE_VO
    tab = KomiseTab(service)
    assert sum(1 for _ in tab._iter_leaves()) == 11
    # Sloupec „Studenti V/O" nese počty (1 vedený, 0 oponovaných) u Bc červené.
    cervena_leaf = next(
        lf for lf in tab._iter_leaves()
        if "červená" in lf.text(0) and "📚 Bakalářské" in lf.parent().text(0)
    )
    assert cervena_leaf.data(1, ROLE_VO) == (1, 0)


def test_komise_tab_responsive_layout(service) -> None:
    """Layout záložky Státnice: sloupce ve splitteru (nepřekrývají se, umí se
    zmenšit); statistika je VŽDY ve 3 záložkách (velké i malé rozlišení)."""
    from PySide6.QtWidgets import (
        QApplication,
        QMainWindow,
        QTabWidget,
        QTextBrowser,
    )

    from bpdpmanager.ui.komise_tab import KomiseTab

    QApplication.instance() or QApplication([])
    win = QMainWindow()
    tabs = QTabWidget()
    win.setCentralWidget(tabs)
    tab = KomiseTab(service)
    tabs.addTab(tab, "S")

    # Tři sloupce ve splitteru (ne fixed-width) → nepřekrývají se a umí se
    # zmenšit hluboko pod šířku okna ze screenshotu (~1100).
    assert tab.cols_splitter.count() == 3
    assert tab.cols_splitter.minimumSizeHint().width() < 900

    # Horní detail nezalamuje → na úzku se nenafoukne do výšky, ale dá vodorovný
    # posuvník.
    assert tab.detail.lineWrapMode() == QTextBrowser.LineWrapMode.NoWrap

    # Statistika = 4 záložky (Podle komise / Graf / Podle členů / Průběh SZZ).
    assert tab.stats_tabs.count() == 4

    # Velké okno: prostřední sloupec bere zbytek; statistika pořád 4 záložky.
    win.resize(2200, 1300)
    win.show()
    QApplication.processEvents()
    QApplication.processEvents()
    big = tab.cols_splitter.sizes()
    assert big[1] > big[0] and big[1] > big[2]
    assert tab.stats_tabs.count() == 4

    # Malé okno: beze změny režimu statistiky (taky 4 záložky).
    win.resize(1000, 760)
    QApplication.processEvents()
    QApplication.processEvents()
    assert tab.stats_tabs.count() == 4

    win.close()


def test_my_defense_schedule(service) -> None:
    """Harmonogram: vedené + oponované sloty chronologicky, s komisí (kde)."""
    from bpdpmanager.models import OpposingThesis, Student, Thesis
    from bpdpmanager.models.enums import ThesisStatus, ThesisType

    service.load_komise_seed()
    s = Student(first_name="Anna", last_name="Vedena", university_id="A10001")
    service.upsert_student(s)
    service.upsert_thesis(Thesis(type=ThesisType.BP, academic_year="2025/2026",
                                 student_id=s.id, status=ThesisStatus.IN_PROGRESS))
    service.upsert_opposing_thesis(OpposingThesis(
        type=ThesisType.DP, academic_year="2025/2026",
        student_first_name="Karel", student_last_name="Oponovan"))
    service.apply_komise_import([], [
        # Oponovaný je dřív (15.6 09:00) a vedený později (17.6) — ověř řazení.
        ParsedSchedule(color="modrá", academic_year="2025/2026", level="Mgr",
                       obor="NSWI", program_label="SWI", dates=["17. 6. 2026"],
                       slots=[("17. 6. 2026", "11:00", "A10001", "Anna Vedena")]),
        ParsedSchedule(color="červená", academic_year="2025/2026", level="Mgr",
                       obor="NSWI", program_label="SWI", dates=["15. 6. 2026"],
                       slots=[("15. 6. 2026", "09:00", "A99", "Karel Oponovan")]),
    ], ["x.pdf"])
    sched = service.my_defense_schedule()
    assert len(sched) == 2
    # Chronologicky: 15. 6. (oponovaný) před 17. 6. (vedený).
    assert sched[0]["date"] == "15. 6. 2026" and sched[0]["role"] == "opp"
    assert sched[1]["date"] == "17. 6. 2026" and sched[1]["role"] == "led"
    # „Kde" = komise (barva + obor).
    assert sched[1]["color"] == "modrá" and sched[1]["obor"] == "NSWI"
    assert sched[0]["personal_number"] == "A99"


def test_opposing_matched_by_personal_number_despite_title(service) -> None:
    """Oponovaný (aktuální rok) se spáruje přes osobní číslo i s titulem v PDF.

    Regrese: dřív se oponovaní párovali jen jménem, takže „Ing. Matěj Suchánek"
    v rozpisu se nespároval s prací „Matěj Suchánek" (bez titulu).
    """
    from bpdpmanager.models import OpposingThesis
    from bpdpmanager.models.enums import ThesisType

    cur = service.current_academic_year()
    service.load_komise_seed()
    service.upsert_opposing_thesis(OpposingThesis(
        type=ThesisType.BP, academic_year=cur,
        student_first_name="Matěj", student_last_name="Suchánek",
        student_university_id="A12345"))
    service.apply_komise_import([], [
        ParsedSchedule(color="fialová", academic_year=cur, level="Bc",
                       obor="SWI", program_label="SWI", dates=["10. 6. 2026"],
                       slots=[("10. 6. 2026", "09:00", "A12345",
                               "Ing. Matěj Suchánek")]),
    ], ["swi_bc.pdf"])
    sched = service.my_defense_schedule()
    mine = [e for e in sched if e["personal_number"] == "A12345"]
    assert mine and mine[0]["role"] == "opp"


def test_opposing_matched_by_name_without_personal_number(service) -> None:
    """Bez osobního čísla: fallback dle jména **bez titulů** (rozpis má titul)."""
    from bpdpmanager.models import OpposingThesis
    from bpdpmanager.models.enums import ThesisType

    cur = service.current_academic_year()
    service.load_komise_seed()
    service.upsert_opposing_thesis(OpposingThesis(
        type=ThesisType.BP, academic_year=cur,
        student_first_name="Matěj", student_last_name="Suchánek"))
    service.apply_komise_import([], [
        ParsedSchedule(color="fialová", academic_year=cur, level="Bc",
                       obor="SWI", program_label="SWI", dates=["10. 6. 2026"],
                       slots=[("10. 6. 2026", "09:00", "", "Ing. Matěj Suchánek")]),
    ], ["swi_bc.pdf"])
    sched = service.my_defense_schedule()
    assert any(e["role"] == "opp" and "Suchánek" in e["student_name"]
               for e in sched)


def test_historical_supervised_not_matched_in_current_committee(service) -> None:
    """Práci vedenou v minulosti (Obhájeno) nesmí aktuální rozpis označit jako
    aktuálně vedenou — ani přes jméno bez titulu (regrese 2.5.28)."""
    from bpdpmanager.models import Student, Thesis
    from bpdpmanager.models.enums import ThesisStatus, ThesisType

    cur = service.current_academic_year()
    service.load_komise_seed()
    s = Student(first_name="Jan", last_name="Novák", university_id="A21111")
    service.upsert_student(s)
    # Historická BP práce (minulý rok, Obhájeno) — NEvedu ji teď.
    service.upsert_thesis(Thesis(type=ThesisType.BP, academic_year="2023/2024",
                                 student_id=s.id, status=ThesisStatus.DEFENDED))
    # Aktuální Mgr rozpis: stejné jméno (s titulem Bc.) a jiné osobní číslo.
    service.apply_komise_import([], [
        ParsedSchedule(color="fialová", academic_year=cur, level="Mgr",
                       obor="NKYB", program_label="NKYB", dates=["10. 6. 2026"],
                       slots=[("10. 6. 2026", "09:00", "A23222", "Bc. Jan Novák")]),
    ], ["nkyb_mgr.pdf"])
    assert service.komise_student_roles().get("a21111".upper()) != "led"
    sched = service.my_defense_schedule()
    assert not any(e["student_name"] == "Bc. Jan Novák" for e in sched)


def test_parse_schedule_orphan_right_column_goes_to_second_date() -> None:
    """Řádek jen s pravým sloupcem (2. den) nesmí spadnout do 1. dne.

    pypdf u osamoceného pravého sloupce nechá malé odsazení (mezeru) — podle
    něj se rozliší, že patří k 2. datu (regrese: Liasnichy/Mlynár 16.6 → 15.6).
    """
    from bpdpmanager.services.komise_parser import parse_schedule_page

    text = (
        "Časový rozvrh obhajob a státních závěrečných zkoušek:\n"
        "15. 6. 2026 16. 6. 2026\n"
        "09:00 A23001 Anna Vzorová 08:00 A23101 Petr Pravý\n"
        "10:00 A23002 Bára Vzorová 09:00 A23102 Pavel Pravý\n"
        " 10:00 A23103 Karel Sirotek\n"
        " 11:00 A23104 Eva Sirotková\n"
    )
    ps = parse_schedule_page(text, "zelená")
    assert ps is not None and ps.dates == ["15. 6. 2026", "16. 6. 2026"]
    by_pnum = {s[2]: s[0] for s in ps.slots}
    assert by_pnum["A23103"] == "16. 6. 2026"   # osamocený pravý → 2. den
    assert by_pnum["A23104"] == "16. 6. 2026"
    assert by_pnum["A23001"] == "15. 6. 2026"   # levý sloupec drží 1. den
    assert by_pnum["A23101"] == "16. 6. 2026"   # párový pravý → 2. den


def test_parse_schedule_orphan_left_column_stays_first_date() -> None:
    """Delší LEVÝ sloupec: osamocené řádky bez odsazení zůstanou na 1. dni."""
    from bpdpmanager.services.komise_parser import parse_schedule_page

    text = (
        "Časový rozvrh obhajob a státních závěrečných zkoušek:\n"
        "17. 6. 2026 18. 6. 2026\n"
        "09:00 A23001 Anna Levá 09:00 A23101 Petr Pravý\n"
        "10:00 A23002 Bára Levá 10:00 A23102 Pavel Pravý\n"
        "11:00 A23003 Cyril Levý\n"
        "12:00 A23004 Dana Levá\n"
    )
    ps = parse_schedule_page(text, "modrá")
    by_pnum = {s[2]: s[0] for s in ps.slots}
    assert by_pnum["A23003"] == "17. 6. 2026"
    assert by_pnum["A23004"] == "17. 6. 2026"


def test_komise_defense_states_persist_roundtrip(service) -> None:
    """Cache stavů obhajob se uloží na disk a po načtení vrátí (stejný rok);
    z jiného roku se ignoruje (čistá tabulka po startu)."""
    import json

    assert service.load_komise_defense_states() == {}     # zatím nic uloženo
    states = {"A12345": "defended", "jan novak": "failed"}
    service.save_komise_defense_states(states)
    assert service.load_komise_defense_states() == states

    # Podvrhni jiný akademický rok → načtení vrátí prázdno.
    p = service._komise_states_path()
    data = json.loads(p.read_text(encoding="utf-8"))
    data["academic_year"] = "1999/2000"
    p.write_text(json.dumps(data), encoding="utf-8")
    assert service.load_komise_defense_states() == {}


def test_future_year_shows_no_composition_notice(service) -> None:
    """Rok bez kurátorovaného složení (jen import rozpisu) → upozornění."""
    from PySide6.QtWidgets import QApplication

    from bpdpmanager.ui.komise_tab import ROLE_YEAR, KomiseTab

    QApplication.instance() or QApplication([])
    service.load_komise_seed()
    service.apply_komise_import([], [
        ParsedSchedule(color="modrá", academic_year="2026/2027", level="Bc",
                       obor="SWI", program_label="SWI", dates=["15. 6. 2027"],
                       slots=[("15. 6. 2027", "09:00", "A1", "X Y")]),
    ], ["x.pdf"])
    tab = KomiseTab(service)

    def select_year(y):
        for i in range(tab.tree.topLevelItemCount()):
            it = tab.tree.topLevelItem(i)
            if it.data(0, ROLE_YEAR) == y:
                tab.tree.setCurrentItem(it)
                return it
        return None

    yr = select_year("2026/2027")
    assert "zatím není v aplikaci" in tab.detail.toPlainText()   # přehled roku
    leaf = yr.child(0).child(0)
    tab.tree.setCurrentItem(leaf)
    assert "zatím není v aplikaci" in tab.detail.toPlainText()   # detail komise
    # Rok se seed složením → žádné upozornění.
    select_year("2025/2026")
    assert "zatím není v aplikaci" not in tab.detail.toPlainText()


def test_right_harmonogram_independent_and_countdown(service) -> None:
    """Pravý panel = harmonogram roku, nezávislý na komisi; odpočet u nejbližšího."""
    from datetime import datetime, timedelta

    from PySide6.QtWidgets import QApplication

    from bpdpmanager.models import Student, Thesis
    from bpdpmanager.models.enums import ThesisStatus, ThesisType
    from bpdpmanager.ui.komise_tab import ROLE_COMMITTEE_ID, KomiseTab

    QApplication.instance() or QApplication([])
    service.load_komise_seed()
    cur = service.current_academic_year()
    s = Student(first_name="Anna", last_name="Vedena", university_id="A10001")
    service.upsert_student(s)
    service.upsert_thesis(Thesis(type=ThesisType.BP, academic_year=cur,
                                 student_id=s.id, status=ThesisStatus.IN_PROGRESS))
    now = datetime.now()
    near = now + timedelta(minutes=8)
    # Datum odvozeno z `near` (ne `now`) — jinak by se u přelomu půlnoci čas
    # přehoupl na další den, ale datum zůstalo dnešní → slot „v minulosti".
    dstr = f"{near.day}. {near.month}. {near.year}"
    service.apply_komise_import([], [
        ParsedSchedule(color="červená", academic_year=cur, level="Bc", obor="SWI",
                       program_label="SWI", dates=[dstr],
                       slots=[(dstr, near.strftime("%H:%M"), "A10001", "Anna Vedena")]),
    ], ["r.pdf"])
    tab = KomiseTab(service)
    # Vyber libovolnou komisi — pravý harmonogram je nezávislý (rok = aktuální).
    target = next(c for c in service.list_committees()
                  if c.color == "modrá" and c.level == "Bc")
    leaf = next(lf for lf in tab._iter_leaves()
                if lf.data(0, ROLE_COMMITTEE_ID) == target.id)
    tab.tree.setCurrentItem(leaf)
    harm = tab.harmonogram_view.toPlainText()
    assert "Můj harmonogram" in harm and cur in harm
    assert "Anna Vedena" in harm           # nezávislé na vybrané komisi
    assert "⏳" in harm                      # odpočet u nejbližšího
    # _nearest_upcoming vrátí ten správný slot.
    entries = [e for e in service.my_defense_schedule() if e["academic_year"] == cur]
    nearest, _dt = tab._nearest_upcoming(entries, now)
    assert nearest and nearest["personal_number"] == "A10001"


def test_right_harmonogram_history_section(service) -> None:
    """Pravý harmonogram má nahoře nadcházející a dole sekci Historie —
    hotoví studenti (Obhájeno/Neobhájeno) se přesunou dolů, ne zmizí."""
    from datetime import datetime, timedelta

    from PySide6.QtWidgets import QApplication

    from bpdpmanager.models import Student, Thesis
    from bpdpmanager.models.enums import ThesisStatus, ThesisType
    from bpdpmanager.ui.komise_tab import KomiseTab

    QApplication.instance() or QApplication([])
    service.load_komise_seed()
    cur = service.current_academic_year()
    near = datetime.now() + timedelta(minutes=20)
    dstr = f"{near.day}. {near.month}. {near.year}"
    for oc, fn, ln in [("A10001", "Anna", "Aktualni"),
                       ("A10002", "Bedrich", "Hotovy")]:
        st = Student(first_name=fn, last_name=ln, university_id=oc)
        service.upsert_student(st)
        service.upsert_thesis(Thesis(type=ThesisType.BP, academic_year=cur,
                                     student_id=st.id,
                                     status=ThesisStatus.IN_PROGRESS))
    service.apply_komise_import([], [
        ParsedSchedule(color="červená", academic_year=cur, level="Bc", obor="SWI",
                       program_label="SWI", dates=[dstr],
                       slots=[(dstr, near.strftime("%H:%M"), "A10001", "Anna Aktualni"),
                              (dstr, near.strftime("%H:%M"), "A10002", "Bedrich Hotovy")]),
    ], ["r.pdf"])
    tab = KomiseTab(service)
    tab._right_year = cur
    tab._render_harmonogram()
    # bez stavů: oba nadcházející, žádná sekce Historie
    harm0 = tab.harmonogram_view.toPlainText()
    assert "Anna Aktualni" in harm0 and "Bedrich Hotovy" in harm0
    assert "📜 Historie" not in harm0
    # Bedrich obhájil → spadne dolů do Historie, Anna zůstane nahoře
    tab._committee_states = {"A10002": "defended"}
    tab._render_harmonogram()
    harm = tab.harmonogram_view.toPlainText()
    up, sep, hist = harm.partition("📜 Historie")
    assert sep                                       # sekce Historie existuje
    assert "Anna Aktualni" in up and "Anna Aktualni" not in hist
    assert "Bedrich Hotovy" in hist and "Bedrich Hotovy" not in up
    assert "Obhájeno" in hist                        # badge stavu v historii


def test_schedule_section_html_reverse_and_empty_note() -> None:
    """Sekce harmonogramu: reverse řadí od nejnovějšího (Historie), empty_note
    nahradí výchozí výzvu „nahraj rozpisy" vlastním textem."""
    from PySide6.QtWidgets import QApplication

    from bpdpmanager.ui.komise_tab import _schedule_section_html

    QApplication.instance() or QApplication([])

    def _e(date, oc, name):
        return {"date": date, "time": "09:00", "personal_number": oc,
                "student_name": name, "role": "led", "color": "červená",
                "obor": "SWI", "academic_year": "2025/2026"}

    entries = [_e("10. 6. 2026", "A1", "Drive"), _e("17. 6. 2026", "A2", "Pozdeji")]
    # reverse=True → nejnovější datum (17.) nahoře
    h = _schedule_section_html(entries, "Historie", reverse=True)
    assert h.index("17. 6. 2026") < h.index("10. 6. 2026")
    # výchozí (reverse=False) → nejstarší nahoře
    h2 = _schedule_section_html(entries, "Plán")
    assert h2.index("10. 6. 2026") < h2.index("17. 6. 2026")
    # prázdný vstup + empty_note → vlastní text místo „nahraj rozpisy"
    h3 = _schedule_section_html([], "Plán", empty_note="Vše odbaveno")
    assert "Vše odbaveno" in h3 and "nahraj" not in h3.lower()


def test_committee_detail_shows_source_pdf(service, tmp_path) -> None:
    """Detail komise ukáže zdrojový rozpis PDF (jen existující, s názvem)."""
    from PySide6.QtWidgets import QApplication

    from bpdpmanager.config import komise_dir
    from bpdpmanager.ui.komise_tab import ROLE_COMMITTEE_ID, KomiseTab

    QApplication.instance() or QApplication([])
    service.load_komise_seed()
    src = tmp_path / "s.pdf"
    src.write_bytes(b"%PDF")
    rel = service.komise_store_pdf(src, "2025/2026",
                                   name="rozpis-studentu_Bc_SWI_2025-2026.pdf",
                                   kind="rozpisy")
    assert (komise_dir() / rel).exists()
    service.apply_komise_import([], [
        ParsedSchedule(color="červená", academic_year="2025/2026", level="Bc",
                       obor="SWI", program_label="SWI", dates=["15. 6. 2026"],
                       slots=[("15. 6. 2026", "09:00", "A1", "X Y")]),
    ], [rel])
    tab = KomiseTab(service)
    target = next(c for c in service.list_committees()
                  if c.color == "červená" and c.level == "Bc")
    leaf = next(lf for lf in tab._iter_leaves()
                if lf.data(0, ROLE_COMMITTEE_ID) == target.id)
    tab.tree.setCurrentItem(leaf)
    txt = tab.detail.toPlainText()
    assert "Zdrojová PDF" in txt
    assert "rozpis-studentu_Bc_SWI_2025-2026.pdf" in txt
    # Komise dostane i dodané složení dle stupně+oboru, ale ne cizí rozpis.
    src_names = [p.name for p in tab._committee_source_pdfs(target)]
    assert "slozeni-komisi_Bc_SWI.pdf" in src_names
    assert "rozpis-studentu_Bc_SWI_2025-2026.pdf" in src_names


def test_committee_period_and_state_badge(service) -> None:
    """Období státnic (rozmezí termínů) + badge stavu obhajoby v rozpisu."""
    from datetime import date

    from PySide6.QtWidgets import QApplication

    from bpdpmanager.ui.komise_tab import (
        ROLE_COMMITTEE_ID,
        KomiseTab,
        _defense_state_badge,
    )

    QApplication.instance() or QApplication([])
    service.load_komise_seed()
    # Období: napříč seed komisemi je 15.-19. 6. 2026.
    assert service.committee_date_range() == (date(2026, 6, 15), date(2026, 6, 19))
    assert service.in_committee_period(date(2026, 6, 17)) is True
    assert service.in_committee_period(date(2026, 1, 1)) is False
    # Badge: match přes osobní číslo i jméno.
    assert "Obhájeno" in _defense_state_badge({"A1": "defended"}, "A1", "X")
    assert "Neobhájeno" in _defense_state_badge({"jan novak": "failed"}, "", "Jan Novák")
    assert _defense_state_badge({}, "A1", "X") == ""
    # Vizualizace v detailu komise.
    service.apply_komise_import([], [
        ParsedSchedule(color="červená", academic_year="2025/2026", level="Bc",
                       obor="SWI", program_label="SWI", dates=["15. 6. 2026"],
                       slots=[("15. 6. 2026", "09:00", "A55501", "Test Student")]),
    ], ["x.pdf"])
    tab = KomiseTab(service)
    tab._stag_states = {"A55501": "defended"}
    target = next(c for c in service.list_committees()
                  if c.color == "červená" and c.level == "Bc")
    leaf = next(lf for lf in tab._iter_leaves()
                if lf.data(0, ROLE_COMMITTEE_ID) == target.id)
    tab.tree.setCurrentItem(leaf)
    assert "Obhájeno" in tab.detail.toPlainText()


def test_fetch_defense_states_maps_codes(service, monkeypatch) -> None:
    """fetch_defense_states mapuje STAG kód na stav, klíč = os. číslo i jméno."""
    import bpdpmanager.ui.stag_check as chk
    from bpdpmanager.models import Student, Thesis
    from bpdpmanager.models.enums import ThesisStatus, ThesisType

    s = Student(first_name="Jan", last_name="Novák", university_id="A22222")
    service.upsert_student(s)
    service.upsert_thesis(Thesis(type=ThesisType.BP, status=ThesisStatus.IN_PROGRESS,
                                 academic_year="2025/2026", student_id=s.id,
                                 adipidno="111"))
    monkeypatch.setattr(chk, "_fetch_target_state", lambda a: ("DUO", [], ""))
    states = chk.fetch_defense_states(service)
    assert states.get("A22222") == ThesisStatus.DEFENDED.value
    assert states.get("jan novak") == ThesisStatus.DEFENDED.value


def test_upcoming_defense_reminders(service) -> None:
    """Připomínka: sloty mých studentů začínající do 10 min od ``now``."""
    from datetime import datetime

    from bpdpmanager.models import Student, Thesis
    from bpdpmanager.models.enums import ThesisStatus, ThesisType

    service.load_komise_seed()
    s = Student(first_name="Anna", last_name="Vedena", university_id="A10001")
    service.upsert_student(s)
    service.upsert_thesis(Thesis(type=ThesisType.BP, academic_year="2025/2026",
                                 student_id=s.id, status=ThesisStatus.IN_PROGRESS))
    service.apply_komise_import([], [
        ParsedSchedule(color="červená", academic_year="2025/2026", level="Bc",
                       obor="SWI", program_label="SWI", dates=["15. 6. 2026"],
                       slots=[("15. 6. 2026", "09:00", "A10001", "Anna Vedena"),
                              ("15. 6. 2026", "14:00", "A10001", "Anna Vedena")]),
    ], ["x.pdf"])
    # 8 minut před 09:00 → připomínka jen na 09:00.
    rem = service.upcoming_defense_reminders(datetime(2026, 6, 15, 8, 52))
    assert len(rem) == 1
    assert rem[0]["time"] == "09:00" and rem[0]["minutes"] == 8
    assert rem[0]["role"] == "led" and rem[0]["key"]
    # Po začátku (09:05) už nic do 10 min dopředu.
    assert service.upcoming_defense_reminders(datetime(2026, 6, 15, 9, 5)) == []
    # Příliš brzy (08:40, 20 min předem) → ještě nic.
    assert service.upcoming_defense_reminders(datetime(2026, 6, 15, 8, 40)) == []


def test_pdf_descriptive_name() -> None:
    """Název PDF: prefix_<stupně>_<obory>_<rok>.pdf z naparsovaných položek."""
    from bpdpmanager.ui.komise_tab import KomiseTab

    items = [
        ParsedSchedule(color="červená", level="Bc", obor="SWI",
                       academic_year="2025/2026"),
    ]
    assert (KomiseTab._pdf_name("2025/2026", items, "rozpis-studentu")
            == "rozpis-studentu_Bc_SWI_2025-2026.pdf")
    multi = [
        ParsedSchedule(color="červená", level="Mgr", obor="NSWI"),
        ParsedSchedule(color="fialová", level="Mgr", obor="NKYB"),
    ]
    assert (KomiseTab._pdf_name("2025/2026", multi, "rozpis-studentu")
            == "rozpis-studentu_Mgr_NKYB-NSWI_2025-2026.pdf")


def test_store_pdf_renames_into_subfolder(service, tmp_path) -> None:
    """komise_store_pdf přejmenuje a uloží do komise/<rok>/<kind>/."""
    from bpdpmanager import config
    config.set_active_data_dir(tmp_path)  # izoluj komise_dir() do tmp
    src = tmp_path / "puvodni nazev!.pdf"
    src.write_bytes(b"%PDF-1.4 test")
    rel = service.komise_store_pdf(src, "2025/2026", name="rozpis_Bc_SWI_2025-2026.pdf",
                                   kind="rozpisy")
    assert rel == "2025-2026/rozpisy/rozpis_Bc_SWI_2025-2026.pdf"
    assert service.komise_pdf_path(rel).exists()
    # Bezpečné jméno z divného názvu (bez name).
    rel2 = service.komise_store_pdf(src, "2025/2026", kind="slozeni")
    assert rel2.startswith("2025-2026/slozeni/") and rel2.endswith(".pdf")


def test_pdf_inventory_includes_shipped_and_local(service, tmp_path) -> None:
    """Inventář PDF: 3 dodaná složení z gitu + lokálně uložené rozpisy."""
    from bpdpmanager.config import komise_dir

    src = tmp_path / "r.pdf"
    src.write_bytes(b"%PDF-1.4")
    service.komise_store_pdf(src, "2025/2026",
                             name="rozpis-studentu_Bc_SWI_2025-2026.pdf", kind="rozpisy")
    inv = service.komise_pdf_inventory()
    assert "2025/2026" in inv
    slozeni = {p.name for p in inv["2025/2026"]["slozeni"]}
    assert "slozeni-komisi_Bc_SWI.pdf" in slozeni          # dodané v gitu
    assert len(inv["2025/2026"]["slozeni"]) == 3
    assert any(p.name == "rozpis-studentu_Bc_SWI_2025-2026.pdf"
               for p in inv["2025/2026"]["rozpisy"])
    # Starší PDF přímo v komise/<rok>/ → skupina „nezařazené" (ne rozpisy).
    (komise_dir() / "2025-2026" / "stary_nazev.pdf").write_bytes(b"%PDF")
    inv2 = service.komise_pdf_inventory()
    assert any(p.name == "stary_nazev.pdf"
               for p in inv2["2025/2026"]["nezarazene"])


def test_delete_pdf_protects_shipped(service, tmp_path) -> None:
    """komise_delete_pdf smaže lokální PDF; dodaná v gitu nesmí (vrátí False)."""
    from bpdpmanager.config import komise_dir

    local = komise_dir() / "2025-2026" / "rozpisy" / "r.pdf"
    local.parent.mkdir(parents=True)
    local.write_bytes(b"%PDF")
    assert service.komise_delete_pdf(str(local)) is True
    assert not local.exists()
    shipped = service._komise_seed_pdf_dir() / "2025-2026" / "slozeni-komisi_Bc_SWI.pdf"
    assert service.komise_delete_pdf(str(shipped)) is False
    assert shipped.exists()


def test_pdf_panel_lists_and_opens(service, tmp_path, monkeypatch) -> None:
    """Panel PDF vypíše soubory a kontextové „Otevřít" je otevře (více najednou)."""
    from PySide6.QtWidgets import QApplication

    from bpdpmanager import config
    from bpdpmanager.ui.komise_tab import ROLE_PDF_PATH, KomiseTab

    QApplication.instance() or QApplication([])
    config.set_active_data_dir(tmp_path)
    tab = KomiseTab(service)
    leaves = []

    def walk(it):
        if it.data(0, ROLE_PDF_PATH):
            leaves.append(it)
        for i in range(it.childCount()):
            walk(it.child(i))

    for i in range(tab.pdf_tree.topLevelItemCount()):
        walk(tab.pdf_tree.topLevelItem(i))
    assert len(leaves) >= 3          # aspoň 3 dodaná složení
    for lf in leaves[:2]:
        lf.setSelected(True)
    opened = []
    monkeypatch.setattr("bpdpmanager.ui.komise_tab.Path.exists", lambda self: True)
    import bpdpmanager.ui._os_actions as osa
    monkeypatch.setattr(osa, "open_path", lambda p: opened.append(str(p)))
    tab._open_selected_pdfs()
    assert len(opened) == 2          # otevřely se oba vybrané


def test_komise_student_roles(service) -> None:
    from bpdpmanager.models import OpposingThesis, Student, Thesis
    from bpdpmanager.models.enums import ThesisStatus, ThesisType

    s = Student(first_name="Marko", last_name="Vzorek", university_id="A23625")
    service.upsert_student(s)
    service.upsert_thesis(Thesis(type=ThesisType.BP, academic_year="2025/2026",
                                 student_id=s.id, status=ThesisStatus.IN_PROGRESS))
    service.upsert_opposing_thesis(OpposingThesis(
        type=ThesisType.BP, academic_year="2025/2026",
        student_first_name="Lilyan", student_last_name="Třetí"))
    roles = service.komise_student_roles()
    assert roles["A23625"] == "led"
    assert roles["marko vzorek"] == "led"
    assert roles["lilyan treti"] == "opp"      # foldované jméno


def test_komise_tab_smoke(service, tmp_path) -> None:
    from PySide6.QtWidgets import QApplication

    QApplication.instance() or QApplication([])

    from bpdpmanager.ui.komise_tab import KomiseTab

    pc = ParsedCommittee(color="žlutá", academic_year="2025/2026", level="Bc",
                         members=[("Předseda", "prof. Jan Vzor")])
    service.apply_komise_import([pc], [], [])
    tab = KomiseTab(service)
    assert tab.tree.topLevelItemCount() == 1          # 1 rok
    year_item = tab.tree.topLevelItem(0)
    assert year_item.childCount() == 1                # skupina Bc
    level_item = year_item.child(0)
    assert "Bakalářské" in level_item.text(0)
    leaves = list(tab._iter_leaves())
    assert len(leaves) == 1
    assert "žlutá" in leaves[0].text(0)               # komise = barva
    assert "Komise žlutá" in tab.detail.toPlainText()
    # Role ve složení jsou zaoblené rámečky (PNG badge, stejná šířka).
    html = tab._committee_html(service.list_committees()[0])
    assert "data:image/png;base64" in html
    assert "předseda" in tab._role_badge_cache  # badge se vygeneroval


def test_deleted_seed_committee_not_reseeded(service) -> None:
    """Smazaná seed komise se po restartu (dalším seedu) NEvrátí; reset ji vrátí."""
    service.load_komise_seed()
    coms = service.list_committees()
    assert coms
    n0 = len(coms)
    target = coms[0]
    service.delete_committee(target.id)
    assert len(service.list_committees()) == n0 - 1
    service.load_komise_seed()                         # simulace restartu
    assert len(service.list_committees()) == n0 - 1    # nevrátila se
    service.reset_committees_from_seed()               # čistý reset
    assert len(service.list_committees()) == n0        # zpět vše


def test_committee_count_excludes_done_students(service) -> None:
    """Počet V/O u komise nepočítá studenty, co už mají hotovo (Obhájeno/Neobhájeno)."""
    from PySide6.QtWidgets import QApplication

    from bpdpmanager.models import Student, Thesis
    from bpdpmanager.models.enums import ThesisStatus, ThesisType
    from bpdpmanager.ui.komise_tab import ROLE_VO, KomiseTab

    QApplication.instance() or QApplication([])
    service.load_komise_seed()
    s = Student(first_name="Marko", last_name="Test", university_id="A55501")
    service.upsert_student(s)
    service.upsert_thesis(Thesis(type=ThesisType.BP, academic_year="2025/2026",
                                 student_id=s.id, status=ThesisStatus.IN_PROGRESS))
    service.apply_komise_import(
        [],
        [ParsedSchedule(color="červená", academic_year="2025/2026", level="Bc",
                        obor="SWI", program_label="SWI", dates=["15. 6. 2026"],
                        slots=[("15. 6. 2026", "09:00", "A55501", "Marko Test")])],
        ["rozpis.pdf"])
    tab = KomiseTab(service)

    def _cervena_vo():
        leaf = next(lf for lf in tab._iter_leaves()
                    if "červená" in lf.text(0)
                    and "📚 Bakalářské" in lf.parent().text(0))
        return leaf.data(1, ROLE_VO)

    assert _cervena_vo() == (1, 0)                  # nehotový → počítá se
    tab._committee_states = {"A55501": "defended"}  # student obhájil
    tab.refresh()
    assert _cervena_vo() == (0, 0)                  # hotový → z počtu zmizí


def test_committee_html_role_name_color(service) -> None:
    """Rozpis v detailu komise: vedený student má jméno zeleně (klikací), cizí
    modře, a čepička 🎓 už se nepoužívá (na tmavém splývala)."""
    from PySide6.QtWidgets import QApplication

    from bpdpmanager.models import Student, Thesis
    from bpdpmanager.models.enums import ThesisStatus, ThesisType
    from bpdpmanager.ui.komise_tab import _C_LED, _SZZ_LINK, KomiseTab

    QApplication.instance() or QApplication([])
    service.load_komise_seed()
    s = Student(first_name="Marko", last_name="Test", university_id="A55501")
    service.upsert_student(s)
    service.upsert_thesis(Thesis(type=ThesisType.BP, academic_year="2025/2026",
                                 student_id=s.id, status=ThesisStatus.IN_PROGRESS))
    service.apply_komise_import(
        [],
        [ParsedSchedule(color="červená", academic_year="2025/2026", level="Bc",
                        obor="SWI", program_label="SWI", dates=["15. 6. 2026"],
                        slots=[("15. 6. 2026", "09:00", "A55501", "Marko Test"),
                               ("15. 6. 2026", "10:00", "A99999", "Cizi Host")])],
        ["rozpis.pdf"])
    tab = KomiseTab(service)
    cervena = next(c for c in service.list_committees()
                   if c.color == "červená" and c.level == "Bc")
    html = tab._committee_html(cervena)
    # vedený student: jméno zeleně, stále klikací odkaz na souhrn SZZ
    assert f"color:{_C_LED}" in html and 'href="szz:A55501' in html
    # cizí student: jméno modře (výchozí odkazová barva)
    assert f"color:{_SZZ_LINK}" in html and 'href="szz:A99999' in html
    # čepička/monokl se z rozpisu vypustily (nahradila je barva jména)
    assert "🎓" not in html and "🧐" not in html
