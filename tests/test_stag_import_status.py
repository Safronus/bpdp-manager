"""Import ze STAG: schválené budoucí téma se převede do „V řešení".

Dřív import stav existující práce nikdy neměnil (a náhled ho přitom ukazoval),
takže ručně založený zájemce / vypsané téma zůstal po schválení v Budoucích.
"""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from bpdpmanager.models import Student, Thesis
from bpdpmanager.models.enums import ThesisStatus, ThesisType
from bpdpmanager.services import ThesisService
from bpdpmanager.services.stag_csv_importer import ImportFile, ImportRole, ParsedRecord
from bpdpmanager.services.stag_status_rules import preselected_status_for_existing
from bpdpmanager.storage import JsonRepository
from bpdpmanager.ui.stag_import_dialog import StagImportDialog

S = ThesisStatus


@pytest.fixture(scope="module")
def qapp():
    yield QApplication.instance() or QApplication([])


@pytest.fixture
def service(tmp_path: Path) -> ThesisService:
    repo = JsonRepository(path=tmp_path / "db.json", backup_path=tmp_path / "db.json.bak")
    return ThesisService(repo)


@pytest.mark.parametrize(("current", "stag", "expected"), [
    (S.LISTED, S.IN_PROGRESS, S.IN_PROGRESS),        # schválené téma → V řešení
    (S.RESERVED, S.IN_PROGRESS, S.IN_PROGRESS),
    (S.INTERESTED, S.DEFENDED, S.DEFENDED),          # STAG už dál → převezmi
    (S.LISTED, None, S.LISTED),                      # STAG nic nedokládá → beze změny
    (S.IN_PROGRESS, S.DEFENDED, S.IN_PROGRESS),      # V řešení: chování se nemění
    (S.DEFENDED, S.IN_PROGRESS, S.DEFENDED),         # ukončené: beze změny
])
def test_preselected_status_rule(current, stag, expected) -> None:
    assert preselected_status_for_existing(current, stag) == expected


def _existing(service: ThesisService, status: ThesisStatus, adipidno: str = "") -> Thesis:
    st = Student(first_name="Jan", last_name="Novák", university_id="A24002")
    service.upsert_student(st)
    t = Thesis(type=ThesisType.DP, academic_year="2026/2027", status=status,
               student_id=st.id, adipidno=adipidno, title_cs="Fiktivní téma")
    service.upsert_thesis(t)
    return t


def _record(**kw) -> ParsedRecord:
    r = ParsedRecord(role=ImportRole.SUPERVISOR, student_uni_id="A24002",
                     student_first="Jan", student_last="Novák", type_code="DP",
                     academic_year="2026/2027", title_cs="Fiktivní téma",
                     title_en="Fictional topic", objectives_text="1. bod",
                     references_text="Zdroj")
    for k, v in kw.items():
        setattr(r, k, v)
    return r


def _preview(qapp, service, record) -> dict:
    dlg = StagImportDialog(service)
    dlg.import_file = ImportFile(path=Path("x.csv"), encoding="utf-8", records=[record])
    dlg._populate_preview()
    return dlg.row_widgets[0]


def test_preview_preselects_stag_status_for_approved_future(qapp, service) -> None:
    _existing(service, S.LISTED)
    w = _preview(qapp, service, _record(stag_state_code="R"))
    assert w["cb_status"].currentData() == S.IN_PROGRESS.value
    assert "Vypsané téma" in w["cb_status"].toolTip()
    assert "#e0a000" in w["cb_status"].styleSheet()          # změna zvýrazněná
    assert "Aktualizovat" in w["cb_action"].currentText()


def test_preview_date_evidence_also_counts(qapp, service) -> None:
    _existing(service, S.RESERVED)
    w = _preview(qapp, service, _record(date_assigned=date(2026, 10, 1)))
    assert w["cb_status"].currentData() == S.IN_PROGRESS.value


@pytest.mark.parametrize(("status", "record_kw"), [
    (S.LISTED, {}),                                   # STAG nic nedokládá
    (S.IN_PROGRESS, {"stag_state_code": "DUO"}),      # V řešení → beze změny
])
def test_preview_keeps_existing_status(qapp, service, status, record_kw) -> None:
    _existing(service, status)
    w = _preview(qapp, service, _record(**record_kw))
    assert w["cb_status"].currentData() == status.value
    assert "nezmění" in w["cb_status"].toolTip()
    assert "#e0a000" not in w["cb_status"].styleSheet()


def test_preview_does_not_pair_thesis_with_other_stag_id(qapp, service) -> None:
    # Stejně jako samotný import: práce s JINÝM STAG ID je jiná práce (repetent).
    _existing(service, S.LISTED, adipidno="111")
    w = _preview(qapp, service, _record(adipidno="222", stag_state_code="R"))
    assert "Vytvořit" in w["cb_action"].currentText()


def _stats() -> dict:
    return {
        "created_thesis": 0, "updated_thesis": 0,
        "created_opposing": 0, "updated_opposing": 0,
        "created_student": 0, "created_opponent": 0,
        "created_supervisor": 0, "skipped": 0,
        "attached_csv": 0, "queued_files": 0,
    }


def test_apply_changes_status_and_fills_assignment(qapp, service) -> None:
    t = _existing(service, S.LISTED)
    dlg = StagImportDialog(service)
    stats = _stats()
    tid, is_new = dlg._apply_supervisor_role(
        _record(stag_state_code="R", adipidno="555"), "", S.IN_PROGRESS, stats)
    saved = service.get_thesis(t.id)
    assert (tid, is_new) == (t.id, False)
    assert saved.status == S.IN_PROGRESS and saved.adipidno == "555"
    assert saved.title_en == "Fictional topic"             # zadání doplněno
    assert stats["updated_thesis"] == 1 and stats["status_changed"] == 1


def test_apply_same_status_is_not_counted(qapp, service) -> None:
    t = _existing(service, S.IN_PROGRESS)
    dlg = StagImportDialog(service)
    stats = _stats()
    dlg._apply_supervisor_role(_record(stag_state_code="DUO"), "", S.IN_PROGRESS, stats)
    assert service.get_thesis(t.id).status == S.IN_PROGRESS
    assert "status_changed" not in stats


def test_apply_manual_choice_in_preview_is_honoured(qapp, service) -> None:
    # „Rozhodně umožnit i ruční nastavení": zvolený stav v náhledu platí.
    t = _existing(service, S.IN_PROGRESS)
    dlg = StagImportDialog(service)
    stats = _stats()
    dlg._apply_supervisor_role(_record(stag_state_code="DUO"), "", S.DEFENDED, stats)
    assert service.get_thesis(t.id).status == S.DEFENDED
    assert stats["status_changed"] == 1
