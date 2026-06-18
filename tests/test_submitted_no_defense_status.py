"""Stav „Odevzdáno bez obhajoby" (SUBMITTED_NO_DEFENSE) — STAG OPUBPOO,
odlišení od „V řešení", mapování a přechody."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from bpdpmanager.models import Student, Thesis
from bpdpmanager.models.enums import (
    STATUS_LABELS,
    STATUSES_CURRENT,
    STATUSES_HISTORY,
    ThesisStatus,
    ThesisType,
)
from bpdpmanager.services import ThesisService
from bpdpmanager.services.thesis_service import TransitionError
from bpdpmanager.storage import JsonRepository


@pytest.fixture
def service(tmp_path: Path) -> ThesisService:
    repo = JsonRepository(path=tmp_path / "db.json",
                         backup_path=tmp_path / "db.json.bak")
    return ThesisService(repo)


def test_distinct_terminal_history_status() -> None:
    st = ThesisStatus.SUBMITTED_NO_DEFENSE
    assert STATUS_LABELS[st] == "Odevzdáno bez obhajoby"
    assert st in STATUSES_HISTORY          # terminální → Historie
    assert st not in STATUSES_CURRENT      # NE „V řešení"
    assert st.color == "#8d6e63"           # hnědá


def test_stag_maps_opubpoo() -> None:
    from bpdpmanager.ui.stag_import_dialog import (
        STAG_STATE_LABELS,
        STAG_STATE_TO_STATUS,
    )

    assert STAG_STATE_TO_STATUS["OPUBPOO"] == ThesisStatus.SUBMITTED_NO_DEFENSE
    # DBPOO (čeká na obhajobu) zůstává „V řešení" — jen OPUBPOO je terminální.
    assert STAG_STATE_TO_STATUS["DBPOO"] == ThesisStatus.IN_PROGRESS
    assert "obhajobu" in STAG_STATE_LABELS["OPUBPOO"]


def _in_progress(service) -> Thesis:
    s = Student(first_name="Jan", last_name="Novák")
    service.upsert_student(s)
    t = Thesis(type=ThesisType.BP, status=ThesisStatus.IN_PROGRESS,
               academic_year="2024/2025", student_id=s.id)
    service.upsert_thesis(t)
    return t


def test_transition_in_progress_to_submitted_no_defense(service) -> None:
    t = _in_progress(service)
    service.transition(t.id, ThesisStatus.SUBMITTED_NO_DEFENSE)
    assert service.get_thesis(t.id).status == ThesisStatus.SUBMITTED_NO_DEFENSE


def test_can_reopen_for_second_attempt(service) -> None:
    t = _in_progress(service)
    service.transition(t.id, ThesisStatus.SUBMITTED_NO_DEFENSE)
    service.transition(t.id, ThesisStatus.IN_PROGRESS)   # re-open
    assert service.get_thesis(t.id).status == ThesisStatus.IN_PROGRESS


def test_defended_cannot_go_to_submitted_no_defense(service) -> None:
    t = _in_progress(service)
    service.transition(t.id, ThesisStatus.DEFENDED)
    with pytest.raises(TransitionError):
        service.transition(t.id, ThesisStatus.SUBMITTED_NO_DEFENSE)
