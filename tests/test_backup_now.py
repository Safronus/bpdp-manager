"""Test ručního „Zálohovat teď" v manažeru záloh."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from bpdpmanager.models import Thesis  # noqa: E402
from bpdpmanager.models.enums import ThesisType  # noqa: E402
from bpdpmanager.services import BackupManager, ThesisService  # noqa: E402
from bpdpmanager.storage import JsonRepository  # noqa: E402
from bpdpmanager.ui import backup_dialog  # noqa: E402
from bpdpmanager.ui.backup_dialog import BackupBrowserDialog  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    yield QApplication.instance() or QApplication([])


def test_backup_now_creates_manual_backup(qapp, tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "db.json"
    repo = JsonRepository(path=db_path, backup_path=tmp_path / "db.json.bak")
    svc = ThesisService(repo)
    svc.upsert_thesis(Thesis(type=ThesisType.BP, academic_year="2024/2025"))
    assert db_path.exists()

    bm = BackupManager(tmp_path)
    # Modální okna v testu potlač.
    monkeypatch.setattr(backup_dialog.QMessageBox, "information", lambda *a, **k: None)
    monkeypatch.setattr(backup_dialog.QMessageBox, "warning", lambda *a, **k: None)

    dlg = BackupBrowserDialog(bm, db_path)
    assert bm.list_backups() == []
    dlg._backup_now()
    backups = bm.list_backups()
    assert len(backups) == 1
    assert backups[0].suffix == "manual"

    # Druhá ruční záloha se vytvoří i bez změny (dedupe=False).
    dlg._backup_now()
    assert len(bm.list_backups()) == 2
