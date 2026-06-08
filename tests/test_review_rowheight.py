"""Výška řádku pro dlouhý text v posudku — ať se v PDF (LibreOffice) neusekne."""

from __future__ import annotations

from pathlib import Path

from bpdpmanager.services.thesis_service import ThesisService
from bpdpmanager.services.xlsx_cell_writer import set_cells


def _make_xlsx(path: Path, *, cell: str = "B2", value: str = "x",
               merge: str | None = None, widths: dict | None = None) -> None:
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws[cell] = value
    if merge:
        ws.merge_cells(merge)
    for col, w in (widths or {}).items():
        ws.column_dimensions[col].width = w
    wb.save(path)


def test_set_cells_applies_row_height(tmp_path: Path) -> None:
    from openpyxl import load_workbook

    tpl = tmp_path / "t.xlsx"
    _make_xlsx(tpl, cell="A1", value="orig")
    out = tmp_path / "o.xlsx"
    set_cells(tpl, out, {"A1": "nový"}, row_heights={1: 180.0})
    ws = load_workbook(out).active
    assert ws["A1"].value == "nový"
    assert ws.row_dimensions[1].height == 180.0
    assert ws.row_dimensions[1].customHeight


def test_long_text_gets_tall_row(tmp_path: Path) -> None:
    tpl = tmp_path / "t.xlsx"
    _make_xlsx(tpl, merge="B2:E2",
               widths={"B": 20, "C": 20, "D": 20, "E": 20})
    heights = ThesisService._estimate_text_row_heights(tpl, {"B2": "x" * 600})
    assert 2 in heights
    assert heights[2] > 90  # ~8 radku po 15 bodech


def test_short_text_keeps_template_height(tmp_path: Path) -> None:
    tpl = tmp_path / "t.xlsx"
    _make_xlsx(tpl, merge="B2:E2",
               widths={"B": 20, "C": 20, "D": 20, "E": 20})
    assert ThesisService._estimate_text_row_heights(tpl, {"B2": "krátký"}) == {}


def test_explicit_newlines_count_as_lines(tmp_path: Path) -> None:
    tpl = tmp_path / "t.xlsx"
    _make_xlsx(tpl, merge="B2:E2",
               widths={"B": 20, "C": 20, "D": 20, "E": 20})
    # pět krátkých řádků díky \n → ≥ 3 řádky → výška se nastaví
    heights = ThesisService._estimate_text_row_heights(
        tpl, {"B2": "a\nb\nc\nd\ne"}
    )
    assert 2 in heights


def test_empty_text_cells_returns_empty(tmp_path: Path) -> None:
    tpl = tmp_path / "t.xlsx"
    _make_xlsx(tpl)
    assert ThesisService._estimate_text_row_heights(tpl, {}) == {}
