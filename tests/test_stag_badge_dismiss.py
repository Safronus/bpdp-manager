"""Test: zavření STAG proužku smaže odznak 🔄 na záložkách."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from bpdpmanager.services import ThesisService
from bpdpmanager.storage import JsonRepository
from bpdpmanager.ui.main_window import MainWindow


@pytest.fixture(scope="module")
def qapp():
    yield QApplication.instance() or QApplication([])


@pytest.fixture
def service(tmp_path: Path) -> ThesisService:
    repo = JsonRepository(path=tmp_path / "db.json", backup_path=tmp_path / "db.json.bak")
    return ThesisService(repo)


def test_dismiss_banner_clears_tab_badge(qapp, service) -> None:
    win = MainWindow(service)
    win._stag_badges[id(win.tab_current)] = 3
    win._refresh_tab_labels()
    idx = win.tabs.indexOf(win.tab_current)
    assert "🔄" in win.tabs.tabText(idx)

    win._dismiss_stag_banner()
    assert "🔄" not in win.tabs.tabText(idx)
    assert not any(win._stag_badges.values())
