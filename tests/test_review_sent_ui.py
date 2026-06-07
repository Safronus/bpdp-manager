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


def test_transitions_hidden_for_historical_status(qapp, service: ThesisService) -> None:
    """Panel přechodů se skryje u historických prací (i v záložce Vše)."""
    from bpdpmanager.ui.thesis_detail import ThesisDetail

    det = ThesisDetail(service)  # show_transitions=True (default)
    box = next(iter(det.transition_buttons.values())).parent()

    s = Student(first_name="Jan", last_name="Novák")
    service.upsert_student(s)
    t = Thesis(type=ThesisType.BP, academic_year="2024/2025", student_id=s.id,
               status=ThesisStatus.IN_PROGRESS, title_cs="P")
    service.upsert_thesis(t)

    det.set_thesis(service.get_thesis(t.id))
    assert box.isVisibleTo(det) is True       # V řešení → panel viditelný

    service.transition(t.id, ThesisStatus.DEFENDED)
    det.set_thesis(service.get_thesis(t.id))
    assert box.isVisibleTo(det) is False      # Obhájeno → panel skrytý


def test_detail_can_hide_transitions(qapp, service: ThesisService) -> None:
    """ThesisDetail se show_transitions=False skryje panel „Přechod do stavu"."""
    from bpdpmanager.ui.thesis_detail import ThesisDetail

    det_default = ThesisDetail(service)
    det_hidden = ThesisDetail(service, show_transitions=False)
    # Tlačítka existují v obou, ale skupinový box je u hidden neviditelný.
    assert det_default._show_transitions is True
    assert det_hidden._show_transitions is False
    # Box přechodů (rodič tlačítka) je u hidden skrytý.
    btn = next(iter(det_hidden.transition_buttons.values()))
    assert btn.parent().isVisibleTo(det_hidden) is False


def test_history_summary_hides_sent_section(qapp, service: ThesisService, tmp_path: Path) -> None:
    """U historických prací (obhájeno/nedokončeno) se sekce Odeslání neukazuje."""
    from bpdpmanager.ui.thesis_detail import ThesisDetail

    student = Student(first_name="Jan", last_name="Novák")
    service.upsert_student(student)
    t = Thesis(type=ThesisType.BP, academic_year="2024/2025", student_id=student.id,
               status=ThesisStatus.IN_PROGRESS, title_cs="Práce")
    service.upsert_thesis(t)
    src = tmp_path / "pv.pdf"
    src.write_bytes(b"%PDF dummy")
    service.attach_document(t.id, src, kind=AttachmentKind.SUPERVISOR_REVIEW)
    service.mark_supervisor_review_sent(t.id)

    det = ThesisDetail(service)
    # Dokud je „V řešení", sekce se ukazuje.
    assert "Odeslání posudku" in det._build_summary_html(service.get_thesis(t.id))

    # Po přechodu do historie (Obhájeno) sekce zmizí — fakt je irelevantní.
    service.transition(t.id, ThesisStatus.DEFENDED)
    assert "Odeslání posudku" not in det._build_summary_html(service.get_thesis(t.id))


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
