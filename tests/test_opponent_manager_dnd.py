"""Test přesunu oponenta mezi Interní / Externí (drag&drop handler)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from bpdpmanager.models import Opponent
from bpdpmanager.models.enums import OpponentKind
from bpdpmanager.services import ThesisService
from bpdpmanager.storage import JsonRepository
from bpdpmanager.ui.manage_dialogs import OpponentsManageDialog


@pytest.fixture(scope="module")
def qapp():
    yield QApplication.instance() or QApplication([])


@pytest.fixture
def service(tmp_path: Path) -> ThesisService:
    repo = JsonRepository(path=tmp_path / "db.json", backup_path=tmp_path / "db.json.bak")
    return ThesisService(repo)


def test_move_opponent_changes_kind(qapp, service) -> None:
    o = Opponent(name="Jan Novák", kind=OpponentKind.INTERNAL)
    service.upsert_opponent(o)

    dlg = OpponentsManageDialog(service)
    dlg._move_opponent(o, OpponentKind.EXTERNAL.value)

    assert service.get_opponent(o.id).kind == OpponentKind.EXTERNAL
    # Skupiny ve stromu nesou svůj kind (cíl drop) v ROLE.
    from bpdpmanager.ui.manage_dialogs import _ROLE_GROUP_KIND

    kinds = {
        dlg.tree.topLevelItem(i).data(0, _ROLE_GROUP_KIND)
        for i in range(dlg.tree.topLevelItemCount())
    }
    assert OpponentKind.INTERNAL.value in kinds
    assert OpponentKind.EXTERNAL.value in kinds
