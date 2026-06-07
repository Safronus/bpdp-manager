"""Hromadný export PDF mých posudků (vedoucího / oponenta) do složky."""

from __future__ import annotations

import os
from pathlib import Path
from unittest import mock

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from bpdpmanager.ui.export_reviews import export_my_review_pdfs


@pytest.fixture(scope="module")
def qapp():
    yield QApplication.instance() or QApplication([])


def _make_pdf(folder: Path, name: str, data: bytes = b"%PDF-1") -> Path:
    p = folder / name
    p.write_bytes(data)
    return p


def test_exports_existing_and_skips_missing(qapp, tmp_path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    dest = tmp_path / "dest"
    dest.mkdir()
    pdf1 = _make_pdf(src, "Novak_posudek.pdf")
    pdf2 = _make_pdf(src, "Svoboda_posudek.pdf")
    jobs = [("Jan Novák", pdf1), ("Petr Svoboda", pdf2), ("Eva Dvořáková", None)]

    with mock.patch(
        "bpdpmanager.ui.export_reviews.QFileDialog.getExistingDirectory",
        return_value=str(dest),
    ), mock.patch("bpdpmanager.ui.export_reviews.QMessageBox.information") as info:
        export_my_review_pdfs(None,jobs)
        summary = info.call_args[0][2]

    assert sorted(p.name for p in dest.iterdir()) == [
        "Novak_posudek.pdf",
        "Svoboda_posudek.pdf",
    ]
    assert "Exportováno 2" in summary
    assert "Přeskočeno (bez PDF posudku): 1" in summary
    assert "Eva Dvořáková" in summary


def test_collision_overwrites(qapp, tmp_path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    dest = tmp_path / "dest"
    dest.mkdir()
    pdf = _make_pdf(src, "Novak_posudek.pdf", b"%PDF-NEW")
    (dest / "Novak_posudek.pdf").write_bytes(b"OLD")

    with mock.patch(
        "bpdpmanager.ui.export_reviews.QFileDialog.getExistingDirectory",
        return_value=str(dest),
    ), mock.patch("bpdpmanager.ui.export_reviews.QMessageBox.information"):
        export_my_review_pdfs(None,[("Jan Novák", pdf)])

    assert (dest / "Novak_posudek.pdf").read_bytes() == b"%PDF-NEW"


def test_no_pdf_does_not_open_folder_dialog(qapp, tmp_path) -> None:
    with mock.patch(
        "bpdpmanager.ui.export_reviews.QFileDialog.getExistingDirectory"
    ) as gd, mock.patch(
        "bpdpmanager.ui.export_reviews.QMessageBox.information"
    ) as info:
        export_my_review_pdfs(None,[("X", None)])
    assert gd.called is False
    assert "není co exportovat" in info.call_args[0][2]


def test_empty_jobs(qapp) -> None:
    with mock.patch(
        "bpdpmanager.ui.export_reviews.QFileDialog.getExistingDirectory"
    ) as gd, mock.patch(
        "bpdpmanager.ui.export_reviews.QMessageBox.information"
    ) as info:
        export_my_review_pdfs(None,[])
    assert gd.called is False
    assert "Nevybrali jste žádnou práci" in info.call_args[0][2]


def test_cancelled_folder_dialog_copies_nothing(qapp, tmp_path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    pdf = _make_pdf(src, "Novak_posudek.pdf")
    with mock.patch(
        "bpdpmanager.ui.export_reviews.QFileDialog.getExistingDirectory",
        return_value="",
    ), mock.patch("bpdpmanager.ui.export_reviews.QMessageBox.information") as info:
        export_my_review_pdfs(None,[("Jan Novák", pdf)])
    # Žádný souhrn (uživatel zrušil výběr složky).
    assert info.called is False
