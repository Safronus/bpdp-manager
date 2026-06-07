"""Filtr stavů v záložce Historie — checkboxy + perzistence napříč restartem."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from bpdpmanager.models.enums import STATUSES_HISTORY, ThesisStatus
from bpdpmanager.services import ThesisService
from bpdpmanager.storage import JsonRepository
from bpdpmanager.ui.main_window import _ThesesTab


@pytest.fixture(scope="module")
def qapp():
    yield QApplication.instance() or QApplication([])


@pytest.fixture
def service(tmp_path: Path) -> ThesisService:
    repo = JsonRepository(path=tmp_path / "db.json", backup_path=tmp_path / "db.json.bak")
    return ThesisService(repo)


class FakePM:
    """Minimální náhrada ProfileManageru — drží UI předvolby v paměti."""

    def __init__(self) -> None:
        self.prefs: dict = {}

    def get_ui_pref(self, key, default=None):
        return self.prefs.get(key, default)

    def set_ui_pref(self, key, value) -> None:
        self.prefs[key] = value


def _history_tab(service, pm) -> _ThesesTab:
    return _ThesesTab(
        service,
        lambda t: t.status in STATUSES_HISTORY,
        profile_manager=pm,
        status_filter_choices=[ThesisStatus.DEFENDED, ThesisStatus.CANCELLED],
        status_filter_pref_key="history_status_filter",
    )


def test_default_all_checked(qapp, service) -> None:
    tab = _history_tab(service, FakePM())
    assert all(cb.isChecked() for cb in tab._status_checks.values())


def test_uncheck_persists_and_filters(qapp, service) -> None:
    pm = FakePM()
    tab = _history_tab(service, pm)
    # Odškrtni „Nedokončeno" → uloží se jen DEFENDED.
    tab._status_checks[ThesisStatus.CANCELLED].setChecked(False)
    assert pm.prefs["history_status_filter"] == [ThesisStatus.DEFENDED.value]

    # Filtr stromu nyní propustí jen obhájené.
    pred = tab.tree._filter_predicate

    class T:
        def __init__(self, status):
            self.status = status

    assert pred(T(ThesisStatus.DEFENDED)) is True
    assert pred(T(ThesisStatus.CANCELLED)) is False


def test_restore_from_saved_pref(qapp, service) -> None:
    pm = FakePM()
    pm.prefs["history_status_filter"] = [ThesisStatus.CANCELLED.value]
    tab = _history_tab(service, pm)
    assert tab._status_checks[ThesisStatus.DEFENDED].isChecked() is False
    assert tab._status_checks[ThesisStatus.CANCELLED].isChecked() is True
