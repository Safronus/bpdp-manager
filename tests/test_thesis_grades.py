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


def test_structured_field_overrides_conclusion() -> None:
    # Strukturovaný posudek (FAI): tabulka má „Navržená známka" (PDF ji rozhodí →
    # samostatné „B"), ale závěrová věta navrhuje A. Pole vyhrává → B.
    scrambled = (
        "Splnění všech bodů zadání: splnil(a)\n95,0%\n"
        "Navržená známka:\n– adekvátnost zvolených metod\n"
        "Spolupráce autora s vedoucím práce\nB\n– náročnost tématu\n28,5\n"
        "…doporučuji k obhajobě a navrhuji hodnocení A (výborně).\n"
        "Celkové hodnocení práce, připomínky a dotazy:"
    )
    assert parse_grade_from_text(scrambled) == "B"


def test_empty_structured_field_ignores_conclusion() -> None:
    # Pole „Navržená známka" je prázdné a v tabulce není samostatná známka →
    # závěrová věta je jen orientační → None (uživatel doplní ručně).
    text = "Navržená známka:\n(nevyplněno)\nnavrhuji hodnocení A (výborně)."
    assert parse_grade_from_text(text) is None


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


# ── nahrání nového posudku přepíše známku ────────────────────────────────────

def _make_docx_review(path: Path, grade: str) -> None:
    import zipfile

    xml = (
        '<?xml version="1.0"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body><w:p><w:r><w:t>Navržená známka: {grade}</w:t></w:r></w:p></w:body>"
        "</w:document>"
    )
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("word/document.xml", xml)


def test_attach_review_overwrites_stale_grade(
    service: ThesisService, tmp_path: Path
) -> None:
    """Nový soubor posudku je autoritativní — přepíše dřív (špatně) uloženou
    známku. (Jinak by stará hodnota držela navždy: smazání přílohy ani nové
    stažení ze STAG ji neobnovilo.)"""
    from bpdpmanager.models.enums import AttachmentKind

    t = Thesis(type=ThesisType.BP, academic_year="2018/2019",
               grade_opponent="B")          # stará, špatně vyčtená hodnota
    service.upsert_thesis(t)
    f = tmp_path / "posudek-oponenta.docx"
    _make_docx_review(f, "C")
    service.attach_document(t.id, f, kind=AttachmentKind.OPPONENT_REVIEW)
    assert service.get_thesis(t.id).grade_opponent == "C"


def test_attach_unreadable_review_keeps_grade(
    service: ThesisService, tmp_path: Path
) -> None:
    """Když ze souboru známku nelze vyčíst, stávající hodnota zůstane."""
    from bpdpmanager.models.enums import AttachmentKind

    t = Thesis(type=ThesisType.BP, academic_year="2018/2019",
               grade_supervisor="A")
    service.upsert_thesis(t)
    f = tmp_path / "posudek-vedouciho.pdf"
    f.write_bytes(b"%PDF-1 broken")
    service.attach_document(t.id, f, kind=AttachmentKind.SUPERVISOR_REVIEW)
    assert service.get_thesis(t.id).grade_supervisor == "A"
