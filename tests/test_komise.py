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
    assert tab.tree.topLevelItemCount() == 1
    year_item = tab.tree.topLevelItem(0)
    assert year_item.childCount() == 1
    assert "žlutá" in year_item.child(0).text(0)
    assert "Komise žlutá" in tab.detail.toPlainText()
