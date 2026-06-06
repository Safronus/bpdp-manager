"""Testy návrhů témat (ThesisProposal) — model, service CRUD, převod, záložka."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QMessageBox

from bpdpmanager.models import ThesisProposal
from bpdpmanager.models.enums import ThesisStatus, ThesisType
from bpdpmanager.services import ThesisService
from bpdpmanager.storage import JsonRepository
from bpdpmanager.storage.repository import Database
from bpdpmanager.ui.proposals_tab import ProposalsTab


@pytest.fixture(scope="module")
def qapp():
    yield QApplication.instance() or QApplication([])


@pytest.fixture
def service(tmp_path: Path) -> ThesisService:
    repo = JsonRepository(path=tmp_path / "db.json", backup_path=tmp_path / "db.json.bak")
    return ThesisService(repo)


def test_proposal_defaults() -> None:
    p = ThesisProposal(title_cs="Téma")
    assert p.type == ThesisType.BP
    assert p.reserved is False
    assert p.id and p.created_at


def test_old_db_without_proposals_loads() -> None:
    """Starší úložiště bez klíče proposals se načte (default = prázdný list)."""
    db = Database.model_validate({"version": 11, "obory": []})
    assert db.proposals == []


def test_service_crud(service: ThesisService) -> None:
    p = ThesisProposal(type=ThesisType.DP, title_cs="Návrh", obor="pbSWI")
    service.upsert_proposal(p)
    assert [x.id for x in service.list_proposals()] == [p.id]
    assert service.get_proposal(p.id).title_cs == "Návrh"
    p.title_cs = "Upravený"
    service.upsert_proposal(p)
    assert service.get_proposal(p.id).title_cs == "Upravený"
    service.delete_proposal(p.id)
    assert service.list_proposals() == []


def test_convert_to_thesis(service: ThesisService) -> None:
    p = ThesisProposal(
        type=ThesisType.DP, title_cs="Skvělé téma", description="Popis",
        objectives="a\nb", references="kniha", obor="pbSWI",
    )
    service.upsert_proposal(p)
    thesis = service.convert_proposal_to_thesis(p.id)

    # Návrh zmizel, práce vznikla s přenesenými poli.
    assert service.get_proposal(p.id) is None
    t = service.get_thesis(thesis.id)
    assert t is not None
    assert t.type == ThesisType.DP
    assert t.title_cs == "Skvělé téma"
    assert t.annotation == "Popis"
    assert t.objectives == "a\nb"
    assert t.references == "kniha"
    assert t.status == ThesisStatus.RESERVED
    assert t.academic_year  # aktuální rok doplněn


def test_tab_create_edit_save(qapp, service: ThesisService) -> None:
    tab = ProposalsTab(service)
    tab._new_proposal()
    pid = tab.current_id
    assert pid is not None

    tab.ed_title.setText("Můj návrh")
    tab.cmb_type.setCurrentIndex(tab.cmb_type.findData("DP"))
    tab.cmb_obor.setEditText("pbKYB")
    tab.chk_reserved.setChecked(True)
    tab.ed_reserved_for.setText("Novák")
    tab._save()

    p = service.get_proposal(pid)
    assert p.title_cs == "Můj návrh"
    assert p.type == ThesisType.DP
    assert p.obor == "pbKYB"
    assert p.reserved is True
    assert p.reserved_for == "Novák"


def test_tab_convert_emits_signal(qapp, service: ThesisService, monkeypatch) -> None:
    monkeypatch.setattr(
        QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes
    )
    tab = ProposalsTab(service)
    tab._new_proposal()
    pid = tab.current_id
    tab.ed_title.setText("K převodu")
    tab._save()

    emitted: list[str] = []
    tab.converted.connect(emitted.append)
    tab._convert()

    assert service.get_proposal(pid) is None
    assert len(emitted) == 1
    assert service.get_thesis(emitted[0]) is not None
