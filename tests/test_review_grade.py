"""Testy navržené známky (ECTS) — 1:1 se vzorcem v XLSX šablonách FAI UTB.

BP (max 30): A≥29, B≥26, C≥23, D≥20, E≥18, jinak FX  (E≥18 == 60 %)
DP (max 35): A≥33, B≥30, C≥27, D≥24, E≥21, jinak F   (E≥21 == 60 %)
"""

from __future__ import annotations

import pytest

from bpdpmanager.models.review import CriterionScore, Review


def _review(n_criteria: int, total_points: float, *, fulfilled: bool = True) -> Review:
    """Review s ``n`` kritérii (váha 1) a daným součtem vážených bodů.

    ``n=6`` → max 30 (BP), ``n=7`` → max 35 (DP). Body se rozloží do skóre.
    """
    scores = [0.0] * n_criteria
    remaining = total_points
    for i in range(n_criteria):
        s = min(5.0, remaining)
        scores[i] = s
        remaining -= s
    criteria = [
        CriterionScore(row=10 + i, label=f"K{i}", weight=1.0, score=scores[i])
        for i in range(n_criteria)
    ]
    return Review(
        criteria=criteria,
        assignment_fulfilled="splnil(a)" if fulfilled else "nesplnil(a)",
    )


@pytest.mark.parametrize(
    "points,expected",
    [
        (30, "A"), (29, "A"),
        (28, "B"), (26, "B"),
        (25, "C"), (23, "C"),
        (22, "D"), (20, "D"),
        (19, "E"), (18, "E"),       # 18/30 = 60 % → E
        (17.5, "FX"),               # 58,3 % → FX (nahlášený bug, dřív E)
        (17, "FX"), (0, "FX"),
    ],
)
def test_bp_grade_matches_template(points: float, expected: str) -> None:
    r = _review(6, points)  # max 30 → BP
    assert abs(r.max_points - 30.0) < 0.01
    assert r.suggested_grade == expected


@pytest.mark.parametrize(
    "points,expected",
    [
        (35, "A"), (33, "A"),
        (32, "B"), (30, "B"),
        (29, "C"), (27, "C"),
        (26, "D"), (24, "D"),
        (23, "E"), (21, "E"),       # 21/35 = 60 % → E
        (20.9, "F"),                # 59,7 % → F
        (20, "F"), (0, "F"),
    ],
)
def test_dp_grade_matches_template(points: float, expected: str) -> None:
    r = _review(7, points)  # max 35 → DP
    assert abs(r.max_points - 35.0) < 0.01
    assert r.suggested_grade == expected


def test_not_fulfilled_forces_fail() -> None:
    assert _review(6, 30, fulfilled=False).suggested_grade == "FX"  # BP
    assert _review(7, 35, fulfilled=False).suggested_grade == "F"   # DP


def test_reported_case_58_percent_bp_is_fx() -> None:
    # 58,3 % z 30 bodů = 17,5 b → musí být FX (ne E)
    r = _review(6, 17.5)
    assert round(r.percentage, 1) == 58.3
    assert r.suggested_grade == "FX"
