"""Vyčtení navržené známky z textu / DOCX posudku (mimo XLSX kritéria)."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from bpdpmanager.services.review_pdf import (
    _grade_from_docx_xml,
    extract_grade_from_file,
    parse_grade_from_text,
)

_W_NS = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
_GRADE_OPTIONS = [
    "vyberte hodnocení", "A - výborně", "B - velmi dobře", "C - dobře",
    "D - uspokojivě", "E - dostatečně", "F - nedostatečně",
]


def _ddlist(name: str, entries: list[str], result_idx: int) -> str:
    items = "".join(f'<w:listEntry w:val="{e}"/>' for e in entries)
    return (
        f'<w:r><w:fldChar w:fldCharType="begin"><w:ffData>'
        f'<w:name w:val="{name}"/>'
        f'<w:ddList><w:result w:val="{result_idx}"/>{items}</w:ddList>'
        f"</w:ffData></w:fldChar></w:r>"
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


def test_grade_from_form_dropdown_is_authoritative() -> None:
    """Známka z formulářového dropdownu vyhrává nad jinou položkou i textem.

    Mimo známkový dropdown jsou i dropdowny oboru / „doporučuji" — nesmí splést.
    """
    body = (
        _ddlist("Rozevírací1", ["Inženýrská informatika"], 0)
        + _ddlist("Rozevírací2",
                  ["Bezpečnostní technologie", "Softwarové inženýrství"], 0)
        + _ddlist("Rozevírací4", ["doporučuji", "nedoporučuji"], 0)
        + _ddlist("Rozevírací3", _GRADE_OPTIONS, 3)   # idx 3 = „C - dobře"
    )
    xml = f"<w:document {_W_NS}><w:body><w:p>{body}</w:p></w:body></w:document>"
    assert _grade_from_docx_xml(xml) == "C"


def test_grade_dropdown_unset_returns_none() -> None:
    """Nevyplněný dropdown (idx 0 = „vyberte hodnocení") → žádná známka."""
    body = _ddlist("Rozevírací3", _GRADE_OPTIONS, 0)
    xml = f"<w:document {_W_NS}><w:body><w:p>{body}</w:p></w:body></w:document>"
    assert _grade_from_docx_xml(xml) is None


def test_docx_dropdown_beats_conflicting_free_text(tmp_path: Path) -> None:
    """Celé .docx: dropdown „C" vyhraje nad volným textem „B-C"."""
    docx = tmp_path / "posudek.docx"
    body = (
        "<w:p><w:r><w:t>doporučuji k obhajobě s hodnocením B-C</w:t></w:r></w:p>"
        f"<w:p>{_ddlist('Rozevírací3', _GRADE_OPTIONS, 3)}</w:p>"
    )
    doc = f'<?xml version="1.0"?><w:document {_W_NS}><w:body>{body}</w:body></w:document>'
    with zipfile.ZipFile(docx, "w") as zf:
        zf.writestr("word/document.xml", doc)
    assert extract_grade_from_file(docx) == "C"


def test_extract_grade_unknown_suffix_returns_none(tmp_path: Path) -> None:
    other = tmp_path / "posudek.txt"
    other.write_text("navrhuji hodnocení A", encoding="utf-8")
    assert extract_grade_from_file(other) is None


def _make_text_pdf_bytes(text: str) -> bytes:
    """Minimální platné PDF s jedním Tj textem (Helvetica, ASCII)."""
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        None,  # doplní se níže (stream)
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    stream = b"BT /F1 24 Tf 72 700 Td (" + text.encode("latin-1") + b") Tj ET"
    objs[3] = b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream"
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objs, 1):
        offsets.append(len(out))
        out += str(i).encode() + b" 0 obj\n" + body + b"\nendobj\n"
    xref_pos = len(out)
    out += b"xref\n0 " + str(len(objs) + 1).encode() + b"\n0000000000 65535 f \n"
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += b"trailer\n<< /Size " + str(len(objs) + 1).encode() + b" /Root 1 0 R >>\n"
    out += b"startxref\n" + str(xref_pos).encode() + b"\n%%EOF"
    return bytes(out)


def test_extract_grade_from_encrypted_pdf(tmp_path: Path) -> None:
    """Posudky ze STAG jsou AES-šifrované — musí jít přečíst (pypdf[crypto])."""
    import io

    from pypdf import PdfReader, PdfWriter

    reader = PdfReader(io.BytesIO(_make_text_pdf_bytes("Proposed grade: B")))
    writer = PdfWriter()
    writer.append(reader)
    writer.encrypt("", algorithm="AES-128")   # jako STAG: prázdné heslo, AES
    out = tmp_path / "posudek.pdf"
    with out.open("wb") as f:
        writer.write(f)

    assert PdfReader(str(out)).is_encrypted
    assert extract_grade_from_file(out) == "B"
