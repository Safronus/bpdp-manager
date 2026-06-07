"""Stav „Neobhájeno" (FAILED) — odlišení od „Nedokončeno", STAG mapování, přechody."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from bpdpmanager.models import Student, Thesis
from bpdpmanager.models.enums import (
    STATUS_LABELS,
    STATUSES_HISTORY,
    ThesisStatus,
    ThesisType,
)
from bpdpmanager.services import ThesisService
from bpdpmanager.services.thesis_service import TransitionError
from bpdpmanager.storage import JsonRepository


@pytest.fixture
def service(tmp_path: Path) -> ThesisService:
    repo = JsonRepository(path=tmp_path / "db.json", backup_path=tmp_path / "db.json.bak")
    return ThesisService(repo)


def test_failed_is_distinct_history_status() -> None:
    assert STATUS_LABELS[ThesisStatus.FAILED] == "Neobhájeno"
    assert STATUS_LABELS[ThesisStatus.CANCELLED] == "Nedokončeno"
    assert ThesisStatus.FAILED in STATUSES_HISTORY
    assert ThesisStatus.FAILED.color  # má vlastní barvu


def test_stag_maps_failed_defense_to_failed() -> None:
    from bpdpmanager.ui.stag_import_dialog import STAG_STATE_TO_STATUS

    assert STAG_STATE_TO_STATUS["DBUO"] == ThesisStatus.FAILED
    assert STAG_STATE_TO_STATUS["OPUNO"] == ThesisStatus.FAILED
    assert STAG_STATE_TO_STATUS["ND"] == ThesisStatus.CANCELLED  # nedokončeno zůstává


def _in_progress(service) -> Thesis:
    s = Student(first_name="Jan", last_name="Novák")
    service.upsert_student(s)
    t = Thesis(type=ThesisType.BP, status=ThesisStatus.IN_PROGRESS,
               academic_year="2024/2025", student_id=s.id)
    service.upsert_thesis(t)
    return t


def test_transition_in_progress_to_failed(service) -> None:
    t = _in_progress(service)
    service.transition(t.id, ThesisStatus.FAILED)
    assert service.get_thesis(t.id).status == ThesisStatus.FAILED


def test_reclassify_cancelled_to_failed_and_back(service) -> None:
    """Existující „Nedokončeno" jde ručně přeřadit na „Neobhájeno" (a zpět)."""
    t = _in_progress(service)
    service.transition(t.id, ThesisStatus.CANCELLED)
    service.transition(t.id, ThesisStatus.FAILED)
    assert service.get_thesis(t.id).status == ThesisStatus.FAILED
    service.transition(t.id, ThesisStatus.CANCELLED)
    assert service.get_thesis(t.id).status == ThesisStatus.CANCELLED


def test_failed_can_reopen_for_second_attempt(service) -> None:
    t = _in_progress(service)
    service.transition(t.id, ThesisStatus.FAILED)
    service.transition(t.id, ThesisStatus.IN_PROGRESS)  # druhý pokus
    assert service.get_thesis(t.id).status == ThesisStatus.IN_PROGRESS


def test_defended_cannot_go_to_failed(service) -> None:
    t = _in_progress(service)
    service.transition(t.id, ThesisStatus.DEFENDED)
    with pytest.raises(TransitionError):
        service.transition(t.id, ThesisStatus.FAILED)
