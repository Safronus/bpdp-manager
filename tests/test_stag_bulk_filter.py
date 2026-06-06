"""Testy hromadného STAG importu — filtr dle celého jména + řazení dle roku."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from bpdpmanager.services import stag_api  # noqa: E402
from bpdpmanager.ui.stag_import_dialog import (  # noqa: E402
    StagDownloadDialog,
    _name_matches,
)


@pytest.fixture(scope="module")
def qapp():
    yield QApplication.instance() or QApplication([])


def test_name_matches() -> None:
    assert _name_matches("Ing. Petr Žáček, Ph.D.", "Petr Žáček") is True
    assert _name_matches("Ing. Pavel Žáček, Ph.D.", "Petr Žáček") is False
    assert _name_matches("Petr Zacek", "Petr Žáček") is True       # bez diakritiky
    assert _name_matches("kdokoliv", "Žáček") is True              # jen příjmení → nefiltruj


def _res(adip, supervisor, year):
    return stag_api.StagThesisResult(
        adipidno=adip, surname="S" + adip, name="N", title="T",
        supervisor=supervisor, year=year,
    )


def _leaf_adips(dlg) -> list[str]:
    """Posbírá adipidno listových položek stromu v zobrazeném pořadí."""
    out: list[str] = []

    def walk(item) -> None:
        for i in range(item.childCount()):
            walk(item.child(i))
        adip = item.data(0, 0x0100)  # Qt.UserRole
        if adip:
            out.append(adip)

    root = dlg.tree_results.invisibleRootItem()
    for i in range(root.childCount()):
        walk(root.child(i))
    return out


def test_render_filters_by_full_name_and_sorts(qapp) -> None:
    dlg = StagDownloadDialog(
        default_person_surname="Žáček", service=None,
        auto_role="supervisor", user_full_name="Petr Žáček",
    )
    dlg._enrich_visible = lambda: None  # bez síťového dotažení v testu
    dlg._results = [
        _res("1", "Petr Žáček", "2022"),
        _res("2", "Pavel Žáček", "2024"),   # jiný jmenovec → odfiltrovat
        _res("3", "Petr Žáček", "2025"),
    ]
    dlg._render_results()
    # Jen moje (filtr zapnutý) → 2 práce.
    adips = _leaf_adips(dlg)
    assert len(adips) == 2
    # Řazení dle roku sestupně → první je 2025 (adip 3).
    assert adips[0] == "3"

    # Vypnu filtr → všechny 3.
    dlg.chk_only_mine.setChecked(False)
    assert len(_leaf_adips(dlg)) == 3
