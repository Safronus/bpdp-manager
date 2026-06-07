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


def _populate_with(dlg, target):
    """Naplní strom konkrétním cílem (obejde síťový _scan)."""
    dlg._targets = [target]
    dlg._populate()


def test_positive_message_when_nothing_new(qapp, service) -> None:
    """Když je jediný STAG soubor druhu, který už máš → pozitivní hláška."""
    from bpdpmanager.models.enums import AttachmentKind, ThesisStatus
    from bpdpmanager.services.stag_api import StagFile
    from bpdpmanager.ui.stag_sync_dialog import _SyncTarget

    dlg = StagSyncDialog(service, ROLE_SUPERVISOR, single=(False, "x"))
    tgt = _SyncTarget(
        is_opposing=False, obj_id="1", type_code="BP", surname="N",
        label="A — T (BP)", local_status=ThesisStatus.IN_PROGRESS,
        local_kinds={AttachmentKind.THESIS_TEXT}, adipidno="X",
        stag_status_code="",  # žádná změna stavu
        stag_files=[StagFile(soubidno="s1", filename="fulltext.pdf",
                             download_path="/d", section="text", size_hint=1700000)],
    )
    _populate_with(dlg, tgt)
    assert "Vše je aktuální" in dlg.lbl_status.text()
    assert not dlg.btn_apply.isEnabled()  # nic předzaškrtnuto


def test_message_when_new_file(qapp, service) -> None:
    """Chybějící druh souboru → počítá se jako změna, hláška „se změnami"."""
    from bpdpmanager.models.enums import ThesisStatus
    from bpdpmanager.services.stag_api import StagFile
    from bpdpmanager.ui.stag_sync_dialog import _SyncTarget

    dlg = StagSyncDialog(service, ROLE_SUPERVISOR, single=(False, "x"))
    tgt = _SyncTarget(
        is_opposing=False, obj_id="1", type_code="BP", surname="N",
        label="A — T (BP)", local_status=ThesisStatus.IN_PROGRESS,
        local_kinds=set(), adipidno="X", stag_status_code="",
        stag_files=[StagFile(soubidno="s1", filename="posudek.pdf",
                             download_path="/d", section="supervisor_review")],
    )
    _populate_with(dlg, tgt)
    assert "se změnami" in dlg.lbl_status.text()
    assert dlg.btn_apply.isEnabled()  # nový druh je předzaškrtnutý
