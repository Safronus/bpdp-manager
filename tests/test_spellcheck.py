"""Testy kontroly pravopisu (spylls + přibalený český slovník)."""

from __future__ import annotations

import pytest

from bpdpmanager.services import spellcheck


def test_spellcheck_available() -> None:
    # spylls je závislost a slovník je přibalený → musí být k dispozici.
    assert spellcheck.is_available()


@pytest.mark.parametrize(
    "word,correct",
    [
        ("práce", True),
        ("posudku", True),
        ("bakalářská", True),
        ("webových", True),
        ("chzba", False),
        ("přklep", False),
    ],
)
def test_check_word(word: str, correct: bool) -> None:
    assert spellcheck.check_word(word) is correct


def test_suggest_offers_correction() -> None:
    sugg = spellcheck.suggest("chzba")
    assert "chyba" in sugg


def test_check_word_without_dict_is_lenient(monkeypatch) -> None:
    # Když slovník není načtený, nic se nehlásí (vrací True) — bezpečné chování.
    monkeypatch.setattr(spellcheck, "_load", lambda: None)
    assert spellcheck.check_word("chzba") is True
    assert spellcheck.suggest("chzba") == []
    assert spellcheck.is_available() is False
