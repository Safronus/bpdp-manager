"""Test nápovědy — Enter v hledání nesmí zavřít okno (default tlačítka)."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QPushButton

from bpdpmanager.ui.help_dialog import HelpDialog


@pytest.fixture(scope="module")
def qapp():
    yield QApplication.instance() or QApplication([])


def test_enter_searches_not_closes(qapp) -> None:
    dlg = HelpDialog()
    buttons = {b.text(): b for b in dlg.findChildren(QPushButton)}
    # „Další" (hledání) je výchozí → Enter hledá.
    assert buttons["Další"].isDefault()
    # „Zavřít" není default ani autoDefault → Enter okno nezavře.
    assert not buttons["Zavřít"].isDefault()
    assert not buttons["Zavřít"].autoDefault()
