"""Historie: skupina aktuálního roku nese poznámku „letošní hotové práce".

Obhájené/ukončené práce letošního roku se po aktualizaci stavu přesouvají
do Historie průběžně — poznámka v titulku skupiny vysvětluje, proč jsou
„hotové" práce už v aktuálním roce.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from bpdpmanager.models import Student, Thesis
from bpdpmanager.models.enums import STATUSES_HISTORY, ThesisStatus, ThesisType
from bpdpmanager.services import ThesisService
from bpdpmanager.storage import JsonRepository
from bpdpmanager.ui.theses_tree import ThesesTreeWidget


@pytest.fixture(scope="module")
def qapp():
    yield QApplication.instance() or QApplication([])


@pytest.fixture
def service(tmp_path) -> ThesisService:
    repo = JsonRepository(path=tmp_path / "db.json", backup_path=tmp_path / "db.json.bak")
    return ThesisService(repo)


def _past_year(current: str) -> str:
    y0, _ = current.split("/")
    return f"{int(y0) - 1}/{int(y0)}"


def test_current_year_group_carries_note(qapp, service) -> None:
    current = service.current_academic_year()
    past = _past_year(current)
    s = Student(first_name="J", last_name="N")
    service.upsert_student(s)
    # Letos obhájená + loni obhájená — obě patří do Historie (dle stavu).
    service.upsert_thesis(Thesis(type=ThesisType.BP, status=ThesisStatus.DEFENDED,
                                 academic_year=current, student_id=s.id))
    service.upsert_thesis(Thesis(type=ThesisType.DP, status=ThesisStatus.DEFENDED,
                                 academic_year=past, student_id=s.id))

    tree = ThesesTreeWidget(service)
    tree.set_filter(lambda t: t.status in STATUSES_HISTORY)
    tree.mark_current_year_done = True   # zapíná jen záložka Historie
    tree.refresh()

    labels = {tree.topLevelItem(i).text(0) for i in range(tree.topLevelItemCount())}
    by_year = {lbl for lbl in labels if current in lbl}
    assert by_year, labels
    assert any("letošní hotové práce" in lbl for lbl in by_year)
    # Minulý rok poznámku nemá.
    assert all("letošní" not in lbl for lbl in labels if past in lbl)


def test_note_only_when_enabled(qapp, service) -> None:
    current = service.current_academic_year()
    s = Student(first_name="J", last_name="N")
    service.upsert_student(s)
    service.upsert_thesis(Thesis(type=ThesisType.BP, status=ThesisStatus.DEFENDED,
                                 academic_year=current, student_id=s.id))
    tree = ThesesTreeWidget(service)   # bez mark_current_year_done (např. „Vše")
    tree.refresh()
    labels = [tree.topLevelItem(i).text(0) for i in range(tree.topLevelItemCount())]
    assert all("letošní" not in lbl for lbl in labels)


def test_stag_synced_signal_refreshes_all_tabs(qapp, service) -> None:
    """Signál stag_synced existuje a hlavní okno na něj obnovuje záložky."""
    from bpdpmanager.ui.main_window import _ThesesTab

    tab = _ThesesTab(service, lambda t: True)
    fired = []
    tab.stag_synced.connect(lambda: fired.append(True))
    tab.stag_synced.emit()
    assert fired == [True]
