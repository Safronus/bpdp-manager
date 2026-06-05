"""Testy manažeru Obory + sekretářky — seskupení, sloupec oslovení, hromadná úprava."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from bpdpmanager.models import Obor  # noqa: E402
from bpdpmanager.services import ThesisService  # noqa: E402
from bpdpmanager.storage import JsonRepository  # noqa: E402
from bpdpmanager.ui.manage_dialogs import OboryManageDialog  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    yield QApplication.instance() or QApplication([])


@pytest.fixture
def service(tmp_path: Path) -> ThesisService:
    repo = JsonRepository(path=tmp_path / "db.json", backup_path=tmp_path / "db.json.bak")
    svc = ThesisService(repo)
    for o in list(svc.list_obor_objects()):
        svc.remove_obor(o.name)
    return svc


def test_group_shows_greeting_column(qapp, service: ThesisService) -> None:
    service.upsert_obor(Obor(name="ITA-P", secretary_name="Nováková",
                             secretary_email="s@utb.cz",
                             secretary_greeting="Vážená paní Nováková"))
    service.upsert_obor(Obor(name="ITA-K", secretary_name="Nováková",
                             secretary_email="s@utb.cz"))
    dlg = OboryManageDialog(service)
    assert dlg.tree.columnCount() == 5
    top = dlg.tree.topLevelItem(0)
    assert "Nováková" in top.text(0)
    assert top.text(4) == "Vážená paní Nováková"  # sloupec Oslovení
    assert top.childCount() == 2


def test_bulk_apply_secretary(qapp, service: ThesisService) -> None:
    service.upsert_obor(Obor(name="A", secretary_name="X", secretary_email="x@utb.cz"))
    service.upsert_obor(Obor(name="B", secretary_name="X", secretary_email="x@utb.cz"))
    dlg = OboryManageDialog(service)
    obory = [o for o in service.list_obor_objects()]
    dlg._apply_secretary_to_group(obory, "Y", "y@utb.cz", "+420 1", "Milá Y")

    for o in service.list_obor_objects():
        assert o.secretary_name == "Y"
        assert o.secretary_email == "y@utb.cz"
        assert o.secretary_greeting == "Milá Y"
