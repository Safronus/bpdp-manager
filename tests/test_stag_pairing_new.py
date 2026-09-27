"""Tichá kontrola: „nová" STAG práce, kterou už evidujeme bez STAG ID, se spáruje.

Ručně založený zájemce / vypsané téma nemá STAG ID. Po schválení ve STAG ho
kontrola dřív hlásila jako „🆕 nové ve STAG" (páruje jen dle STAG ID). Teď se
přísně spáruje (jméno + typ, pak os. číslo a rok z CSV) a nabídne se aktualizace
existující práce — ta převezme stav ze STAG a doplní prázdné zadání.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QMessageBox

import bpdpmanager.ui.stag_check as chk
import bpdpmanager.ui.stag_sync_dialog as sync
from bpdpmanager.models import OpposingThesis, Student, Thesis
from bpdpmanager.models.enums import ThesisStatus, ThesisType
from bpdpmanager.services import ThesisService
from bpdpmanager.services.stag_api import StagThesisResult
from bpdpmanager.services.stag_csv_importer import ImportRole, ParsedRecord
from bpdpmanager.services.stag_match import LocalWork, pair_new_result
from bpdpmanager.services.thesis_service import TransitionError
from bpdpmanager.storage import JsonRepository

HEADER = ("adipidno;stavPrace;typPrace;osCislo.student;jmeno.student;"
          "prijmeni.student;datumZadani;temaHlavni;temaHlavniAn;zasady;seznamLiter")


def _csv(adip, uid, state="R", typ="Diplomová práce", zadani="1.10.2026"):
    row = (f"{adip};{state};{typ};{uid};Jan;Novák;{zadani};Fiktivní téma;"
           "Fictional topic;<ol><li>bod</li></ol>;<ol><li>zdroj</li></ol>")
    return f"{HEADER}\r\n{row}\r\n".encode()


@pytest.fixture(scope="module")
def qapp():
    yield QApplication.instance() or QApplication([])


@pytest.fixture
def service(tmp_path: Path) -> ThesisService:
    repo = JsonRepository(path=tmp_path / "db.json", backup_path=tmp_path / "db.json.bak")
    return ThesisService(repo)


def _manual_dp(service, uid="A24002", status=ThesisStatus.LISTED, **kw) -> Thesis:
    st = Student(first_name="Jan", last_name="Novák", university_id=uid)
    service.upsert_student(st)
    t = Thesis(type=ThesisType.DP, academic_year="2026/2027", status=status,
               student_id=st.id, **kw)
    service.upsert_thesis(t)
    return t


def _res(adip="999"):
    return StagThesisResult(adipidno=adip, surname="Novák", name="Jan",
                            type_label="Diplomová práce", supervisor="Eva Vedoucí")


# --- služba: pair_new_result ---------------------------------------------------------


def _rec(uid):
    return ParsedRecord(role=ImportRole.SUPERVISOR, student_uni_id=uid,
                        academic_year="2026/2027")


def test_pair_unique_ambiguous_none() -> None:
    w = lambda uid: LocalWork("Novák", "DP", "Jan", uni_id=uid, academic_year="2026/2027")  # noqa: E731
    fetched = []

    def fetch(adip):
        fetched.append(adip)
        return _rec("A24002")

    p = pair_new_result(_res(), [("a", w("A24002")), ("b", w("A20001"))], fetch_record=fetch)
    assert p.local_id == "a" and not p.ambiguous and p.record is not None
    p = pair_new_result(_res(), [("a", w("")), ("b", w(""))], fetch_record=fetch)
    assert p.local_id == "" and p.ambiguous
    fetched.clear()
    p = pair_new_result(_res(), [("x", LocalWork("Černá", "DP"))], fetch_record=fetch)
    assert p.local_id == "" and not p.ambiguous and fetched == []   # bez shody jména nic nestahuje


# --- tichá kontrola --------------------------------------------------------------------


def _patch_stag(monkeypatch, results, csv_by_adip):
    monkeypatch.setattr(chk.stag_api, "search_theses", lambda *a: results)
    monkeypatch.setattr(chk.stag_api, "download_csv", lambda a: csv_by_adip[a])
    monkeypatch.setattr(chk, "_fetch_target_state", lambda a: ("", [], ""))


def test_check_pairs_manual_future_thesis_instead_of_new(service, monkeypatch) -> None:
    t = _manual_dp(service)
    _patch_stag(monkeypatch, [_res("999")], {"999": _csv("999", "A24002")})
    r = chk.compute_stag_check(service, "Eva Vedoucí", "Vedoucí")
    assert r.new == []
    assert r.supervised_ids == [t.id]
    assert "spárovat" in r.supervised[0] and "V řešení" in r.supervised[0]


def test_check_other_student_stays_new(service, monkeypatch) -> None:
    _manual_dp(service, uid="A20001")                     # jiné os. číslo → jiná osoba
    _patch_stag(monkeypatch, [_res("999")], {"999": _csv("999", "A24002")})
    r = chk.compute_stag_check(service, "Eva Vedoucí", "Vedoucí")
    assert len(r.new) == 1 and r.supervised_ids == []


def test_check_ambiguous_stays_new_with_warning(service, monkeypatch) -> None:
    _manual_dp(service, uid="")
    _manual_dp(service, uid="")
    _patch_stag(monkeypatch, [_res("999")], {"999": _csv("999", "A24002")})
    r = chk.compute_stag_check(service, "Eva Vedoucí", "Vedoucí")
    assert len(r.new) == 1 and "možná už evidováno" in r.new[0]


def test_check_pairs_opposing_without_stag_id(service, monkeypatch) -> None:
    o = OpposingThesis(type=ThesisType.DP, academic_year="2026/2027",
                       student_last_name="Novák", student_first_name="Jan",
                       student_university_id="A24002")
    service.upsert_opposing_thesis(o)
    res = StagThesisResult(adipidno="999", surname="Novák", name="Jan",
                           type_label="Diplomová práce", reviewer="Eva Vedoucí")
    monkeypatch.setattr(chk.stag_api, "search_theses",
                        lambda s, p, role: [res] if role == chk.stag_api.ROLE_OPPONENT else [])
    monkeypatch.setattr(chk.stag_api, "download_csv", lambda a: _csv("999", "A24002"))
    monkeypatch.setattr(chk, "_fetch_target_state", lambda a: ("", [], ""))
    r = chk.compute_stag_check(service, "Eva Vedoucí", "Vedoucí")
    assert r.new == [] and r.opposing_ids == [o.id]


def test_check_includes_future_thesis_with_stag_id(service, monkeypatch) -> None:
    t = _manual_dp(service, adipidno="555")
    monkeypatch.setattr(chk.stag_api, "search_theses", lambda *a: [])
    monkeypatch.setattr(chk, "_fetch_target_state", lambda a: ("R", [], ""))
    r = chk.compute_stag_check(service, "Eva Vedoucí", "Vedoucí")
    assert r.supervised_ids == [t.id] and "změna stavu" in r.supervised[0]


# --- služba: adopt_stag_status -----------------------------------------------------------


def test_adopt_fills_only_empty_fields_and_skips_graph(service) -> None:
    # Zájemce bez tématu → V řešení: ruční graf to nedovolí, STAG (autorita) ano.
    t = _manual_dp(service, status=ThesisStatus.INTERESTED, title_cs="Můj název")
    with pytest.raises(TransitionError):
        service.transition(t.id, ThesisStatus.IN_PROGRESS)
    service.adopt_stag_status(t.id, ThesisStatus.IN_PROGRESS, {
        "title_cs": "Název ze STAG", "title_en": "Fictional topic",
        "objectives": "bod", "references": "zdroj",
    })
    saved = service.get_thesis(t.id)
    assert saved.status == ThesisStatus.IN_PROGRESS
    assert saved.title_cs == "Můj název"                  # vyplněné se nepřepíše
    assert (saved.title_en, saved.objectives) == ("Fictional topic", "bod")


def test_adopt_other_statuses_use_normal_validation(service) -> None:
    t = _manual_dp(service, status=ThesisStatus.DEFENDED)
    with pytest.raises(TransitionError):                  # DEFENDED → LISTED nepovoleno
        service.adopt_stag_status(t.id, ThesisStatus.LISTED)


# --- celý tok: aktualizace z proužku -----------------------------------------------------


def test_sync_subset_pairs_and_moves_to_in_progress(qapp, service, monkeypatch) -> None:
    t = _manual_dp(service)                               # bez STAG ID, bez zadání
    monkeypatch.setattr(sync.stag_api, "search_theses", lambda *a: [_res("999")])
    monkeypatch.setattr(sync.stag_api, "download_csv", lambda a: _csv("999", "A24002"))
    monkeypatch.setattr(sync.stag_api, "list_thesis_files", lambda a: [])
    monkeypatch.setattr(QMessageBox, "exec", lambda self: 0)
    monkeypatch.setattr(QMessageBox, "clickedButton", lambda self: None)

    dlg = sync.StagSyncDialog(service, sync.ROLE_SUPERVISOR, subset=[t.id])
    dlg._scan()
    assert service.get_thesis(t.id).adipidno == "999"     # jednoznačně spárováno
    assert dlg._targets[0].new_status == ThesisStatus.IN_PROGRESS
    dlg._apply()
    saved = service.get_thesis(t.id)
    assert saved.status == ThesisStatus.IN_PROGRESS
    assert saved.title_en == "Fictional topic" and saved.references == "zdroj"
