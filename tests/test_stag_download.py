"""Testy stahování ze STAG — varování u velkých příloh (regrese _cs_plural)."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QMessageBox

import bpdpmanager.ui.stag_import_dialog as mod
from bpdpmanager.services import stag_api
from bpdpmanager.ui.stag_import_dialog import StagDownloadDialog


@pytest.fixture(scope="module")
def qapp():
    yield QApplication.instance() or QApplication([])


def _dialog():
    dlg = StagDownloadDialog(service=None)
    dlg._enrich_visible = lambda: None
    return dlg


def _big():
    return stag_api.StagFile(
        soubidno="9", filename="velky_text.pdf", download_path="/big",
        section="text", size_hint=mod._LARGE_FILE_BYTES + 1,
    )


def _small():
    return stag_api.StagFile(
        soubidno="1", filename="posudek.pdf", download_path="/small",
        section="supervisor_review", size_hint=2048,
    )


def test_confirm_oversized_skip(qapp, monkeypatch) -> None:
    """Klik na „Přeskočit velké" → vrátí soubidno velké přílohy (žádný crash)."""
    dlg = _dialog()
    captured: dict = {}

    def fake_exec(self_msg):
        for b in self_msg.buttons():
            if "Přeskočit" in b.text():
                captured["b"] = b
        return 0

    monkeypatch.setattr(QMessageBox, "exec", fake_exec)
    monkeypatch.setattr(QMessageBox, "clickedButton", lambda self: captured.get("b"))

    skip = dlg._confirm_oversized({"42": [_big(), _small()]})
    assert skip == {"9"}


def test_confirm_oversized_download_anyway(qapp, monkeypatch) -> None:
    """Klik na „Stáhnout i tak" → prázdná množina (nic se nepřeskočí)."""
    dlg = _dialog()
    monkeypatch.setattr(QMessageBox, "exec", lambda self: 0)
    monkeypatch.setattr(QMessageBox, "clickedButton", lambda self: None)
    assert dlg._confirm_oversized({"42": [_big()]}) == set()


def test_confirm_oversized_no_big_no_dialog(qapp, monkeypatch) -> None:
    """Bez velkých příloh se dialog vůbec nevyvolá a vrátí prázdnou množinu."""
    dlg = _dialog()

    def boom(self):  # dialog se nesmí otevřít
        raise AssertionError("QMessageBox se neměl zobrazit")

    monkeypatch.setattr(QMessageBox, "exec", boom)
    assert dlg._confirm_oversized({"42": [_small()]}) == set()
