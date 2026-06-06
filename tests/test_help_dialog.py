"""Test nápovědy — Enter v hledání nesmí zavřít okno (default tlačítka)."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QPushButton

from bpdpmanager.ui.help_dialog import (
    FirstRunDialog,
    HelpDialog,
    _extract_section,
    _napoveda_path,
)


@pytest.fixture(scope="module")
def qapp():
    yield QApplication.instance() or QApplication([])


def test_tutorial_recommends_stag_download(qapp) -> None:
    """Tutoriál (sekce Začínáme) doporučí prvotní stažení prací ze STAG."""
    section = _extract_section(_napoveda_path().read_text(encoding="utf-8"), "Začínáme")
    assert "Moje vedené práce" in section
    assert "Moje oponentury" in section
    # a první spuštěcí dialog ho z té sekce renderuje
    dlg = FirstRunDialog()
    md = dlg.view.toMarkdown() if hasattr(dlg.view, "toMarkdown") else dlg.view.toHtml()
    assert "vedené práce" in md or "oponentury" in md


def test_enter_searches_not_closes(qapp) -> None:
    dlg = HelpDialog()
    buttons = {b.text(): b for b in dlg.findChildren(QPushButton)}
    # „Další" (hledání) je výchozí → Enter hledá.
    assert buttons["Další"].isDefault()
    # „Zavřít" není default ani autoDefault → Enter okno nezavře.
    assert not buttons["Zavřít"].isDefault()
    assert not buttons["Zavřít"].autoDefault()
