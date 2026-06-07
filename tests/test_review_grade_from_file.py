"""Vyčtení navržené známky z textu / DOCX posudku (mimo XLSX kritéria)."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from bpdpmanager.services.review_pdf import (
    extract_grade_from_file,
    parse_grade_from_text,
)

_DOCX_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
    "<w:body>{body}</w:body></w:document>"
)


def _make_docx(path: Path, text: str) -> None:
    """Sestaví minimální .docx s jedním odstavcem zadaného textu."""
    para = f"<w:p><w:r><w:t>{text}</w:t></w:r></w:p>"
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("word/document.xml", _DOCX_XML.format(body=para))


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Navržená známka: D", "D"),
        ("navrhuji hodnocení B - velmi dobře", "B"),
        ("a doporučuji hodnotit stupněm A", "A"),
        ("Proposed grade: C", "C"),
        ("doporučuji ji k obhajobě s hodnocením B-C", "B"),
        ("v případě hodnocení stupněm F – nedostatečně", None),  # boilerplate
        ("žádná navržená známka tu není", None),
    ],
)
def test_parse_grade_from_text(text: str, expected: str | None) -> None:
    assert parse_grade_from_text(text) == expected


def test_extract_grade_from_docx(tmp_path: Path) -> None:
    docx = tmp_path / "posudek.docx"
    _make_docx(docx, "Předloženou práci doporučuji k obhajobě s hodnocením B.")
    assert extract_grade_from_file(docx) == "B"


def test_extract_grade_unknown_suffix_returns_none(tmp_path: Path) -> None:
    other = tmp_path / "posudek.txt"
    other.write_text("navrhuji hodnocení A", encoding="utf-8")
    assert extract_grade_from_file(other) is None
