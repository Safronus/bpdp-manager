"""Testy: auto-doplnění známek u oponentur + parsování známky z textu posudku."""

from __future__ import annotations

from pathlib import Path

import pytest

from bpdpmanager.models import OpposingThesis
from bpdpmanager.models.enums import ThesisType
from bpdpmanager.models.review import CriterionScore, Review
from bpdpmanager.services import ThesisService
from bpdpmanager.services.review_pdf import parse_grade_from_text
from bpdpmanager.storage import JsonRepository


@pytest.fixture
def service(tmp_path: Path) -> ThesisService:
    repo = JsonRepository(path=tmp_path / "db.json", backup_path=tmp_path / "db.json.bak")
    return ThesisService(repo)


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Procentuální úspěšnost: 66,7%\nNavržená známka: D\nVýsledek", "D"),
        ("Proposed grade: B\nResult of plagiarism", "B"),
        ("Suggested grade:  FX ", "FX"),
        ("Navržená známka:\nA", "A"),
        ("Klasifikační stupnice ECTS: A – výborně, B – velmi dobře", None),  # jen legenda
        ("žádná známka tu není", None),
    ],
)
def test_parse_grade_from_text(text: str, expected: str | None) -> None:
    assert parse_grade_from_text(text) == expected


def test_opponent_grade_autofilled_from_review(service: ThesisService) -> None:
    op = OpposingThesis(type=ThesisType.DP, academic_year="2025/2026")
    service.upsert_opposing_thesis(op)
    # 7 kritérií, skóre 3 → DP body 21 → 60 % → E
    review = Review(
        role="opponent", is_current=True,
        criteria=[CriterionScore(row=10 + i, label=f"K{i}", weight=1.0, score=3.0)
                  for i in range(7)],
    )
    service.upsert_review(op.id, review, opposing=True)
    refreshed = service.get_opposing_thesis(op.id)
    assert refreshed.grade_opponent == review.suggested_grade == "E"


def test_supervisor_grade_from_uploaded_pdf(service: ThesisService, tmp_path: Path) -> None:
    op = OpposingThesis(type=ThesisType.DP, academic_year="2025/2026",
                        student_last_name="Pohanka")
    service.upsert_opposing_thesis(op)

    # minimální „PDF" — extrakce pypdf selže (není to validní PDF) → None,
    # ale grade_supervisor zůstane prázdná (žádná výjimka).
    fake = tmp_path / "fake.pdf"
    fake.write_bytes(b"%PDF-1.4 not really")
    from bpdpmanager.models.enums import AttachmentKind
    service.opposing_attach_document(op.id, fake, kind=AttachmentKind.SUPERVISOR_REVIEW)
    refreshed = service.get_opposing_thesis(op.id)
    assert refreshed.grade_supervisor == ""  # nečitelné PDF → bez známky, bez pádu
