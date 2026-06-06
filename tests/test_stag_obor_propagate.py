"""Test: vytvoření nového oboru se propíše do dalších řádků se stejným STAG kódem."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QComboBox

from bpdpmanager.models import Obor
from bpdpmanager.services import ThesisService
from bpdpmanager.services.stag_csv_importer import ImportRole, ParsedRecord
from bpdpmanager.storage import JsonRepository
from bpdpmanager.ui.stag_import_dialog import StagImportDialog


@pytest.fixture(scope="module")
def qapp():
    yield QApplication.instance() or QApplication([])


@pytest.fixture
def service(tmp_path: Path) -> ThesisService:
    repo = JsonRepository(path=tmp_path / "db.json", backup_path=tmp_path / "db.json.bak")
    return ThesisService(repo)


def _unmapped_combo(stag: str) -> QComboBox:
    cb = QComboBox()
    cb.addItem(f"⚠ Nemapováno — uložit jako '{stag}'", "__keep__")
    cb.addItem("➕ Nový obor…", "__new__")
    cb.setCurrentIndex(0)
    return cb


def _record(stag: str) -> ParsedRecord:
    r = ParsedRecord(role=ImportRole.SUPERVISOR)
    r.student_obor_stag = stag
    return r


def test_new_obor_propagates_to_same_stag_rows(qapp, service) -> None:
    dlg = StagImportDialog(service, None)
    dlg.row_widgets = [
        {"cb_obor": _unmapped_combo("pbSWI"), "record": _record("pbSWI")},
        {"cb_obor": _unmapped_combo("pbSWI"), "record": _record("pbSWI")},
        {"cb_obor": _unmapped_combo("pbKYB"), "record": _record("pbKYB")},
    ]
    # Uživatel založí nový obor pro pbSWI (z 1. řádku).
    new = Obor(name="Softwarové inženýrství", stag_code="pbSWI")
    service.upsert_obor(new)
    trigger = dlg.row_widgets[0]["cb_obor"]
    dlg._propagate_new_obor(new, trigger)

    # Oba pbSWI řádky se rovnou namapují na nový obor…
    assert dlg.row_widgets[0]["cb_obor"].currentData() == "Softwarové inženýrství"
    assert dlg.row_widgets[1]["cb_obor"].currentData() == "Softwarové inženýrství"
    # …ale řádek s jiným STAG kódem zůstane nenamapovaný.
    assert dlg.row_widgets[2]["cb_obor"].currentData() == "__keep__"
    # Nový obor je přesto nabízen i v tom řádku (k ruční volbě).
    assert dlg.row_widgets[2]["cb_obor"].findData("Softwarové inženýrství") >= 0


def test_propagate_keeps_existing_manual_choice(qapp, service) -> None:
    """Řádek už ručně namapovaný na jiný obor se propagací nezmění."""
    service.add_obor("Kybernetika")
    dlg = StagImportDialog(service, None)

    mapped = QComboBox()
    mapped.addItem("⚠ Nemapováno — uložit jako 'pbSWI'", "__keep__")
    mapped.addItem("Kybernetika", "Kybernetika")
    mapped.addItem("➕ Nový obor…", "__new__")
    mapped.setCurrentIndex(1)  # ručně zvolená Kybernetika

    dlg.row_widgets = [
        {"cb_obor": _unmapped_combo("pbSWI"), "record": _record("pbSWI")},
        {"cb_obor": mapped, "record": _record("pbSWI")},
    ]
    new = Obor(name="Softwarové inženýrství", stag_code="pbSWI")
    service.upsert_obor(new)
    dlg._propagate_new_obor(new, dlg.row_widgets[0]["cb_obor"])

    assert dlg.row_widgets[0]["cb_obor"].currentData() == "Softwarové inženýrství"
    # Ruční volba zůstává.
    assert dlg.row_widgets[1]["cb_obor"].currentData() == "Kybernetika"
