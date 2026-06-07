"""Test barev v titulcích záložek (kapacita budoucích + dokončenost posudků)."""

from __future__ import annotations

from bpdpmanager.ui.main_window import (
    _FUTURE_CAPACITY,
    _TAB_AMBER,
    _TAB_GREEN,
    _TAB_RED,
    _future_count_color,
    _reviews_complete_color,
)


def test_future_count_color_thresholds() -> None:
    assert _future_count_color(0) == _TAB_GREEN
    assert _future_count_color(_FUTURE_CAPACITY - 1) == _TAB_GREEN
    assert _future_count_color(_FUTURE_CAPACITY) == _TAB_AMBER
    assert _future_count_color(_FUTURE_CAPACITY + 1) == _TAB_RED


def test_reviews_complete_color() -> None:
    assert _reviews_complete_color([]) is None              # žádné práce
    assert _reviews_complete_color([True, True]) == _TAB_GREEN   # vše hotové+odeslané
    assert _reviews_complete_color([True, False]) == _TAB_AMBER  # něco chybí
    assert _reviews_complete_color([False]) == _TAB_AMBER
