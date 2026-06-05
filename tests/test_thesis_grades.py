"""Testy navržených známek u vedených prací.

Pokrývá:
- parser historických formulací posudku („navrhuji hodnocení B - velmi dobře"),
- bezpečnost vůči boilerplate vět („v případě hodnocení stupněm F…"),
- ThesisService.sync_thesis_grades (z in-app posudku; prázdné pole se nepřepíše).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from bpdpmanager.models import Thesis
from bpdpmanager.models.enums import ThesisType
from bpdpmanager.models.review import CriterionScore, Review
from bpdpmanager.services import ThesisService
from bpdpmanager.services.review_pdf import parse_grade_from_text
from bpdpmanager.storage import JsonRepository


@pytest.fixture
def service(tmp_path: Path) -> ThesisService:
    repo = JsonRepository(path=tmp_path / "db.json", backup_path=tmp_path / "db.json.bak")
    return ThesisService(repo)


# ── Parser historických formulací ────────────────────────────────────────────

@pytest.mark.parametrize(
    "text,expected",
    [
        ("Navržená známka: D", "D"),
        ("Proposed grade: B", "B"),
        ("...a navrhuji hodnocení B - velmi dobře.", "B"),
        ("doporučuji k obhajobě a doporučuji hodnotit stupněm A - výborně.", "A"),
        ("navrhuji hodnocení F - nedostatečně.", "F"),
        ("navrhuji klasifikovat stupněm C.", "C"),
    ],
)
def test_parse_historical_phrasings(text: str, expected: str) -> None:
    assert parse_grade_from_text(text) == expected


def test_parse_ignores_boilerplate() -> None:
    # Věta, která je v každém posudku FAI UTB, NESMÍ vrátit známku.
    boiler = (
        "Hodnocení práce: A B C D E F. Známku uvede oponent dle svého uvážení "
        "dle klasifikační stupnice ECTS. Stupeň F znamená též „nedoporučuji "
        "práci k obhajobě“. V případě hodnocení stupněm „F – nedostatečně“ "
        "uveďte do připomínek hlavní nedostatky."
    )
    assert parse_grade_from_text(boiler) is None


def test_parse_proposal_before_boilerplate() -> None:
    # Skutečný posudek: návrhová věta (B) je před boilerplate (F) → vrátí B.
    text = (
        "Předloženou bakalářskou práci doporučuji k obhajobě a navrhuji "
        "hodnocení B - velmi dobře. V případě hodnocení stupněm „F – "
        "nedostatečně“ uveďte do připomínek hlavní nedostatky."
    )
    assert parse_grade_from_text(text) == "B"


# ── sync_thesis_grades ───────────────────────────────────────────────────────

def _bp_review(role: str, points: float) -> Review:
    # 6 kritérií váhy 1 → max 30 (BP). 26 b → B.
    scores = []
    remaining = points
    for _ in range(6):
        s = min(5.0, remaining)
        scores.append(s)
        remaining -= s
    return Review(
        role=role,
        criteria=[
            CriterionScore(row=10 + i, label=f"K{i}", weight=1.0, score=sc)
            for i, sc in enumerate(scores)
        ],
    )


def test_sync_from_inapp_reviews(service: ThesisService) -> None:
    t = Thesis(type=ThesisType.BP, academic_year="2023/2024")
    t.reviews = [_bp_review("supervisor", 26.0), _bp_review("opponent", 29.0)]
    service.upsert_thesis(t)

    synced = service.sync_thesis_grades(t.id)
    assert synced.grade_supervisor == "B"
    assert synced.grade_opponent == "A"


def test_sync_does_not_overwrite_existing(service: ThesisService) -> None:
    t = Thesis(type=ThesisType.BP, academic_year="2023/2024",
               grade_supervisor="C")
    t.reviews = [_bp_review("supervisor", 29.0)]  # spočetlo by A
    service.upsert_thesis(t)

    synced = service.sync_thesis_grades(t.id)
    assert synced.grade_supervisor == "C"  # ruční hodnota zůstane


def test_sync_empty_when_no_data(service: ThesisService) -> None:
    t = Thesis(type=ThesisType.DP, academic_year="2023/2024")
    service.upsert_thesis(t)
    synced = service.sync_thesis_grades(t.id)
    assert synced.grade_supervisor == ""
    assert synced.grade_opponent == ""
