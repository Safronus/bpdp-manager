"""Testy tiché kontroly STAG (compute_stag_check) — počítání změn / nových prací."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import bpdpmanager.ui.stag_check as chk
from bpdpmanager.models import OpposingThesis, Student, Thesis
from bpdpmanager.models.enums import ThesisStatus, ThesisType
from bpdpmanager.services import ThesisService
from bpdpmanager.services.stag_api import StagThesisResult
from bpdpmanager.storage import JsonRepository


@pytest.fixture
def service(tmp_path: Path) -> ThesisService:
    repo = JsonRepository(path=tmp_path / "db.json", backup_path=tmp_path / "db.json.bak")
    return ThesisService(repo)


def _patch(monkeypatch, fetch_map: dict, search_results=None, search_raises=False):
    def fake_fetch(adip):
        return fetch_map.get(adip, ("", [], ""))

    monkeypatch.setattr(chk, "_fetch_target_state", fake_fetch)

    def fake_search(student, person, role):
        if search_raises:
            raise RuntimeError("offline")
        return search_results or []

    monkeypatch.setattr(chk.stag_api, "search_theses", fake_search)


def test_detects_status_change_and_new_works(service, monkeypatch) -> None:
    s = Student(first_name="Jan", last_name="Novák")
    service.upsert_student(s)
    # Vedená „V řešení" → STAG hlásí obhájeno (DUO) → změna stavu.
    led = Thesis(type=ThesisType.BP, status=ThesisStatus.IN_PROGRESS,
                 academic_year="2024/2025", student_id=s.id, adipidno="111")
    service.upsert_thesis(led)
    # Oponentura akt. roku bez kódu → STAG hlásí DUO → změna.
    op = OpposingThesis(type=ThesisType.DP, academic_year=service.current_academic_year(),
                        student_last_name="Dvořák", adipidno="222")
    service.upsert_opposing_thesis(op)

    _patch(
        monkeypatch,
        fetch_map={"111": ("DUO", [], ""), "222": ("DUO", [], "")},
        search_results=[
            StagThesisResult(adipidno="111", supervisor="Jan Novák"),   # už máš
            StagThesisResult(adipidno="999", supervisor="Jan Novák"),   # nová, moje
            StagThesisResult(adipidno="888", supervisor="Pavel Novák"),  # jmenovec
        ],
    )
    r = chk.compute_stag_check(service, "Jan Novák")
    assert r.ok
    assert r.supervised_changes == 1
    assert r.opposing_changes == 1
    # Jen 999 (111 už máš; 888 je jmenovec Pavel → odfiltrován dle celého jména).
    assert r.new_works == 1
    assert r.total_changes == 3
    # ID dotčených prací — pro tlačítka „Aktualizovat…" v náhledu (subset).
    assert r.supervised_ids == [led.id]
    assert r.opposing_ids == [op.id]


def test_no_changes_all_aktualni(service, monkeypatch) -> None:
    s = Student(first_name="A", last_name="B")
    service.upsert_student(s)
    led = Thesis(type=ThesisType.BP, status=ThesisStatus.IN_PROGRESS,
                 academic_year="2024/2025", student_id=s.id, adipidno="111")
    service.upsert_thesis(led)
    # STAG hlásí „R" (v řešení) = stejný stav, žádné soubory → beze změn.
    _patch(monkeypatch, fetch_map={"111": ("R", [], "")}, search_results=[
        StagThesisResult(adipidno="111"),
    ])
    r = chk.compute_stag_check(service, "Tester")
    assert r.ok
    assert r.total_changes == 0
    assert r.checked == 1
    assert r.total == 1   # jedna evidovaná práce ke kontrole (X z Y)
    # Pro debug: zkontrolovaná-a-aktuální práce je vypsaná jmenovitě.
    assert len(r.up_to_date) == 1
    assert "A B" in r.up_to_date[0] and "(vedená)" in r.up_to_date[0]


def test_missing_file_detail_names_kind(service, monkeypatch) -> None:
    """Náhled u nového souboru uvádí KTERÝ druh (ne generické „nový soubor")."""
    from bpdpmanager.services.stag_api import StagFile

    s = Student(first_name="A", last_name="B")
    service.upsert_student(s)
    led = Thesis(type=ThesisType.BP, status=ThesisStatus.IN_PROGRESS,
                 academic_year="2024/2025", student_id=s.id, adipidno="111")
    service.upsert_thesis(led)
    # STAG nabízí posudek oponenta (stejný stav „R") → chybějící druh.
    review = StagFile(soubidno="9", filename="posudek.pdf", download_path="/r",
                      section="opponent_review")
    _patch(monkeypatch, fetch_map={"111": ("R", [review], "")}, search_results=[])
    r = chk.compute_stag_check(service, "")
    assert r.supervised_changes == 1
    assert "Posudek oponenta" in r.supervised[0]
    assert "nový soubor" in r.supervised[0]


def test_missing_defense_record_offered(service, monkeypatch) -> None:
    """Kontrola hlásí i chybějící „Soubor s průběhem obhajoby" (defense_record)."""
    from bpdpmanager.services.stag_api import StagFile

    s = Student(first_name="A", last_name="B")
    service.upsert_student(s)
    led = Thesis(type=ThesisType.BP, status=ThesisStatus.IN_PROGRESS,
                 academic_year="2024/2025", student_id=s.id, adipidno="111")
    service.upsert_thesis(led)
    record = StagFile(soubidno="7", filename="prubeh_obhajoby.pdf",
                      download_path="/p", section="defense_record")
    _patch(monkeypatch, fetch_map={"111": ("R", [record], "")}, search_results=[])
    r = chk.compute_stag_check(service, "")
    assert r.supervised_changes == 1
    assert "Soubor s průběhem obhajoby" in r.supervised[0]


def test_preview_dialog_buttons(service) -> None:
    """Tlačítka náhledu: Aktualizovat vedené/oponované dle změn, Import jen pro nové."""
    from PySide6.QtWidgets import QApplication

    QApplication.instance() or QApplication([])

    r = chk.StagCheckResult(
        ok=True, checked=3,
        supervised=["X — BP · změna stavu"], supervised_ids=["t1"],
        opposing=[], opposing_ids=[],
        new=[],
    )
    dlg = chk.StagChangesPreviewDialog(r)
    assert dlg.btn_sync_sup.isEnabled()
    assert not dlg.btn_sync_opp.isEnabled()
    assert not dlg.btn_import.isEnabled()   # žádné nové práce → import nedává smysl
    dlg.btn_sync_sup.click()
    assert dlg.open_sync_supervised and not dlg.open_sync_opposing


def test_preview_dialog_inline_both(service) -> None:
    """S callbackem lze aktualizovat vedené i oponované v JEDNOM otevření okna."""
    from PySide6.QtWidgets import QApplication

    QApplication.instance() or QApplication([])

    r = chk.StagCheckResult(
        ok=True, checked=4,
        supervised=["A — BP · změna"], supervised_ids=["t1"],
        opposing=["B — DP · změna"], opposing_ids=["o1"],
        new=[],
    )
    calls: list = []

    def fake_sync(opposing: bool, ids=None) -> bool:
        calls.append((opposing, tuple(ids or ())))
        return True   # něco se změnilo

    dlg = chk.StagChangesPreviewDialog(r, on_sync=fake_sync)
    assert dlg.btn_sync_sup.isEnabled() and dlg.btn_sync_opp.isEnabled()

    dlg.btn_sync_sup.click()
    assert calls == [(False, ("t1",))]        # předá ID z vlastního výsledku
    assert dlg.did_sync
    assert not dlg.btn_sync_sup.isEnabled()   # vedené vyřízeno (zašedlé)
    assert dlg.btn_sync_opp.isEnabled()       # oponované pořád aktivní
    # okno se NEzavřelo (žádný accept → flagy zůstávají False)
    assert not dlg.open_sync_supervised and not dlg.open_sync_opposing

    dlg.btn_sync_opp.click()
    assert calls == [(False, ("t1",)), (True, ("o1",))]
    assert not dlg.btn_sync_opp.isEnabled()   # i oponované vyřízeno


def test_preview_dialog_no_change_keeps_button(service) -> None:
    """Když aktualizace nic nezmění (callback vrátí False), tlačítko zůstává."""
    from PySide6.QtWidgets import QApplication

    QApplication.instance() or QApplication([])

    r = chk.StagCheckResult(
        ok=True, checked=2,
        supervised=["A — BP · změna"], supervised_ids=["t1"],
        opposing=[], opposing_ids=[],
        new=[],
    )
    dlg = chk.StagChangesPreviewDialog(r, on_sync=lambda opposing, ids=None: False)
    dlg.btn_sync_sup.click()
    assert dlg.btn_sync_sup.isEnabled()   # nic se nezměnilo → zůstává aktivní
    assert not dlg.did_sync


def test_offline_marks_not_ok(service, monkeypatch) -> None:
    s = Student(first_name="A", last_name="B")
    service.upsert_student(s)
    service.upsert_thesis(Thesis(type=ThesisType.BP, status=ThesisStatus.IN_PROGRESS,
                                 academic_year="2024/2025", student_id=s.id, adipidno="111"))
    # Všechny pokusy selžou (fetch i search) → offline.
    _patch(monkeypatch, fetch_map={"111": ("", [], "síť")}, search_raises=True)
    r = chk.compute_stag_check(service, "Tester")
    assert r.ok is False
    assert r.error


def test_stag_pending_persist_roundtrip(service) -> None:
    """Pending změny se uloží a načtou (přežijí restart); prázdné = vyřešeno."""
    assert service.load_stag_pending_changes() == {}
    r = chk.StagCheckResult(
        ok=True, checked=3, total=5,
        supervised=["A — BP"], supervised_ids=["t1"],
        opposing=["B — DP"], opposing_ids=["o1"],
        new=["C — nová"],
    )
    service.save_stag_pending_changes({**r.to_pending(), "ts": "09:30", "dismissed": False})
    loaded = service.load_stag_pending_changes()
    assert loaded["supervised_ids"] == ["t1"] and loaded["opposing_ids"] == ["o1"]
    assert loaded["ts"] == "09:30" and loaded["dismissed"] is False
    assert loaded["checked"] == 3 and loaded["total"] == 5

    r2 = chk.StagCheckResult.from_pending(loaded)
    assert r2.ok and r2.total_changes == 3
    assert r2.supervised_ids == ["t1"] and r2.new == ["C — nová"]
    assert r2.checked == 3 and r2.total == 5   # „X z Y" přežije restart

    service.save_stag_pending_changes({})   # vše vyřešeno
    assert service.load_stag_pending_changes() == {}


def test_stag_pending_ignores_other_year(service) -> None:
    """Pending z jiného akademického roku se ignoruje (čistý start)."""
    import json

    p = service._stag_pending_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps({"academic_year": "1999/2000",
                    "pending": {"supervised_ids": ["x"]}}),
        encoding="utf-8")
    assert service.load_stag_pending_changes() == {}


def test_match_committee_prefers_current_year_not_namesake() -> None:
    """Jmenovec s obhajobou z minulého roku (rok 2025, DUO) nesmí přebít
    rozpracovanou práci letošní komise (prázdný rok, DBPOO). Rok obhajoby se
    bere z data slotu (2026), ne z akademického roku „2025/2026" (ten obsahuje
    i „2025"). Fiktivní data."""
    from types import SimpleNamespace

    from bpdpmanager.services.stag_api import StagThesisResult

    results = [
        StagThesisResult(adipidno="OLD", surname="Nováková", name="Jana",
                         type_label="diplomová", year="2025", status_code="DUO"),
        StagThesisResult(adipidno="CUR", surname="Nováková", name="Jana",
                         type_label="diplomová", year="", status_code="DBPOO"),
    ]
    com = SimpleNamespace(
        level="Mgr", academic_year="2025/2026",
        dates=["17. 6. 2026", "18. 6. 2026", "19. 6. 2026"])

    # Rok z data slotu (2026) → jmenovec z 2025 (DUO) se zahodí.
    slot = SimpleNamespace(student_name="Jana Nováková", date="19. 6. 2026")
    m = chk._match_committee_result(results, slot, com)
    assert m is not None and m.adipidno == "CUR" and m.status_code == "DBPOO"

    # Bez data slotu fallback na data komise (taky 2026) → stejný výsledek.
    slot2 = SimpleNamespace(student_name="Jana Nováková", date="")
    m2 = chk._match_committee_result(results, slot2, com)
    assert m2 is not None and m2.adipidno == "CUR"


def test_academic_year_of() -> None:
    """Akademický rok z celého data: měsíc ≥ 9 → rok/rok+1, jinak rok-1/rok."""
    assert chk._academic_year_of("4. 6. 2025") == "2024/2025"
    assert chk._academic_year_of("04.06.2025") == "2024/2025"
    assert chk._academic_year_of("15. 9. 2025") == "2025/2026"
    assert chk._academic_year_of("") == ""
    assert chk._academic_year_of("2025") == ""   # neúplné datum → nevylučovat


def test_match_committee_academic_year_excludes_namesake_same_calendar_year() -> None:
    """Jmenovec s obhajobou v červnu 2025 (kalendářní rok 2025 je v „2025/2026",
    ale akademický rok je 2024/2025) se vyřadí i bez data slotu — díky kontrole
    akademického roku z CELÉHO data. Fiktivní data."""
    from types import SimpleNamespace

    from bpdpmanager.services.stag_api import StagThesisResult

    results = [
        StagThesisResult(adipidno="OLD", surname="Nováková", name="Jana",
                         type_label="diplomová", year="2025",
                         defense_date="04.06.2025", status_code="DUO"),
        StagThesisResult(adipidno="CUR", surname="Nováková", name="Jana",
                         type_label="diplomová", year="", defense_date="",
                         status_code="DBPOO"),
    ]
    # Slot i komise BEZ konkrétních dat → rok by spadl na „2025/2026"; jmenovce
    # z června 2025 vyřadí až kontrola akademického roku.
    slot = SimpleNamespace(student_name="Jana Nováková", date="")
    com = SimpleNamespace(level="Mgr", academic_year="2025/2026", dates=[])
    m = chk._match_committee_result(results, slot, com)
    assert m is not None and m.adipidno == "CUR" and m.status_code == "DBPOO"


def test_compute_uses_explicit_surname(service, monkeypatch) -> None:
    """Hledání nových prací bere EXPLICITNÍ příjmení z profilu (přesné i
    u dvojího jména); prázdné = fallback na poslední token celého jména."""
    seen: list[str] = []

    monkeypatch.setattr(chk, "_fetch_target_state", lambda adip: ("", [], ""))

    def fake_search(student, person, role):
        seen.append(person)
        return []

    monkeypatch.setattr(chk.stag_api, "search_theses", fake_search)

    # Explicitní příjmení → hledá se „Komínková Oplatková", ne jen „Oplatková".
    seen.clear()
    chk.compute_stag_check(service, "Zuzana Komínková Oplatková",
                           "Komínková Oplatková")
    assert seen and all(p == "Komínková Oplatková" for p in seen)

    # Bez explicitního → fallback na poslední token.
    seen.clear()
    chk.compute_stag_check(service, "Zuzana Komínková Oplatková", "")
    assert seen and all(p == "Oplatková" for p in seen)


def test_change_keyset_detects_new() -> None:
    """change_keyset rozliší, co přibylo (pro re-show proužku po další kontrole)."""
    a = chk.StagCheckResult(ok=True, supervised_ids=["t1"], opposing_ids=["o1"])
    b = chk.StagCheckResult(ok=True, supervised_ids=["t1"], opposing_ids=["o1", "o2"])
    assert b.change_keyset() - a.change_keyset() == {"o2"}
    assert not (a.change_keyset() - b.change_keyset())
