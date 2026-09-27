"""Testy aktualizace existujících prací ze STAG (StagSyncDialog)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QMessageBox

import bpdpmanager.ui.stag_sync_dialog as mod
from bpdpmanager.models import OpposingThesis, Student, Thesis
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


def test_resolve_adipidno_strict(qapp, monkeypatch) -> None:
    """Typ + jméno + osobní číslo z CSV; při nejednoznačnosti se ID neuloží."""
    from bpdpmanager.services.stag_api import StagThesisResult

    seen = {}

    def fake_search(surname, person, role):
        seen["person"] = person
        return [
            StagThesisResult(adipidno="999", surname="Novák", name="Jan",
                             type_label="Bakalářská práce"),
            StagThesisResult(adipidno="888", surname="Novák", name="Jan",
                             type_label="Diplomová práce"),
            StagThesisResult(adipidno="777", surname="Novák", name="Jan",
                             type_label="Diplomová práce"),
        ]

    csv_by_adip = {
        "999": "stavPrace;typPrace;osCislo.student\r\nR;Bakalářská práce;A1\r\n",
        "888": "stavPrace;typPrace;osCislo.student\r\nR;Diplomová práce;A2\r\n",
        "777": "stavPrace;typPrace;osCislo.student\r\nR;Diplomová práce;A9\r\n",
    }
    monkeypatch.setattr(mod.stag_api, "search_theses", fake_search)
    monkeypatch.setattr(mod.stag_api, "download_csv", lambda a: csv_by_adip[a].encode())

    def tgt(type_code, uni_id=""):
        return _SyncTarget(is_opposing=False, obj_id="x", type_code=type_code,
                           surname="Novák", label="", local_status=None,
                           local_kinds=set(), first_name="Jan", uni_id=uni_id)

    assert mod._resolve_adipidno(tgt("BP"), mod.ROLE_SUPERVISOR, "Vedoucí") == ("999", "")
    assert seen["person"] == "Vedoucí"                     # jen mezi mými pracemi
    # Dvě DP téhož jména: rozhodne osobní číslo…
    assert mod._resolve_adipidno(tgt("DP", "A2"), mod.ROLE_SUPERVISOR, "") == ("888", "")
    # …bez něj je to nejednoznačné → žádné ID.
    adip, err = mod._resolve_adipidno(tgt("DP"), mod.ROLE_SUPERVISOR, "")
    assert adip == "" and "nejednoznačné" in err


def test_find_new_works_sets_flag(qapp, service) -> None:
    """„Najít nové práce…" nastaví příznak (caller pak otevře hromadné stažení)."""
    dlg = StagSyncDialog(service, "supervisor")
    assert dlg.open_new_works is False
    dlg._find_new_works()
    assert dlg.open_new_works is True


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

        def download_file_streamed(self, path, on_progress=None, timeout=None):
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


def test_opposing_sync_backfills_status(qapp, service, monkeypatch) -> None:
    """Aktualizace oponentur doplní STAG stav (stag_state_code) i existujícím."""
    monkeypatch.setattr(mod.stag_api, "download_csv", lambda a: _CSV_DUO)
    monkeypatch.setattr(mod.stag_api, "list_thesis_files", lambda a: [])
    cur = service.current_academic_year()
    op = OpposingThesis(type=ThesisType.BP, academic_year=cur,
                        student_last_name="Novák", adipidno="111")
    service.upsert_opposing_thesis(op)
    assert not op.stag_state_code

    dlg = StagSyncDialog(service, "opponent")
    dlg._scan()

    assert service.get_opposing_thesis(op.id).stag_state_code == "DUO"


@pytest.mark.parametrize(("resolved", "stored"), [
    (("", "nejednoznačné — ve STAG 2 odpovídající práce"), ""),
    (("555", ""), "555"),
])
def test_scan_without_stag_id_stores_only_unique_match(
    qapp, service, monkeypatch, resolved, stored
) -> None:
    st = Student(first_name="Jan", last_name="Novák", university_id="A24002")
    service.upsert_student(st)
    t = Thesis(type=ThesisType.DP, status=ThesisStatus.IN_PROGRESS,
               academic_year="2026/2027", student_id=st.id)
    service.upsert_thesis(t)
    seen = {}

    def fake_resolve(work, person_role, person_surname=""):
        seen["work"] = work
        seen["person"] = person_surname
        return resolved

    class _Prof:
        user_surname = "Vedoucí"

    class _PM:
        active = _Prof()

    monkeypatch.setattr(mod, "resolve_adipidno", fake_resolve)
    monkeypatch.setattr(mod.stag_api, "download_csv", lambda a: _CSV_DUO)
    monkeypatch.setattr(mod.stag_api, "list_thesis_files", lambda a: [])
    dlg = StagSyncDialog(service, "supervisor", profile_manager=_PM())
    dlg._scan()

    w = seen["work"]
    assert (w.surname, w.first_name, w.uni_id, w.academic_year, w.type_code) == (
        "Novák", "Jan", "A24002", "2026/2027", "DP")
    assert seen["person"] == "Vedoucí"
    assert (service.get_thesis(t.id).adipidno or "") == stored
    if not stored:
        assert "nejednoznačné" in dlg._targets[0].error
