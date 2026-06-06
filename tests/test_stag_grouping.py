"""Testy seskupení výsledků STAG (combo) + dotažení akad. roku/oboru z CSV."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from bpdpmanager.services import stag_api
from bpdpmanager.services.stag_csv_importer import load_stag_csv_bytes
from bpdpmanager.ui.stag_import_dialog import (
    StagDownloadDialog,
    _fetch_stag_meta,
    _invert_year,
)


@pytest.fixture(scope="module")
def qapp():
    yield QApplication.instance() or QApplication([])


def _r(adip, year, status, typ, obor="", ay=""):
    return stag_api.StagThesisResult(
        adipidno=adip, surname="S" + adip, name="N", title="T",
        type_label=typ, year=year, status_code=status, obor=obor, academic_year=ay,
    )


def _dialog(qapp):
    dlg = StagDownloadDialog(service=None)
    dlg._enrich_visible = lambda: None  # žádná síť v testu
    return dlg


def _headers(dlg) -> list[str]:
    root = dlg.tree_results.invisibleRootItem()
    return [root.child(i).text(0) for i in range(root.childCount())]


def _set_mode(dlg, key) -> None:
    for i in range(dlg.cmb_group.count()):
        if dlg.cmb_group.itemData(i) == key:
            dlg.cmb_group.setCurrentIndex(i)
            return
    raise AssertionError(f"režim {key!r} nenalezen")


def test_group_by_type_orders_bp_before_dp(qapp) -> None:
    dlg = _dialog(qapp)
    dlg._results = [
        _r("1", "2023", "DUO", "Bakalářská práce"),
        _r("2", "2024", "DUO", "Diplomová práce"),
        _r("3", "2022", "ND", "Bakalářská práce"),
    ]
    _set_mode(dlg, "typ")
    headers = _headers(dlg)
    assert headers[0].startswith("Bakalářské práce") and "(2)" in headers[0]
    assert headers[1].startswith("Diplomové práce") and "(1)" in headers[1]


def test_group_by_obor(qapp) -> None:
    dlg = _dialog(qapp)
    dlg._results = [
        _r("1", "2023", "DUO", "Bakalářská práce", obor="pbSWI"),
        _r("2", "2022", "ND", "Bakalářská práce", obor="pbKYB"),
    ]
    _set_mode(dlg, "obor")
    headers = _headers(dlg)
    assert any(h.startswith("pbKYB") for h in headers)
    assert any(h.startswith("pbSWI") for h in headers)


def test_group_by_year_newest_first(qapp) -> None:
    dlg = _dialog(qapp)
    dlg._results = [
        _r("1", "2019", "ND", "Bakalářská práce", ay="2018/2019"),
        _r("2", "2023", "DUO", "Bakalářská práce", ay="2022/2023"),
    ]
    _set_mode(dlg, "rok")
    headers = _headers(dlg)
    assert headers[0].startswith("2022/2023")  # nejnovější první
    assert headers[1].startswith("2018/2019")


def test_group_none_is_flat(qapp) -> None:
    dlg = _dialog(qapp)
    dlg._results = [
        _r("1", "2023", "DUO", "Bakalářská práce"),
        _r("2", "2024", "DUO", "Diplomová práce"),
    ]
    _set_mode(dlg, "none")
    root = dlg.tree_results.invisibleRootItem()
    # top-level položky jsou listy (mají adipidno), žádné hlavičky skupin
    adips = {
        root.child(i).data(0, Qt.ItemDataRole.UserRole)
        for i in range(root.childCount())
    }
    assert adips == {"1", "2"}


def test_group_header_toggle_propagates_to_children(qapp) -> None:
    dlg = _dialog(qapp)
    dlg._results = [
        _r("1", "2023", "DUO", "Bakalářská práce"),
        _r("2", "2024", "DUO", "Diplomová práce"),
    ]
    _set_mode(dlg, "typ")
    root = dlg.tree_results.invisibleRootItem()
    bp_header = root.child(0)  # bakalářské první
    bp_header.setCheckState(0, Qt.CheckState.Unchecked)
    for i in range(bp_header.childCount()):
        assert bp_header.child(i).checkState(0) == Qt.CheckState.Unchecked
    checked = {r.adipidno for r in dlg._checked_results()}
    assert "1" not in checked  # BP odškrtnuto
    assert "2" in checked       # DP zůstalo


def test_invert_year_orders_newest_first() -> None:
    assert _invert_year("2022/2023") < _invert_year("2018/2019")
    assert _invert_year("") == "9999"


def test_fetch_stag_meta_parses_year_and_obor(qapp, monkeypatch) -> None:
    csv_bytes = (
        "osCislo.student;typPrace;datumZadani;oborKombinaceStudenta\r\n"
        "A12345;Bakalářská práce;15.11.2018;knBT-M\r\n"
    ).encode()
    import bpdpmanager.ui.stag_import_dialog as mod
    monkeypatch.setattr(mod.stag_api, "download_csv", lambda adip: csv_bytes)
    ay, obor = _fetch_stag_meta("999")
    assert ay == "2018/2019"
    assert obor == "knBT-M"


def test_fetch_stag_meta_swallows_errors(qapp, monkeypatch) -> None:
    import bpdpmanager.ui.stag_import_dialog as mod

    def boom(adip):
        raise stag_api.StagError("síť")

    monkeypatch.setattr(mod.stag_api, "download_csv", boom)
    assert _fetch_stag_meta("999") == ("", "")


def test_load_stag_csv_bytes_basic() -> None:
    csv_bytes = (
        "osCislo.student;typPrace;datumZadani;oborKombinaceStudenta\r\n"
        "A12345;Diplomová práce;01.03.2020;pmSWI\r\n"
    ).encode()
    imp = load_stag_csv_bytes(csv_bytes)
    assert imp.records
    rec = imp.records[0]
    assert rec.student_obor_stag == "pmSWI"
    assert rec.academic_year == "2019/2020"
