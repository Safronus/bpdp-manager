"""Testy e-mailové vrstvy pro odesílání posudků + servisních pomocníků."""

from __future__ import annotations

import email as email_mod
import email.policy
from pathlib import Path

import pytest

from bpdpmanager.models import Student, Thesis
from bpdpmanager.models.enums import AttachmentKind, ThesisType
from bpdpmanager.services import ThesisService
from bpdpmanager.services import email_sender
from bpdpmanager.services.email_sender import MailDraft
from bpdpmanager.storage import JsonRepository


@pytest.fixture
def service(tmp_path: Path) -> ThesisService:
    repo = JsonRepository(path=tmp_path / "db.json", backup_path=tmp_path / "db.json.bak")
    return ThesisService(repo)


# ── Skládání textu ───────────────────────────────────────────────────────────

def test_compose_subject() -> None:
    assert "vedoucího" in email_sender.compose_subject("supervisor")
    assert "oponenta" in email_sender.compose_subject("opponent")


def test_compose_body_groups_bp_dp() -> None:
    items = [
        ("BP", "Jan Novák", "A1", "Téma jedna"),
        ("DP", "Eva Malá", "A2", "Téma dvě"),
        ("BP", "Petr Velký", "A3", "Téma tři"),
    ]
    body = email_sender.compose_body(
        items, role="supervisor", secretary_name="Nováková", sender_display="doc. X"
    )
    assert "Dobrý den, paní Nováková," in body
    assert "Bakalářské práce:" in body
    assert "Diplomové práce:" in body
    # BP skupina obsahuje oba BP studenty, DP jednoho
    bp_idx = body.index("Bakalářské práce:")
    dp_idx = body.index("Diplomové práce:")
    assert bp_idx < dp_idx
    assert "Jan Novák (A1)" in body
    assert "Eva Malá (A2)" in body
    assert "doc. X" in body


def test_compose_body_no_secretary_name() -> None:
    body = email_sender.compose_body(
        [("BP", "X Y", "", "T")], role="opponent"
    )
    assert body.startswith("Dobrý den,")


# ── MailDraft / build_message ────────────────────────────────────────────────

def test_recipients_dedup() -> None:
    d = MailDraft(
        from_addr="me@utb.cz", to=["sek@utb.cz"], subject="s", body="b",
        cc=["me@utb.cz", "sek@utb.cz"],
    )
    # Pořadí To pak Cc, bez duplicit
    assert d.recipients == ["sek@utb.cz", "me@utb.cz"]


def test_build_message_with_pdf(tmp_path: Path) -> None:
    pdf = tmp_path / "posudek.pdf"
    pdf.write_bytes(b"%PDF-1.4 dummy")
    draft = MailDraft(
        from_addr="me@utb.cz", from_name="doc. Já",
        to=["sek@utb.cz"], cc=["me@utb.cz"],
        subject="Posudky", body="Text", attachments=[pdf],
    )
    msg = email_sender.build_message(draft)
    assert msg["Subject"] == "Posudky"
    assert msg["To"] == "sek@utb.cz"
    assert msg["Cc"] == "me@utb.cz"
    assert "me@utb.cz" in msg["From"]
    attachments = [p for p in msg.iter_attachments()]
    assert len(attachments) == 1
    assert attachments[0].get_filename() == "posudek.pdf"
    assert attachments[0].get_content_type() == "application/pdf"


def test_build_message_requires_sender_and_recipient(tmp_path: Path) -> None:
    with pytest.raises(email_sender.EmailError):
        email_sender.build_message(MailDraft(from_addr="", to=["x@y"], subject="", body=""))
    with pytest.raises(email_sender.EmailError):
        email_sender.build_message(MailDraft(from_addr="a@b", to=[], subject="", body=""))


def test_build_message_missing_attachment(tmp_path: Path) -> None:
    draft = MailDraft(
        from_addr="me@utb.cz", to=["s@utb.cz"], subject="s", body="b",
        attachments=[tmp_path / "neexistuje.pdf"],
    )
    with pytest.raises(email_sender.EmailError):
        email_sender.build_message(draft)


def test_save_as_eml_roundtrip(tmp_path: Path) -> None:
    pdf = tmp_path / "p.pdf"
    pdf.write_bytes(b"%PDF dummy")
    draft = MailDraft(
        from_addr="me@utb.cz", to=["s@utb.cz"], subject="Předmět",
        body="Tělo", attachments=[pdf],
    )
    out = tmp_path / "mail.eml"
    email_sender.save_as_eml(draft, out)
    assert out.is_file()
    parsed = email_mod.message_from_bytes(out.read_bytes(), policy=email.policy.default)
    assert str(parsed["Subject"]) == "Předmět"
    assert parsed["To"] == "s@utb.cz"


# ── Servisní pomocníci ───────────────────────────────────────────────────────

def test_current_supervisor_review_pdf_and_mark_sent(service: ThesisService, tmp_path: Path) -> None:
    student = Student(first_name="Jan", last_name="Novák", university_id="A1")
    service.upsert_student(student)
    t = Thesis(type=ThesisType.BP, academic_year="2024/2025", student_id=student.id)
    service.upsert_thesis(t)

    src = tmp_path / "src_posudek.pdf"
    src.write_bytes(b"%PDF dummy")
    service.attach_document(t.id, src, kind=AttachmentKind.SUPERVISOR_REVIEW)

    pdf = service.current_supervisor_review_pdf(service.get_thesis(t.id))
    assert pdf is not None and pdf.exists() and pdf.suffix == ".pdf"

    assert service.get_thesis(t.id).supervisor_review_sent_at is None
    service.mark_supervisor_review_sent(t.id)
    assert service.get_thesis(t.id).supervisor_review_sent_at is not None


def test_current_supervisor_review_pdf_none_when_no_pdf(service: ThesisService) -> None:
    t = Thesis(type=ThesisType.DP, academic_year="2024/2025")
    service.upsert_thesis(t)
    assert service.current_supervisor_review_pdf(t) is None
