"""Testy zploštění „obrázku v buňce" (Excel rich-value image) na drawing."""

from __future__ import annotations

import zipfile
from pathlib import Path

from bpdpmanager.services.xlsx_image_in_cell import (
    flatten_image_in_cell,
    has_image_in_cell,
)

# Nejmensi validni GIF (1x1) — staci PIL pro zjisteni rozmeru.
_TINY_GIF = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!"
    b"\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
)

_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_XLRD = "http://schemas.microsoft.com/office/spreadsheetml/2017/richdata"
_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_PKG = "http://schemas.openxmlformats.org/package/2006/relationships"


def _fixture_parts() -> dict[str, bytes]:
    sheet = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<worksheet xmlns="{_MAIN}" xmlns:r="{_REL}">'
        '<sheetFormatPr defaultRowHeight="15" defaultColWidth="8.43"/>'
        '<cols><col min="1" max="1" width="27.5" customWidth="1"/>'
        '<col min="2" max="4" width="10" customWidth="1"/></cols>'
        '<sheetData><row r="1">'
        '<c r="A1" s="0" t="e" vm="1"><v>#VALUE!</v></c>'
        '</row></sheetData>'
        '<mergeCells count="1"><mergeCell ref="A1:D4"/></mergeCells>'
        '<pageSetup paperSize="9" orientation="portrait"/>'
        '</worksheet>'
    )
    metadata = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<metadata xmlns="{_MAIN}" xmlns:xlrd="{_XLRD}">'
        '<metadataTypes count="1"><metadataType name="XLRICHVALUE"/></metadataTypes>'
        '<futureMetadata name="XLRICHVALUE" count="1"><bk><extLst>'
        '<ext uri="{3e2802c4-a4d2-4d8b-9148-e3be6c30e623}"><xlrd:rvb i="0"/></ext>'
        '</extLst></bk></futureMetadata>'
        '<valueMetadata count="1"><bk><rc t="1" v="0"/></bk></valueMetadata></metadata>'
    )
    struct = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<rvStructures xmlns="{_XLRD}" count="1"><s t="_localImage">'
        '<k n="_rvRel:LocalImageIdentifier" t="i"/><k n="CalcOrigin" t="i"/>'
        '</s></rvStructures>'
    )
    rv = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<rvData xmlns="{_XLRD}" count="1"><rv s="0"><v>0</v><v>5</v></rv></rvData>'
    )
    rvrel = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<richValueRels xmlns="http://schemas.microsoft.com/office/spreadsheetml/2022/richvaluerel" '
        f'xmlns:r="{_REL}"><rel r:id="rId1"/></richValueRels>'
    )
    rvrel_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<Relationships xmlns="{_PKG}"><Relationship Id="rId1" '
        f'Type="{_REL}/image" Target="../media/image1.gif"/></Relationships>'
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="gif" ContentType="image/gif"/>'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '</Types>'
    )
    return {
        "[Content_Types].xml": content_types.encode(),
        "xl/worksheets/sheet1.xml": sheet.encode(),
        "xl/metadata.xml": metadata.encode(),
        "xl/richData/rdrichvaluestructure.xml": struct.encode(),
        "xl/richData/rdrichvalue.xml": rv.encode(),
        "xl/richData/richValueRel.xml": rvrel.encode(),
        "xl/richData/_rels/richValueRel.xml.rels": rvrel_rels.encode(),
        "xl/media/image1.gif": _TINY_GIF,
    }


def _build_fixture(path: Path) -> None:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in _fixture_parts().items():
            z.writestr(name, data)


def test_has_image_in_cell_detects_richvalue() -> None:
    assert has_image_in_cell(_fixture_parts()) is True
    assert has_image_in_cell({"xl/worksheets/sheet1.xml": b"<x/>"}) is False


def test_flatten_converts_to_drawing_and_clears_error(tmp_path: Path) -> None:
    src = tmp_path / "in.xlsx"
    dst = tmp_path / "out.xlsx"
    _build_fixture(src)

    changed = flatten_image_in_cell(src, dst)
    assert changed is True

    with zipfile.ZipFile(dst) as z:
        names = z.namelist()
        sheet = z.read("xl/worksheets/sheet1.xml").decode()
        drawing = z.read("xl/drawings/drawing1.xml").decode()
        drawing_rels = z.read("xl/drawings/_rels/drawing1.xml.rels").decode()
        ct = z.read("[Content_Types].xml").decode()
        sheet_rels = z.read("xl/worksheets/_rels/sheet1.xml.rels").decode()

    # #VALUE! je pryč a A1 si zachovala styl
    assert "#VALUE!" not in sheet
    assert '<c r="A1" s="0"/>' in sheet
    # list odkazuje na drawing
    assert "<drawing r:id=" in sheet
    assert "/drawing" in sheet_rels
    # drawing odkazuje na obrázek
    assert "r:embed=" in drawing
    assert "image1.gif" in drawing_rels
    # content types ví o drawing partu
    assert "/xl/drawings/drawing1.xml" in ct
    assert "xl/drawings/drawing1.xml" in names


def test_flatten_noop_when_no_image_in_cell(tmp_path: Path) -> None:
    src = tmp_path / "plain.xlsx"
    dst = tmp_path / "plain_out.xlsx"
    with zipfile.ZipFile(src, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", b"<Types></Types>")
        z.writestr("xl/worksheets/sheet1.xml", b"<worksheet/>")

    changed = flatten_image_in_cell(src, dst)
    assert changed is False
    assert dst.exists()  # kopie i tak vznikne
