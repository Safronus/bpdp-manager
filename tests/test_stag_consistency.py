"""Test kontroly konzistence DB vs STAG (chybějící druhy souborů)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

import bpdpmanager.ui.stag_consistency_dialog as mod
from bpdpmanager.models import Attachment, OpposingThesis, Student, Thesis
from bpdpmanager.models.enums import AttachmentKind, ThesisStatus, ThesisType
from bpdpmanager.services import ThesisService
from bpdpmanager.services.stag_api import StagFile
from bpdpmanager.storage import JsonRepository
from bpdpmanager.ui.stag_consistency_dialog import StagConsistencyDialog


@pytest.fixture(scope="module")
def qapp():
    yield QApplication.instance() or QApplication([])


@pytest.fixture
def service(tmp_path: Path) -> ThesisService:
    repo = JsonRepository(path=tmp_path / "db.json", backup_path=tmp_path / "db.json.bak")
    return ThesisService(repo)


def _stag_files():
    return [
        StagFile(soubidno="1", filename="full.pdf", download_path="/a", section="text"),
        StagFile(soubidno="2", filename="posudek.pdf", download_path="/b",
                 section="supervisor_review"),
    ]


def test_consistency_detects_missing_kind(qapp, service, monkeypatch) -> None:
    # Práce s STAG ID, v DB má jen plný text → posudek vedoucího chybí.
    monkeypatch.setattr(mod.QTimer, "singleShot", lambda *a, **k: None)
    monkeypatch.setattr(mod.stag_api, "list_thesis_files", lambda adip: _stag_files())

    st = Student(first_name="Jan", last_name="Novák")
    service.upsert_student(st)
    t = Thesis(
        type=ThesisType.BP, status=ThesisStatus.IN_PROGRESS,
        academic_year="2025/2026", student_id=st.id, adipidno="111",
        attachments=[Attachment(
            label="text", url_or_path="x.pdf",
            kind=AttachmentKind.THESIS_TEXT, is_file=True,
        )],
    )
    service.upsert_thesis(t)
    # Práce bez STAG ID → nelze ověřit.
    service.upsert_thesis(Thesis(
        type=ThesisType.DP, status=ThesisStatus.IN_PROGRESS,
        academic_year="2025/2026", student_id=st.id,
    ))

    dlg = StagConsistencyDialog(service)
    dlg._scan()

    assert len(dlg._rows) == 1
    missing_kinds = {k for k, _ in dlg._rows[0].missing}
    assert AttachmentKind.SUPERVISOR_REVIEW in missing_kinds  # chybí posudek
    assert AttachmentKind.THESIS_TEXT not in missing_kinds     # text máš
    assert dlg._no_id  # DP bez STAG ID


def test_consistency_complete_when_all_kinds_present(qapp, service, monkeypatch) -> None:
    monkeypatch.setattr(mod.QTimer, "singleShot", lambda *a, **k: None)
    monkeypatch.setattr(mod.stag_api, "list_thesis_files", lambda adip: _stag_files())

    op = OpposingThesis(
        type=ThesisType.BP, academic_year="2025/2026", adipidno="222",
        student_last_name="Dvořák",
        attachments=[
            Attachment(label="t", url_or_path="t", kind=AttachmentKind.THESIS_TEXT,
                       is_file=True),
            Attachment(label="r", url_or_path="r",
                       kind=AttachmentKind.SUPERVISOR_REVIEW, is_file=True),
        ],
    )
    service.upsert_opposing_thesis(op)

    dlg = StagConsistencyDialog(service)
    dlg._scan()
    assert dlg._rows and not dlg._rows[0].missing  # vše máš → nic nechybí


def test_consistency_error_surfaced(qapp, service, monkeypatch) -> None:
    monkeypatch.setattr(mod.QTimer, "singleShot", lambda *a, **k: None)

    def boom(adip):
        raise RuntimeError("síť")

    monkeypatch.setattr(mod.stag_api, "list_thesis_files", boom)
    st = Student(first_name="A", last_name="B")
    service.upsert_student(st)
    service.upsert_thesis(Thesis(
        type=ThesisType.BP, status=ThesisStatus.IN_PROGRESS,
        academic_year="2025/2026", student_id=st.id, adipidno="333",
    ))
    dlg = StagConsistencyDialog(service)
    dlg._scan()
    assert dlg._rows[0].error  # chyba dotazu se zaznamená


def test_consistency_skips_future(qapp, service, monkeypatch) -> None:
    """Budoucí práce (zájemce / vypsané téma) se nekontrolují."""
    monkeypatch.setattr(mod.QTimer, "singleShot", lambda *a, **k: None)
    monkeypatch.setattr(mod.stag_api, "list_thesis_files", lambda a: _stag_files())
    st = Student(first_name="Jan", last_name="Novák")
    service.upsert_student(st)
    service.upsert_thesis(Thesis(
        type=ThesisType.BP, status=ThesisStatus.RESERVED,  # budoucí
        academic_year="2025/2026", student_id=st.id, adipidno="111",
    ))
    dlg = StagConsistencyDialog(service)
    dlg._scan()
    assert dlg._rows == []        # budoucí práce přeskočena
    assert dlg._no_id == []       # a ani v „bez STAG ID"


def test_consistency_downloads_missing(qapp, service, monkeypatch) -> None:
    """Zaškrtnutý chybějící soubor jde dostáhnout a připojí se k práci."""
    from PySide6.QtWidgets import QMessageBox

    monkeypatch.setattr(mod.QTimer, "singleShot", lambda *a, **k: None)
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: None)
    review = StagFile(soubidno="r1", filename="posudek.pdf", download_path="/dl",
                      section="supervisor_review")
    monkeypatch.setattr(mod.stag_api, "list_thesis_files", lambda a: [review])

    class FakeClient:
        def list_thesis_files(self, a):
            return [review]

        def download_file(self, p):
            return b"%PDF-1.4 fake review"

    monkeypatch.setattr(mod.stag_api, "StagClient", FakeClient)

    st = Student(first_name="A", last_name="B")
    service.upsert_student(st)
    t = Thesis(type=ThesisType.BP, status=ThesisStatus.IN_PROGRESS,
               academic_year="2025/2026", student_id=st.id, adipidno="111")
    service.upsert_thesis(t)

    dlg = StagConsistencyDialog(service)
    dlg._scan()
    assert dlg._rows[0].missing  # posudek chybí, předzaškrtnutý
    dlg._download_selected()

    updated = service.get_thesis(t.id)
    assert any(a.kind == AttachmentKind.SUPERVISOR_REVIEW for a in updated.attachments)
    assert dlg.changed_any is True
