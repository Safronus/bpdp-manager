"""Testy párování prací na sekretářku v dialogu odesílání posudků.

Regrese: oponentské posudky se nezobrazovaly, protože ``student_obor`` bývá
STAG kód (např. „NSWI-K"), ale párovalo se jen proti názvu oboru. Nově se
matchuje proti názvu i STAG kódu.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from bpdpmanager.models import Obor, OpposingThesis, Student, Thesis  # noqa: E402
from bpdpmanager.models.enums import AttachmentKind, ThesisStatus, ThesisType  # noqa: E402
from bpdpmanager.services import ThesisService  # noqa: E402
from bpdpmanager.storage import JsonRepository  # noqa: E402
from bpdpmanager.ui.send_reviews_dialog import SendReviewsDialog  # noqa: E402


class _StubPM:
    """Minimální náhrada ProfileManageru — dialog potřebuje jen ``.active``."""

    active = None


@pytest.fixture(scope="module")
def qapp():
    yield QApplication.instance() or QApplication([])


@pytest.fixture
def service(tmp_path: Path) -> ThesisService:
    repo = JsonRepository(path=tmp_path / "db.json", backup_path=tmp_path / "db.json.bak")
    return ThesisService(repo)


@pytest.fixture
def pm() -> _StubPM:
    return _StubPM()


def _obor_with_secretary(service: ThesisService) -> None:
    service.upsert_obor(
        Obor(
            name="Softwarové inženýrství",
            stag_code="NSWI-K",
            secretary_name="Nováková",
            secretary_email="sekretarka@utb.cz",
        )
    )


def test_opponent_matches_by_stag_code(qapp, service: ThesisService, pm: _StubPM, tmp_path: Path) -> None:
    _obor_with_secretary(service)
    op = OpposingThesis(
        type=ThesisType.BP, academic_year="2024/2025",
        student_first_name="Jan", student_last_name="Novák",
        student_obor="NSWI-K",  # STAG kód, NE název
        title_cs="Nějaká práce",
    )
    service.upsert_opposing_thesis(op)
    src = tmp_path / "posudek.pdf"
    src.write_bytes(b"%PDF dummy")
    service.opposing_attach_document(op.id, src, kind=AttachmentKind.OPPONENT_REVIEW)

    dlg = SendReviewsDialog(service, pm, "opponent")
    sec = dlg._current_secretary()
    assert sec is not None
    items = dlg._gather_items(sec)
    assert len(items) == 1
    assert items[0].student_name == "Novák, Jan" or "Novák" in items[0].student_name


def test_supervisor_matches_by_name(qapp, service: ThesisService, pm: _StubPM, tmp_path: Path) -> None:
    _obor_with_secretary(service)
    student = Student(first_name="Eva", last_name="Malá",
                      obor="Softwarové inženýrství", university_id="A1")
    service.upsert_student(student)
    t = Thesis(type=ThesisType.DP, academic_year="2024/2025", student_id=student.id,
               title_cs="DP práce", status=ThesisStatus.IN_PROGRESS)
    service.upsert_thesis(t)
    src = tmp_path / "pv.pdf"
    src.write_bytes(b"%PDF dummy")
    service.attach_document(t.id, src, kind=AttachmentKind.SUPERVISOR_REVIEW)

    dlg = SendReviewsDialog(service, pm, "supervisor")
    sec = dlg._current_secretary()
    assert sec is not None
    items = dlg._gather_items(sec)
    assert len(items) == 1
    assert items[0].type_code == "DP"


def test_supervisor_skips_history(qapp, service: ThesisService, pm: _StubPM, tmp_path: Path) -> None:
    """Práce z Historie (obhájeno) se k odeslání nenabízí — jen „V řešení"."""
    _obor_with_secretary(service)
    student = Student(first_name="Petr", last_name="Starý",
                      obor="Softwarové inženýrství", university_id="A9")
    service.upsert_student(student)
    t = Thesis(type=ThesisType.BP, academic_year="2022/2023", student_id=student.id,
               title_cs="Obhájená práce", status=ThesisStatus.DEFENDED)
    service.upsert_thesis(t)
    src = tmp_path / "pv.pdf"
    src.write_bytes(b"%PDF dummy")
    service.attach_document(t.id, src, kind=AttachmentKind.SUPERVISOR_REVIEW)

    dlg = SendReviewsDialog(service, pm, "supervisor")
    assert dlg._gather_items(dlg._current_secretary()) == []


def test_no_match_other_obor(qapp, service: ThesisService, pm: _StubPM, tmp_path: Path) -> None:
    _obor_with_secretary(service)
    op = OpposingThesis(
        type=ThesisType.BP, academic_year="2024/2025",
        student_last_name="Cizí", student_obor="UPLNE-JINY",
        title_cs="Práce",
    )
    service.upsert_opposing_thesis(op)
    src = tmp_path / "p.pdf"
    src.write_bytes(b"%PDF dummy")
    service.opposing_attach_document(op.id, src, kind=AttachmentKind.OPPONENT_REVIEW)

    dlg = SendReviewsDialog(service, pm, "opponent")
    items = dlg._gather_items(dlg._current_secretary())
    assert items == []
