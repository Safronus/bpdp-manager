"""Export harmonogramu obhajob do kalendáře (.ics).

Pokrývá `ThesisService.calendar_events` (filtr roku/role/nadcházející, délka dle
stupně Bc 45 / Mgr 60 min) a `ics_export.build_ics` (struktura VEVENT/VALARM).
"""

from __future__ import annotations

import os
from datetime import datetime

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from bpdpmanager.models import OpposingThesis, Student, Thesis
from bpdpmanager.models.enums import ThesisStatus, ThesisType
from bpdpmanager.services import ThesisService
from bpdpmanager.services.ics_export import build_ics
from bpdpmanager.services.komise_parser import ParsedSchedule
from bpdpmanager.storage import JsonRepository


@pytest.fixture
def service(tmp_path) -> ThesisService:
    repo = JsonRepository(path=tmp_path / "db.json", backup_path=tmp_path / "db.json.bak")
    return ThesisService(repo)


def _seed_schedule(service: ThesisService) -> None:
    """Vedený (Mgr, 17.6 11:00) + oponovaný (Bc, 15.6 09:00) ve 2025/2026."""
    service.load_komise_seed()
    s = Student(first_name="Anna", last_name="Vedena", university_id="A10001")
    service.upsert_student(s)
    service.upsert_thesis(Thesis(type=ThesisType.DP, academic_year="2025/2026",
                                 student_id=s.id, status=ThesisStatus.IN_PROGRESS))
    service.upsert_opposing_thesis(OpposingThesis(
        type=ThesisType.BP, academic_year="2025/2026",
        student_first_name="Karel", student_last_name="Oponovan"))
    service.apply_komise_import([], [
        ParsedSchedule(color="modrá", academic_year="2025/2026", level="Mgr",
                       obor="NSWI", program_label="SWI", dates=["17. 6. 2026"],
                       slots=[("17. 6. 2026", "11:00", "A10001", "Anna Vedena")]),
        ParsedSchedule(color="červená", academic_year="2025/2026", level="Bc",
                       obor="NSWI", program_label="SWI", dates=["15. 6. 2026"],
                       slots=[("15. 6. 2026", "09:00", "A99", "Karel Oponovan")]),
    ], ["x.pdf"])


def test_calendar_events_durations_and_order(service) -> None:
    _seed_schedule(service)
    now = datetime(2026, 1, 1, 0, 0)
    evs = service.calendar_events("2025/2026", now=now)
    assert len(evs) == 2
    # Chronologicky: oponovaný 15.6 (Bc, 45 min) před vedeným 17.6 (Mgr, 60 min).
    assert evs[0]["start"] == datetime(2026, 6, 15, 9, 0)
    assert (evs[0]["end"] - evs[0]["start"]).total_seconds() == 45 * 60
    assert evs[1]["start"] == datetime(2026, 6, 17, 11, 0)
    assert (evs[1]["end"] - evs[1]["start"]).total_seconds() == 60 * 60
    assert "Oponovan" in evs[0]["summary"] and evs[0]["role"] == "opp"
    assert "Vedena" in evs[1]["summary"] and evs[1]["role"] == "led"


def test_calendar_events_role_filter(service) -> None:
    _seed_schedule(service)
    now = datetime(2026, 1, 1)
    only_led = service.calendar_events("2025/2026", include_opp=False, now=now)
    assert [e["role"] for e in only_led] == ["led"]
    only_opp = service.calendar_events("2025/2026", include_led=False, now=now)
    assert [e["role"] for e in only_opp] == ["opp"]


def test_calendar_events_only_upcoming(service) -> None:
    _seed_schedule(service)
    # „Teď" mezi oběma obhajobami → zbude jen ta pozdější (17.6).
    now = datetime(2026, 6, 16, 0, 0)
    evs = service.calendar_events("2025/2026", now=now)
    assert len(evs) == 1 and evs[0]["start"] == datetime(2026, 6, 17, 11, 0)


def test_calendar_events_year_filter(service) -> None:
    _seed_schedule(service)
    now = datetime(2026, 1, 1)
    assert service.calendar_events("2024/2025", now=now) == []


def test_build_ics_structure_and_alarm() -> None:
    events = [{
        "uid": "abc@bpdpmanager",
        "start": datetime(2026, 6, 17, 11, 0),
        "end": datetime(2026, 6, 17, 12, 0),
        "summary": "🎓 Obhajoba: Anna Vedena",
        "location": "Komise modrá (NSWI)",
        "description": "Role: vedoucí\nKomise: A; B",
        "reminder_min": 15,
    }]
    ics = build_ics(events, dtstamp=datetime(2026, 1, 1, 8, 0))
    assert ics.startswith("BEGIN:VCALENDAR")
    assert ics.rstrip().endswith("END:VCALENDAR")
    assert "BEGIN:VEVENT" in ics and "END:VEVENT" in ics
    assert "DTSTART:20260617T110000" in ics
    assert "DTEND:20260617T120000" in ics
    assert "UID:abc@bpdpmanager" in ics
    assert "BEGIN:VALARM" in ics and "TRIGGER:-PT15M" in ics
    # Escapování: středník i newline v TEXT hodnotě.
    assert "Komise: A\\; B" in ics
    # CRLF zakončení řádků.
    assert "\r\n" in ics


def test_build_ics_no_reminder_omits_valarm() -> None:
    events = [{
        "uid": "x@bpdpmanager",
        "start": datetime(2026, 6, 17, 11, 0),
        "end": datetime(2026, 6, 17, 11, 45),
        "summary": "Obhajoba",
        "reminder_min": None,
    }]
    ics = build_ics(events, dtstamp=datetime(2026, 1, 1))
    assert "VALARM" not in ics


def test_add_to_calendar_dialog_options_and_count(service) -> None:
    from PySide6.QtWidgets import QApplication

    from bpdpmanager.ui.komise_tab import AddToCalendarDialog

    _seed_schedule(service)
    _ = QApplication.instance() or QApplication([])
    now = datetime(2026, 1, 1)
    dlg = AddToCalendarDialog(service, "2025/2026", now)
    # Default: obojí zaškrtnuto, připomínka 15 min, Apple, 2 obhajoby.
    opts = dlg.options()
    assert opts == {"led": True, "opp": True, "reminder": 15, "provider": "apple"}
    assert "2 obhajob" in dlg.lbl_count.text()
    # Odškrtnutí oponovaných → počet 1.
    dlg.cb_opp.setChecked(False)
    assert "1 obhajob" in dlg.lbl_count.text()
    assert dlg.options()["opp"] is False
