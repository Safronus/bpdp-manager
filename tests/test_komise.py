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
    tab = KomiseTab(service)
    assert sum(1 for _ in tab._iter_leaves()) == 11


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
