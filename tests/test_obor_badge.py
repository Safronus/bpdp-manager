"""Test barevného badge oboru (barva dle programu + EN vlaječka)."""

from __future__ import annotations

import pytest

from bpdpmanager.ui.theses_tree import _OBOR_COLORS, obor_badge


@pytest.mark.parametrize(
    "name,exp_label,exp_color,exp_en",
    [
        ("BTSM-K", "BTSM-K", _OBOR_COLORS["BTSM"], False),
        ("SWI-P", "SWI-P", _OBOR_COLORS["SWI"], False),
        ("SWI-P-EN", "SWI-P", _OBOR_COLORS["SWI"], True),     # EN → vlaječka, barva dle SWI
        ("NSWI-P", "NSWI-P", _OBOR_COLORS["NSWI"], False),    # N-varianta jiná barva
        ("NKYB-K", "NKYB-K", _OBOR_COLORS["NKYB"], False),
        ("ITA-P", "ITA-P", _OBOR_COLORS["ITA"], False),
        ("NUI-P", "NUI-P", _OBOR_COLORS["NUI"], False),
        ("IRT-K", "IRT-K", _OBOR_COLORS["IRT"], False),
    ],
)
def test_obor_badge_known(name, exp_label, exp_color, exp_en) -> None:
    label, color, is_en = obor_badge(name)
    assert label == exp_label
    assert color == exp_color
    assert is_en is exp_en


def test_obor_badge_empty_and_fallback() -> None:
    assert obor_badge("—") == (None, None, False)
    assert obor_badge("") == (None, None, False)
    # Neznámý obor → dostane deterministickou (neprázdnou) barvu z palety.
    label, color, _ = obor_badge("NPKS-P")
    assert label == "NPKS-P" and color and color not in _OBOR_COLORS.values()
    # Stejný název → stejná barva (deterministické).
    assert obor_badge("NPKS-P")[1] == color
