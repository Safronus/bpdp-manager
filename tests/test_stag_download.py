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


def _result(adip="1"):
    return stag_api.StagThesisResult(
        adipidno=adip, surname="A", name="B", title="T",
        type_label="Bakalářská práce", status_code="DUO",
    )


def _cell_text(dlg, adip, col):
    root = dlg.tree_results.invisibleRootItem()
    found = []

    def walk(item):
        for i in range(item.childCount()):
            walk(item.child(i))
        if item.data(0, 0x0100) == adip:
            found.append(item.text(col))

    for i in range(root.childCount()):
        walk(root.child(i))
    return found[0] if found else None


def test_attachments_lazy_fill(qapp, monkeypatch) -> None:
    """Po zaškrtnutí práce se dotáhne počet + velikost příloh do sloupce."""
    monkeypatch.setattr(mod.stag_api, "list_thesis_files", lambda a: [_big(), _small()])
    dlg = _dialog()
    dlg._results = [_result("1")]
    dlg._render_results()
    assert _cell_text(dlg, "1", mod._ATTACH_COL) == ""   # zatím nezjištěno
    dlg._fetch_attachments(["1"])
    assert dlg._attach_info["1"] == (2, mod._LARGE_FILE_BYTES + 1 + 2048)
    assert _cell_text(dlg, "1", mod._ATTACH_COL).startswith("📎 2")


def test_attachments_error_shows_question_mark(qapp, monkeypatch) -> None:
    """Chyba při zjišťování příloh → „?" a nezakešuje se (jde zkusit znovu)."""
    def boom(adip):
        raise stag_api.StagError("síť")

    monkeypatch.setattr(mod.stag_api, "list_thesis_files", boom)
    dlg = _dialog()
    dlg._results = [_result("1")]
    dlg._render_results()
    dlg._fetch_attachments(["1"])
    assert "1" not in dlg._attach_info
    assert _cell_text(dlg, "1", mod._ATTACH_COL) == "?"
