"""Test barevného prahu počtu budoucích prací v titulku záložky."""

from __future__ import annotations

from bpdpmanager.ui.main_window import _FUTURE_CAPACITY, _future_count_color


def test_future_count_color_thresholds() -> None:
    assert _future_count_color(0) == "#2e7d32"                     # zelená
    assert _future_count_color(_FUTURE_CAPACITY - 1) == "#2e7d32"
    assert _future_count_color(_FUTURE_CAPACITY) == "#f9a825"      # žlutá
    assert _future_count_color(_FUTURE_CAPACITY + 1) == "#c62828"  # červená
    assert _future_count_color(99) == "#c62828"
