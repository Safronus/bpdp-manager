"""Test single-work režimu StagSyncDialog (kontextová akce „Aktualizace ze STAG")."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from bpdpmanager.models import OpposingThesis, Student, Thesis
from bpdpmanager.models.enums import ThesisStatus, ThesisType
from bpdpmanager.services import ThesisService
from bpdpmanager.storage import JsonRepository
from bpdpmanager.ui.stag_sync_dialog import ROLE_OPPONENT, ROLE_SUPERVISOR, StagSyncDialog


@pytest.fixture(scope="module")
def qapp():
    yield QApplication.instance() or QApplication([])


@pytest.fixture
def service(tmp_path: Path) -> ThesisService:
    repo = JsonRepository(path=tmp_path / "db.json", backup_path=tmp_path / "db.json.bak")
    return ThesisService(repo)


def test_single_target_supervised_any_status(qapp, service) -> None:
    """Single režim vybere danou práci bez ohledu na stav (i z Historie)."""
    s = Student(first_name="Jan", last_name="Novák")
    service.upsert_student(s)
    # DEFENDED (Historie) — hromadný režim by ji nevzal, single ano.
    t = Thesis(type=ThesisType.BP, academic_year="2024/2025", student_id=s.id,
               status=ThesisStatus.DEFENDED, adipidno="A123", title_cs="Práce")
    service.upsert_thesis(t)

    dlg = StagSyncDialog(service, ROLE_SUPERVISOR, single=(False, t.id))
    assert dlg.windowTitle() == "Aktualizace práce ze STAG"
    targets = dlg._collect_targets()
    assert len(targets) == 1
    assert targets[0].obj_id == t.id
    assert targets[0].is_opposing is False
    assert targets[0].adipidno == "A123"


def test_single_target_opposing(qapp, service) -> None:
    op = OpposingThesis(type=ThesisType.DP, academic_year="2018/2019",
                        student_last_name="Malá", adipidno="OP9", title_cs="P")
    service.upsert_opposing_thesis(op)

    dlg = StagSyncDialog(service, ROLE_OPPONENT, single=(True, op.id))
    targets = dlg._collect_targets()
    assert len(targets) == 1
    assert targets[0].obj_id == op.id
    assert targets[0].is_opposing is True
    assert targets[0].adipidno == "OP9"


def test_single_target_missing_work_empty(qapp, service) -> None:
    dlg = StagSyncDialog(service, ROLE_SUPERVISOR, single=(False, "neexistuje"))
    assert dlg._collect_targets() == []
