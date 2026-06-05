"""Testy kosmetiky PDF kopie (vyvážené okraje + hlavička „Body")."""

from __future__ import annotations

import re
import shutil
import zipfile
from pathlib import Path

from bpdpmanager.services.default_data import default_templates_dir
from bpdpmanager.services.xlsx_pdf_polish import polish_pdf_layout


def _first_col_width(sheet_xml: str) -> float:
    m = re.search(r'<col min="1"[^>]*?width="([0-9.]+)"', sheet_xml)
    return float(m.group(1)) if m else 0.0


def test_polish_real_template_widens_and_restyles(tmp_path: Path) -> None:
    src = next(default_templates_dir().glob("*.xlsx"))
    dst = tmp_path / "polished.xlsx"
    shutil.copy(src, dst)

    with zipfile.ZipFile(src) as z:
        orig_width = _first_col_width(z.read("xl/worksheets/sheet1.xml").decode("utf-8"))

    polish_pdf_layout(dst)

    # soubor je stále validní ZIP / XLSX
    with zipfile.ZipFile(dst) as z:
        sheet = z.read("xl/worksheets/sheet1.xml").decode("utf-8")
        workbook = z.read("xl/workbook.xml").decode("utf-8")
        styles = z.read("xl/styles.xml").decode("utf-8")

    # 1) sloupce tabulky roztažené na šířku (NE měřítkem — výška/strany beze změny)
    assert _first_col_width(sheet) > orig_width
    assert "scale=" not in sheet
    # 2) oblast tisku omezená na sloupce s obsahem (A1:D…)
    assert "_xlnm.Print_Area" in workbook and "$A$1:$D$" in workbook
    # 3) hlavička „Body" dostala černý font (přibyl černý color do fonts)
    assert "FF000000" in styles


def test_polish_is_idempotent_and_safe(tmp_path: Path) -> None:
    src = next(default_templates_dir().glob("*.xlsx"))
    dst = tmp_path / "p.xlsx"
    shutil.copy(src, dst)
    polish_pdf_layout(dst)
    with zipfile.ZipFile(dst) as z:
        width_after_first = _first_col_width(
            z.read("xl/worksheets/sheet1.xml").decode("utf-8")
        )
    polish_pdf_layout(dst)  # druhý běh nesmí rozbít soubor ani znovu roztáhnout
    with zipfile.ZipFile(dst) as z:
        sheet = z.read("xl/worksheets/sheet1.xml").decode("utf-8")
        workbook = z.read("xl/workbook.xml").decode("utf-8")
    assert _first_col_width(sheet) == width_after_first  # neroztáhlo se podruhé
    assert workbook.count("_xlnm.Print_Area") == 1


def test_polish_missing_file_is_noop(tmp_path: Path) -> None:
    # neexistující soubor → bez výjimky
    polish_pdf_layout(tmp_path / "neexistuje.xlsx")
