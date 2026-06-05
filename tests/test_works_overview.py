"""Testy: vyhledávání prací, stav posudku (barvy) a tituly před/za."""

from __future__ import annotations

from pathlib import Path

import pytest

from bpdpmanager.models import (
    Attachment,
    Opponent,
    OpposingThesis,
    Student,
    Supervisor,
    Thesis,
)
from bpdpmanager.models.enums import AttachmentKind, ThesisType
from bpdpmanager.models.naming import compose_titled_name
from bpdpmanager.models.review import Review
from bpdpmanager.services import ThesisService
from bpdpmanager.storage import JsonRepository


@pytest.fixture
def service(tmp_path: Path) -> ThesisService:
    repo = JsonRepository(path=tmp_path / "db.json", backup_path=tmp_path / "db.json.bak")
    return ThesisService(repo)


# ── tituly ───────────────────────────────────────────────────────────────────


def test_compose_titled_name() -> None:
    assert compose_titled_name("doc. Ing.", "Petr Novák", "Ph.D.") == "doc. Ing. Petr Novák Ph.D."
    assert compose_titled_name("doc. Ing.", "Petr Novák", ", Ph.D.") == "doc. Ing. Petr Novák, Ph.D."
    assert compose_titled_name("", "Petr Novák", "") == "Petr Novák"
    assert compose_titled_name("  ", " Eva Malá ", "") == "Eva Malá"


def test_opponent_supervisor_display_name() -> None:
    o = Opponent(name="Petr Novák", title_before="doc. Ing.", title_after="Ph.D.")
    assert o.display_name == "doc. Ing. Petr Novák Ph.D."
    s = Supervisor(name="Eva Malá", title_before="prof.", title_after="CSc.")
    assert s.display_name == "prof. Eva Malá CSc."
    assert "(" not in s.display_name  # affiliation jen v display_label


# ── stav posudku (barvy) ─────────────────────────────────────────────────────


def _thesis(**kw) -> Thesis:
    return Thesis(type=ThesisType.BP, academic_year="2025/2026", **kw)


def test_supervisor_review_state() -> None:
    assert _thesis().supervisor_review_state == "none"

    draft = _thesis(reviews=[Review(role="supervisor")])
    assert draft.supervisor_review_state == "draft"

    done = _thesis(
        attachments=[
            Attachment(
                label="x.xlsx", url_or_path="posudky/x.xlsx",
                kind=AttachmentKind.SUPERVISOR_REVIEW, is_file=True,
            )
        ],
        reviews=[Review(role="supervisor")],
    )
    assert done.supervisor_review_state == "done"  # soubor má přednost


def test_opponent_review_state() -> None:
    op = OpposingThesis(type=ThesisType.DP, academic_year="2025/2026")
    assert op.opponent_review_state == "none"
    op.reviews = [Review(role="opponent")]
    assert op.opponent_review_state == "draft"
    op.attachments = [
        Attachment(
            label="o.xlsx", url_or_path="posudky/o.xlsx",
            kind=AttachmentKind.OPPONENT_REVIEW, is_file=True,
        )
    ]
    assert op.opponent_review_state == "done"


# ── vyhledávání ──────────────────────────────────────────────────────────────


def test_search_works(service: ThesisService) -> None:
    student = Student(first_name="Veronika", last_name="Hřešilová", university_id="A21000")
    service.upsert_student(student)
    t = Thesis(
        type=ThesisType.BP, academic_year="2025/2026",
        title_cs="Kryptografie v praxi", student_id=student.id,
    )
    service.upsert_thesis(t)
    op = OpposingThesis(
        type=ThesisType.DP, academic_year="2025/2026",
        student_first_name="Jan", student_last_name="Dvořák",
        student_university_id="A19999", title_cs="Neuronové sítě",
    )
    service.upsert_opposing_thesis(op)

    # podle příjmení studenta
    hits = service.search_works("hřešil")
    assert len(hits) == 1 and hits[0]["kind"] == "thesis" and hits[0]["id"] == t.id

    # podle názvu
    assert any(h["id"] == t.id for h in service.search_works("kryptograf"))

    # podle univerzitního ID
    assert service.search_works("A21000")[0]["id"] == t.id

    # oponentura podle jména i ID
    assert service.search_works("dvořák")[0]["kind"] == "opposing"
    assert service.search_works("a19999")[0]["id"] == op.id

    # prázdný dotaz → nic
    assert service.search_works("   ") == []
    # nic nenalezeno
    assert service.search_works("xyzxyz") == []
