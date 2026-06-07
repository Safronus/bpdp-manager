"""Smoke testy dialogů přenosu práce (výběr co zahrnout / co aktualizovat)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from bpdpmanager.models import Obor, Opponent, Student, Thesis
from bpdpmanager.models.enums import AttachmentKind, OpponentKind, ThesisStatus, ThesisType
from bpdpmanager.services import ThesisService
from bpdpmanager.services.thesis_export import export_thesis_to_zip
from bpdpmanager.storage import JsonRepository
from bpdpmanager.ui.thesis_transfer_dialog import (
    _NODE_FILE,
    _ROLE_NODE,
    ThesisExportDialog,
    ThesisImportDialog,
)


@pytest.fixture(scope="module")
def qapp():
    yield QApplication.instance() or QApplication([])


@pytest.fixture
def service(tmp_path: Path) -> ThesisService:
    repo = JsonRepository(path=tmp_path / "db.json", backup_path=tmp_path / "db.json.bak")
    return ThesisService(repo)


def _seed(service: ThesisService, tmp_path: Path) -> Thesis:
    service.upsert_obor(Obor(name="ITA-P", stag_code="pbITA"))
    s = Student(first_name="Jan", last_name="Novák", obor="ITA-P", university_id="A1")
    service.upsert_student(s)
    o = Opponent(kind=OpponentKind.INTERNAL, name="Ing. Oponent")
    service.upsert_opponent(o)
    t = Thesis(type=ThesisType.BP, academic_year="2024/2025", student_id=s.id,
               opponent_id=o.id, status=ThesisStatus.IN_PROGRESS, title_cs="Moje práce")
    service.upsert_thesis(t)
    src = tmp_path / "posudek.pdf"
    src.write_bytes(b"%PDF dummy")
    service.attach_document(t.id, src, kind=AttachmentKind.SUPERVISOR_REVIEW)
    return t


def _uncheck_first_file(dlg) -> None:
    root = dlg.tree.invisibleRootItem()

    def _walk(item):
        if item.data(0, _ROLE_NODE) == _NODE_FILE:
            item.setCheckState(0, Qt.CheckState.Unchecked)
            return True
        for i in range(item.childCount()):
            if _walk(item.child(i)):
                return True
        return False

    for i in range(root.childCount()):
        if _walk(root.child(i)):
            return


def test_export_dialog_default_all_then_uncheck(qapp, service, tmp_path) -> None:
    t = _seed(service, tmp_path)
    dlg = ThesisExportDialog(service, t.id)
    sel = dlg.selection()
    assert sel.include_student and sel.include_opponent and sel.include_obor
    assert len(sel.file_relpaths) == 1  # default vše zaškrtnuto

    _uncheck_first_file(dlg)
    sel2 = dlg.selection()
    assert len(sel2.file_relpaths) == 0


def test_import_dialog_detects_existing_and_update_mode(qapp, service, tmp_path) -> None:
    t = _seed(service, tmp_path)
    zip_path = tmp_path / "prace.zip"
    export_thesis_to_zip(service, t.id, zip_path)

    dlg = ThesisImportDialog(service, zip_path)
    # Práce existuje (stejné ID) → default režim aktualizace.
    assert dlg.contents.existing is not None
    assert dlg.mode() == ThesisImportDialog.MODE_UPDATE
    assert dlg.target_id() == t.id
    usel = dlg.update_selection()
    assert usel.update_data and usel.update_student

    # Přepnutí na novou práci → cíl je None.
    dlg.rb_new.setChecked(True)
    assert dlg.mode() == ThesisImportDialog.MODE_NEW
    assert dlg.target_id() is None


def test_import_dialog_new_when_no_match(qapp, service, tmp_path) -> None:
    t = _seed(service, tmp_path)
    zip_path = tmp_path / "prace.zip"
    export_thesis_to_zip(service, t.id, zip_path)

    repo2 = JsonRepository(path=tmp_path / "db2.json", backup_path=tmp_path / "db2.json.bak")
    svc2 = ThesisService(repo2)
    dlg = ThesisImportDialog(svc2, zip_path)
    assert dlg.contents.existing is None
    assert dlg.mode() == ThesisImportDialog.MODE_NEW
