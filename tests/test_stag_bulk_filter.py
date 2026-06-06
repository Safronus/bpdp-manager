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


def test_render_filters_by_full_name_and_sorts(qapp) -> None:
    dlg = StagDownloadDialog(
        default_person_surname="Žáček", service=None,
        auto_role="supervisor", user_full_name="Petr Žáček",
    )
    dlg._results = [
        _res("1", "Petr Žáček", "2022"),
        _res("2", "Pavel Žáček", "2024"),   # jiný jmenovec → odfiltrovat
        _res("3", "Petr Žáček", "2025"),
    ]
    dlg._render_results()
    # Jen moje (filtr zapnutý) → 2 práce.
    assert dlg.list_results.count() == 2
    # Řazení dle roku sestupně → první je 2025 (adip 3).
    assert dlg.list_results.item(0).data(0x0100) == "3"  # Qt.UserRole = 0x0100

    # Vypnu filtr → všechny 3.
    dlg.chk_only_mine.setChecked(False)
    assert dlg.list_results.count() == 3
