"""Testy: adipidno (STAG ID) na pracích + odznaky 'nové/už máš' v download dialogu.

Bez sítě — testuje jen perzistenci a anotační logiku.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from bpdpmanager.models import OpposingThesis, Student, Thesis  # noqa: E402
from bpdpmanager.models.enums import ThesisType  # noqa: E402
from bpdpmanager.services import ThesisService  # noqa: E402
from bpdpmanager.services.stag_api import StagThesisResult  # noqa: E402
from bpdpmanager.storage import JsonRepository  # noqa: E402
from bpdpmanager.ui.stag_import_dialog import StagDownloadDialog  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def service(tmp_path: Path) -> ThesisService:
    repo = JsonRepository(path=tmp_path / "db.json", backup_path=tmp_path / "db.json.bak")
    return ThesisService(repo)


def test_adipidno_persists_on_thesis(service: ThesisService) -> None:
    t = Thesis(type=ThesisType.BP, academic_year="2025/2026", adipidno="12345")
    service.upsert_thesis(t)
    assert service.get_thesis(t.id).adipidno == "12345"

    op = OpposingThesis(type=ThesisType.DP, academic_year="2025/2026", adipidno="999")
    service.upsert_opposing_thesis(op)
    assert service.get_opposing_thesis(op.id).adipidno == "999"


def test_result_type_code() -> None:
    f = StagDownloadDialog._result_type_code
    assert f(StagThesisResult(adipidno="1", type_label="Diplomová práce")) == "DP"
    assert f(StagThesisResult(adipidno="1", type_label="Bakalářská práce")) == "BP"
    assert f(StagThesisResult(adipidno="1", type_label="")) == ""


def test_existing_badges_by_adipidno_and_name(qapp, service: ThesisService) -> None:
    # V DB: student Hřešilová, BP s adipidno=111
    student = Student(first_name="Veronika", last_name="Hřešilová")
    service.upsert_student(student)
    service.upsert_thesis(Thesis(
        type=ThesisType.BP, academic_year="2025/2026",
        student_id=student.id, adipidno="111",
    ))

    dlg = StagDownloadDialog(service=service)
    adip, name_type = dlg._existing_keys()
    assert "111" in adip
    assert ("veronika hřešilová", "BP") in name_type

    # stejná BP (adipidno) → už máš
    r_same = StagThesisResult(adipidno="111", surname="Hřešilová", name="Veronika",
                              type_label="Bakalářská práce", year="2025")
    assert dlg._is_existing(r_same, adip, name_type) is True

    # nová DP téhož studenta (jiné adipidno, jiný typ) → nové
    r_dp = StagThesisResult(adipidno="222", surname="Hřešilová", name="Veronika",
                            type_label="Diplomová práce", year="2026")
    assert dlg._is_existing(r_dp, adip, name_type) is False

    # BP téhož studenta bez adipidno, ale shoda jméno+typ → už máš (heuristika)
    r_bp_noid = StagThesisResult(adipidno="333", surname="Hřešilová", name="Veronika",
                                 type_label="Bakalářská práce", year="2025")
    assert dlg._is_existing(r_bp_noid, adip, name_type) is True


def test_search_populates_checkable_list(qapp, service: ThesisService, monkeypatch) -> None:
    # V DB existuje BP s adipidno=111 → ve výsledcích bude „už máš" (neoznačená),
    # DP (222) bude „nové" (předzaškrtnutá).
    student = Student(first_name="Veronika", last_name="Hřešilová")
    service.upsert_student(student)
    service.upsert_thesis(Thesis(
        type=ThesisType.BP, academic_year="2025/2026",
        student_id=student.id, adipidno="111",
    ))

    import bpdpmanager.ui.stag_import_dialog as mod

    def fake_search(student_surname, person_surname, role):
        return [
            StagThesisResult(adipidno="111", surname="Hřešilová", name="Veronika",
                             type_label="Bakalářská práce", year="2025"),
            StagThesisResult(adipidno="222", surname="Hřešilová", name="Veronika",
                             type_label="Diplomová práce", year="2026"),
        ]

    monkeypatch.setattr(mod.stag_api, "search_theses", fake_search)

    dlg = StagDownloadDialog(service=service)
    dlg.ed_student.setText("Hřešilová")
    dlg._do_search()

    from PySide6.QtCore import Qt
    assert dlg.list_results.count() == 2
    states = {
        dlg.list_results.item(i).data(Qt.ItemDataRole.UserRole):
        dlg.list_results.item(i).checkState()
        for i in range(2)
    }
    assert states["111"] == Qt.CheckState.Unchecked  # už máš
    assert states["222"] == Qt.CheckState.Checked     # nové, předzaškrtnuté
    # jen nové je ve vybraných ke stažení
    checked = {r.adipidno for r in dlg._checked_results()}
    assert checked == {"222"}
