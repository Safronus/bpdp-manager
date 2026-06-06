"""Testy tiskové akce (bez reálného tisku — monkeypatch subprocess/open)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from bpdpmanager.ui import _os_actions


def test_print_nonexistent_returns_error(tmp_path: Path) -> None:
    assert _os_actions.print_path(tmp_path / "neni.pdf") == "error"


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX větev (lpr)")
def test_print_pdf_sends_to_printer(tmp_path: Path, monkeypatch) -> None:
    pdf = tmp_path / "a.pdf"
    pdf.write_bytes(b"%PDF dummy")
    calls = {}
    monkeypatch.setattr(_os_actions.subprocess, "run",
                        lambda *a, **k: calls.setdefault("cmd", a[0]))
    assert _os_actions.print_path(pdf) == "printed"
    assert calls["cmd"][0] == "lpr"


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX větev")
def test_print_xlsx_opens_app(tmp_path: Path, monkeypatch) -> None:
    xlsx = tmp_path / "a.xlsx"
    xlsx.write_bytes(b"x")
    opened = {}
    monkeypatch.setattr(_os_actions, "open_path", lambda p: opened.setdefault("p", p))
    assert _os_actions.print_path(xlsx) == "opened"
    assert opened["p"] == xlsx
