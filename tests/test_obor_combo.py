"""Testy editace oboru přes combobox (vedené práce → student; oponentury)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from bpdpmanager.models import Obor, Student, Thesis  # noqa: E402
from bpdpmanager.models.enums import ThesisStatus, ThesisType  # noqa: E402
from bpdpmanager.services import ThesisService  # noqa: E402
from bpdpmanager.storage import JsonRepository  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    yield QApplication.instance() or QApplication([])


@pytest.fixture
def service(tmp_path: Path) -> ThesisService:
    repo = JsonRepository(path=tmp_path / "db.json", backup_path=tmp_path / "db.json.bak")
    svc = ThesisService(repo)
    svc.upsert_obor(Obor(name="ITA-P", stag_code="pbITA"))
    return svc


def test_thesis_detail_obor_loads_and_saves(qapp, service: ThesisService) -> None:
    from bpdpmanager.ui.thesis_detail import ThesisDetail

    student = Student(first_name="Jan", last_name="Novák", obor="ITA-P", university_id="A1")
    service.upsert_student(student)
    t = Thesis(type=ThesisType.BP, academic_year="2024/2025", student_id=student.id,
               status=ThesisStatus.IN_PROGRESS)
    service.upsert_thesis(t)

    det = ThesisDetail(service)
    det.set_thesis(t)
    # Načetl obor studenta
    assert det.cb_thesis_obor.currentText() == "ITA-P"
    # Dropdown nabízí evidovaný obor
    items = [det.cb_thesis_obor.itemText(i) for i in range(det.cb_thesis_obor.count())]
    assert "ITA-P" in items

    # Změna oboru → flush → uloží se ke studentovi
    det.cb_thesis_obor.setCurrentText("NSWI-K")
    det.flush()
    assert service.get_student(student.id).obor == "NSWI-K"

    # (Oponentury už editovatelný obor combo nemají — Detail záložka zrušena;
    #  obor se u oponentur plní importem ze STAG.)
