"""Testy kosmetiky PDF kopie (vyvážené okraje + hlavička „Body")."""

from __future__ import annotations

import re
import shutil
import zipfile
from pathlib import Path

from bpdpmanager.services.default_data import default_templates_dir
from bpdpmanager.services.xlsx_pdf_polish import polish_pdf_layout


def test_polish_real_template_widens_and_restyles(tmp_path: Path) -> None:
    src = next(default_templates_dir().glob("*.xlsx"))
    dst = tmp_path / "polished.xlsx"
    shutil.copy(src, dst)

    polish_pdf_layout(dst)

    # soubor je stále validní ZIP / XLSX
    with zipfile.ZipFile(dst) as z:
        sheet = z.read("xl/worksheets/sheet1.xml").decode("utf-8")
        workbook = z.read("xl/workbook.xml").decode("utf-8")
        styles = z.read("xl/styles.xml").decode("utf-8")

    # 1) měřítko tisku >100 % (tabulka se roztáhne na šířku)
    m = re.search(r'<pageSetup[^>]*\bscale="(\d+)"', sheet)
    assert m is not None and int(m.group(1)) > 100
    # 2) oblast tisku omezená na sloupce s obsahem (A1:D…)
    assert "_xlnm.Print_Area" in workbook and "$A$1:$D$" in workbook
    # 3) hlavička „Body" dostala černý font (přibyl černý color do fonts)
    assert "FF000000" in styles


def test_polish_is_idempotent_and_safe(tmp_path: Path) -> None:
    src = next(default_templates_dir().glob("*.xlsx"))
    dst = tmp_path / "p.xlsx"
    shutil.copy(src, dst)
    polish_pdf_layout(dst)
    polish_pdf_layout(dst)  # druhý běh nesmí rozbít soubor ani zdvojit nastavení
    with zipfile.ZipFile(dst) as z:
        sheet = z.read("xl/worksheets/sheet1.xml").decode("utf-8")
        workbook = z.read("xl/workbook.xml").decode("utf-8")
    assert sheet.count("scale=") == 1
    assert workbook.count("_xlnm.Print_Area") == 1


def test_polish_missing_file_is_noop(tmp_path: Path) -> None:
    # neexistující soubor → bez výjimky
    polish_pdf_layout(tmp_path / "neexistuje.xlsx")
