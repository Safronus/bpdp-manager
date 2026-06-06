"""Test záchranné brzdy importu — záloha před importem + obnova (revert)."""

from __future__ import annotations

from pathlib import Path

import pytest

from bpdpmanager.models import Thesis
from bpdpmanager.models.enums import ThesisType
from bpdpmanager.services import BackupManager, ThesisService
from bpdpmanager.storage import JsonRepository


@pytest.fixture
def service(tmp_path: Path) -> ThesisService:
    repo = JsonRepository(path=tmp_path / "db.json", backup_path=tmp_path / "db.json.bak")
    return ThesisService(repo)


def test_backup_then_revert_restores_preimport_state(service: ThesisService, tmp_path: Path) -> None:
    # Výchozí stav: jedna práce.
    a = Thesis(type=ThesisType.BP, academic_year="2023/2024", title_cs="Původní")
    service.upsert_thesis(a)
    assert len(service.list_theses()) == 1

    db_path = tmp_path / "db.json"
    bm = BackupManager(tmp_path)
    info = bm.create_backup(db_path, suffix="before-stag-import", dedupe=False)
    assert info is not None
    assert "before-stag-import" in info.path.name

    # „Import" přidá další práce.
    for i in range(3):
        service.upsert_thesis(Thesis(type=ThesisType.DP, academic_year="2024/2025",
                                     title_cs=f"Import {i}"))
    assert len(service.list_theses()) == 4

    # Revert — obnova ze zálohy + reload.
    bm.restore_backup(info.path.name, db_path)
    service.reload()
    titles = [t.title_cs for t in service.list_theses()]
    assert titles == ["Původní"]

    # Před-revertová záloha existuje (importovaný stav lze vrátit zpět).
    assert any("before-restore" in b.path.name for b in bm.list_backups())
