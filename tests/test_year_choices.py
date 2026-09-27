"""Nabídka akademických roků v detailu práce podle tabu (``year_mode``)."""

from __future__ import annotations

import pytest

from bpdpmanager.ui import thesis_detail as td


@pytest.fixture
def year_2026(monkeypatch: pytest.MonkeyPatch) -> None:
    # Běžící rok 2026/2027 (po 1. 9. 2026) — nezávisle na skutečném datu.
    monkeypatch.setattr(td, "_current_year_start", lambda: 2026)


def test_future_includes_current_year(year_2026) -> None:
    # Zájemci / vypsaná témata běžícího roku se ještě schvalují → letošní rok
    # musí být v nabídce Budoucích (dřív jen příští + přespříští).
    assert td._academic_year_choices(td.YEAR_MODE_FUTURE) == [
        "2026/2027", "2027/2028", "2028/2029",
    ]


def test_other_modes_unchanged(year_2026) -> None:
    assert td._academic_year_choices(td.YEAR_MODE_CURRENT) == ["2026/2027"]
    history = td._academic_year_choices(td.YEAR_MODE_HISTORY)
    assert history[0] == "2025/2026" and history[-1] == "2009/2010"
    all_years = td._academic_year_choices(td.YEAR_MODE_ALL)
    assert all_years[0] == "2028/2029" and "2026/2027" in all_years
