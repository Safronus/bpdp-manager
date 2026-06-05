"""Testy kosmetiky PDF kopie (vyvážené okraje + hlavička „Body")."""

from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

from bpdpmanager.services.default_data import default_templates_dir
from bpdpmanager.services.xlsx_pdf_polish import polish_pdf_layout


def test_polish_real_template_centers_and_restyles(tmp_path: Path) -> None:
    src = next(default_templates_dir().glob("*.xlsx"))
    dst = tmp_path / "polished.xlsx"
    shutil.copy(src, dst)

    polish_pdf_layout(dst)

    # soubor je stále validní ZIP / XLSX
    with zipfile.ZipFile(dst) as z:
        sheet = z.read("xl/worksheets/sheet1.xml").decode("utf-8")
        styles = z.read("xl/styles.xml").decode("utf-8")

    # 1) vyvážené okraje
    assert "horizontalCentered" in sheet
    # 2) hlavička „Body" dostala černý font (přibyl černý color do fonts)
    assert "FF000000" in styles


def test_polish_is_idempotent_and_safe(tmp_path: Path) -> None:
    src = next(default_templates_dir().glob("*.xlsx"))
    dst = tmp_path / "p.xlsx"
    shutil.copy(src, dst)
    polish_pdf_layout(dst)
    # druhý běh nesmí rozbít soubor ani zdvojit horizontalCentered
    polish_pdf_layout(dst)
    with zipfile.ZipFile(dst) as z:
        sheet = z.read("xl/worksheets/sheet1.xml").decode("utf-8")
    assert sheet.count("horizontalCentered") == 1


def test_polish_missing_file_is_noop(tmp_path: Path) -> None:
    # neexistující soubor → bez výjimky
    polish_pdf_layout(tmp_path / "neexistuje.xlsx")
