"""Testy indikace odeslání posudku v souhrnu + akcí nad souborem."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from bpdpmanager.models import OpposingThesis, Student, Thesis  # noqa: E402
from bpdpmanager.models.enums import AttachmentKind, ThesisStatus, ThesisType  # noqa: E402
from bpdpmanager.services import ThesisService  # noqa: E402
from bpdpmanager.storage import JsonRepository  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    yield QApplication.instance() or QApplication([])


@pytest.fixture
def service(tmp_path: Path) -> ThesisService:
    repo = JsonRepository(path=tmp_path / "db.json", backup_path=tmp_path / "db.json.bak")
    return ThesisService(repo)


def test_thesis_summary_sent_indicator(qapp, service: ThesisService, tmp_path: Path) -> None:
    from bpdpmanager.ui.thesis_detail import ThesisDetail

    student = Student(first_name="Jan", last_name="Novák")
    service.upsert_student(student)
    t = Thesis(type=ThesisType.BP, academic_year="2024/2025", student_id=student.id,
               status=ThesisStatus.IN_PROGRESS, title_cs="Práce")
    service.upsert_thesis(t)
    src = tmp_path / "pv.pdf"
    src.write_bytes(b"%PDF dummy")
    service.attach_document(t.id, src, kind=AttachmentKind.SUPERVISOR_REVIEW)

    det = ThesisDetail(service)
    html = det._build_summary_html(service.get_thesis(t.id))
    assert "neodesláno" in html  # má posudek, ale neodeslaný

    service.mark_supervisor_review_sent(t.id)
    html2 = det._build_summary_html(service.get_thesis(t.id))
    assert "odesláno" in html2 and "neodesláno" not in html2


def test_opposing_summary_sent_indicator(qapp, service: ThesisService, tmp_path: Path) -> None:
    from bpdpmanager.ui.opposing_detail import OpposingDetail

    op = OpposingThesis(type=ThesisType.BP, academic_year="2024/2025",
                        student_last_name="Malá", title_cs="P")
    service.upsert_opposing_thesis(op)
    src = tmp_path / "po.pdf"
    src.write_bytes(b"%PDF dummy")
    service.opposing_attach_document(op.id, src, kind=AttachmentKind.OPPONENT_REVIEW)

    det = OpposingDetail(service)
    html = det._build_summary_html(service.get_opposing_thesis(op.id))
    assert "neodesláno" in html

    service.mark_opponent_review_sent(op.id)
    html2 = det._build_summary_html(service.get_opposing_thesis(op.id))
    assert "odesláno" in html2 and "neodesláno" not in html2


def test_copy_file_to_clipboard(qapp, service: ThesisService, tmp_path: Path) -> None:
    from bpdpmanager.ui.widgets.documents_widget import DocumentsWidget

    t = Thesis(type=ThesisType.BP, academic_year="2024/2025")
    service.upsert_thesis(t)
    src = tmp_path / "soubor.pdf"
    src.write_bytes(b"%PDF dummy")
    service.attach_document(t.id, src, kind=AttachmentKind.THESIS_TEXT)

    w = DocumentsWidget(service)
    w.set_thesis_id(t.id)
    att = service.get_thesis(t.id).attachments[0]
    w._copy_file_to_clipboard(att)

    md = QApplication.clipboard().mimeData()
    assert md.hasUrls()
    assert md.urls()[0].toLocalFile().endswith(".pdf")
