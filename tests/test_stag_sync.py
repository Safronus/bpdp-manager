"""Testy aktualizace existujících prací ze STAG (StagSyncDialog)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QMessageBox

import bpdpmanager.ui.stag_sync_dialog as mod
from bpdpmanager.models import Student, Thesis
from bpdpmanager.models.enums import AttachmentKind, ThesisStatus, ThesisType
from bpdpmanager.services import ThesisService
from bpdpmanager.services.stag_api import StagFile
from bpdpmanager.storage import JsonRepository
from bpdpmanager.ui.stag_sync_dialog import StagSyncDialog, _SyncTarget


@pytest.fixture(scope="module")
def qapp():
    yield QApplication.instance() or QApplication([])


@pytest.fixture
def service(tmp_path: Path) -> ThesisService:
    repo = JsonRepository(path=tmp_path / "db.json", backup_path=tmp_path / "db.json.bak")
    return ThesisService(repo)


_CSV_DUO = (
    "stavPrace;typPrace;osCislo.student\r\nDUO;Bakalářská práce;A1\r\n"
).encode()


def _review_file():
    return StagFile(
        soubidno="s1", filename="posudek_vedouciho.pdf", download_path="/dl",
        section="supervisor_review", size_hint=1234,
    )


def _seed_thesis(service: ThesisService) -> Thesis:
    st = Student(first_name="Jan", last_name="Novák")
    service.upsert_student(st)
    t = Thesis(
        type=ThesisType.BP, status=ThesisStatus.IN_PROGRESS,
        academic_year="2025/2026", student_id=st.id, adipidno="111",
        title_cs="Téma", title_en="Topic", objectives="1. a", references="x",
    )
    service.upsert_thesis(t)
    return t


def test_new_status_diff() -> None:
    t = _SyncTarget(
        is_opposing=False, obj_id="x", type_code="BP", surname="N", label="L",
        local_status=ThesisStatus.IN_PROGRESS, local_kinds=set(),
        stag_status_code="DUO",
    )
    assert t.new_status == ThesisStatus.DEFENDED
    # Stejný stav → žádný návrh.
    t.local_status = ThesisStatus.DEFENDED
    assert t.new_status is None
    # Oponovaná práce stav nemá.
    t.is_opposing = True
    t.local_status = None
    assert t.new_status is None


def test_resolve_adipidno_by_surname(qapp, monkeypatch) -> None:
    from bpdpmanager.services.stag_api import StagThesisResult

    def fake_search(surname, person, role):
        return [
            StagThesisResult(adipidno="999", surname="Novák", name="Jan",
                             type_label="Bakalářská práce"),
            StagThesisResult(adipidno="888", surname="Novák", name="Jan",
                             type_label="Diplomová práce"),
        ]

    monkeypatch.setattr(mod.stag_api, "search_theses", fake_search)
    # BP → vybere 999 (bakalářská), ne DP.
    assert mod._resolve_adipidno("Novák", "BP", mod.ROLE_SUPERVISOR) == "999"
    assert mod._resolve_adipidno("Novák", "DP", mod.ROLE_SUPERVISOR) == "888"


def test_scan_populates_status_and_file_actions(qapp, service, monkeypatch) -> None:
    _seed_thesis(service)
    monkeypatch.setattr(mod.stag_api, "download_csv", lambda a: _CSV_DUO)
    monkeypatch.setattr(mod.stag_api, "list_thesis_files", lambda a: [_review_file()])

    dlg = StagSyncDialog(service, "supervisor")
    dlg._scan()  # přímo (bez event loopu)

    assert len(dlg._targets) == 1
    tgt = dlg._targets[0]
    assert tgt.new_status == ThesisStatus.DEFENDED
    assert len(tgt.stag_files) == 1

    actions = dlg._checked_actions()
    kinds = {a[0] for a in actions}
    assert "status" in kinds      # změna stavu předzaškrtnutá
    assert "file" in kinds        # nový posudek (druh chybí) předzaškrtnutý


def test_scan_file_already_present_not_prechecked(qapp, service, monkeypatch) -> None:
    """Když práce už má posudek vedoucího, soubor není předzaškrtnutý."""
    t = _seed_thesis(service)
    # Doplň lokálně posudek vedoucího → druh už existuje.
    src = Path(os.environ.get("TMPDIR", "/tmp")) / "fake_review.pdf"
    src.write_bytes(b"%PDF-1.4 local")
    service.attach_document(t.id, src, kind=AttachmentKind.SUPERVISOR_REVIEW)

    monkeypatch.setattr(mod.stag_api, "download_csv", lambda a: _CSV_DUO)
    monkeypatch.setattr(mod.stag_api, "list_thesis_files", lambda a: [_review_file()])

    dlg = StagSyncDialog(service, "supervisor")
    dlg._scan()
    file_actions = [a for a in dlg._checked_actions() if a[0] == "file"]
    assert not file_actions  # stejný druh už máš → nepředzaškrtnuto


def test_apply_updates_status_and_attaches(qapp, service, monkeypatch) -> None:
    t = _seed_thesis(service)
    monkeypatch.setattr(mod.stag_api, "download_csv", lambda a: _CSV_DUO)
    monkeypatch.setattr(mod.stag_api, "list_thesis_files", lambda a: [_review_file()])

    class FakeClient:
        def list_thesis_files(self, adip):
            return [_review_file()]

        def download_file(self, path):
            return b"%PDF-1.4 downloaded review"

    monkeypatch.setattr(mod.stag_api, "StagClient", FakeClient)
    # Souhrnný dialog neblokuj.
    monkeypatch.setattr(QMessageBox, "exec", lambda self: 0)
    monkeypatch.setattr(QMessageBox, "clickedButton", lambda self: None)

    dlg = StagSyncDialog(service, "supervisor")
    dlg._scan()
    dlg._apply()

    updated = service.get_thesis(t.id)
    assert updated.status == ThesisStatus.DEFENDED
    assert any(a.kind == AttachmentKind.SUPERVISOR_REVIEW for a in updated.attachments)
    assert dlg.changed is True
