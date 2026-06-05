"""Regrese: náhled importu více STAG prací (BP + DP) nesmí spadnout.

Dříve ``_load_preview_from_stag`` konstruoval ``ImportFile`` bez povinného
argumentu ``path`` → ``TypeError`` při stažení BP i DP stejného studenta.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from bpdpmanager.services import ThesisService, stag_api  # noqa: E402
from bpdpmanager.storage import JsonRepository  # noqa: E402
from bpdpmanager.ui.stag_import_dialog import StagImportDialog  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    yield QApplication.instance() or QApplication([])


@pytest.fixture
def service(tmp_path: Path) -> ThesisService:
    repo = JsonRepository(path=tmp_path / "db.json", backup_path=tmp_path / "db.json.bak")
    return ThesisService(repo)


def _write_csv(path: Path, *, typ: str, adip: str, osc: str) -> None:
    header = "osCislo.student;jmeno.student;prijmeni.student;typPrace;adipidno;nazevsCZ"
    row = f"{osc};Jan;Novák;{typ};{adip};Nějaká práce"
    path.write_text(header + "\n" + row + "\n", encoding="utf-8")


def test_preview_merge_bp_and_dp(qapp, service: ThesisService, tmp_path: Path) -> None:
    bp = tmp_path / "stag_Novak_111.csv"
    dp = tmp_path / "stag_Novak_222.csv"
    _write_csv(bp, typ="Bakalářská práce", adip="111", osc="A1")
    _write_csv(dp, typ="Diplomová práce", adip="222", osc="A1")

    items = [
        (bp, stag_api.StagThesisResult(adipidno="111", surname="Novák", name="Jan",
                                       type_label="Bakalářská práce")),
        (dp, stag_api.StagThesisResult(adipidno="222", surname="Novák", name="Jan",
                                       type_label="Diplomová práce")),
    ]

    dlg = StagImportDialog(service)
    dlg._load_preview_from_stag(items)  # dříve vyhodilo TypeError

    assert dlg.import_file is not None
    assert dlg.import_file.path is not None
    assert len(dlg.import_file.records) == 2
    assert {r.adipidno for r in dlg.import_file.records} == {"111", "222"}
