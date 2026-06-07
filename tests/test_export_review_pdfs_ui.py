"""Wiring exportu PDF posudků ve stromech (vedené / oponované práce).

Odděleno od ``test_export_review_pdfs.py`` (čistá logika helperu) — kombinace
mnoha čistě-logických testů těsně před stavbou velkého Qt widgetu ve stejném
procesu spolehlivě spouštěla GC segfault PySide6 při offscreen běhu.
"""

from __future__ import annotations

import os
from unittest import mock

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QAbstractItemView, QApplication


@pytest.fixture(scope="module")
def qapp():
    yield QApplication.instance() or QApplication([])


def test_supervised_tree_multiselect_export(qapp, tmp_path) -> None:
    """Strom vedených prací: extended selection + export jen prací s PDF."""
    from bpdpmanager.models import Student, Thesis
    from bpdpmanager.models.enums import AttachmentKind, ThesisStatus, ThesisType
    from bpdpmanager.services import ThesisService
    from bpdpmanager.storage import JsonRepository
    from bpdpmanager.ui.theses_tree import ROLE_THESIS_ID, ThesesTreeWidget

    repo = JsonRepository(
        path=tmp_path / "db.json", backup_path=tmp_path / "db.json.bak"
    )
    service = ThesisService(repo)
    s1 = Student(first_name="Jan", last_name="Novák")
    s2 = Student(first_name="Petr", last_name="Svoboda")
    service.upsert_student(s1)
    service.upsert_student(s2)
    t1 = Thesis(type=ThesisType.BP, status=ThesisStatus.IN_PROGRESS,
                academic_year="2024/2025", student_id=s1.id)
    t2 = Thesis(type=ThesisType.BP, status=ThesisStatus.IN_PROGRESS,
                academic_year="2024/2025", student_id=s2.id)
    service.upsert_thesis(t1)
    service.upsert_thesis(t2)
    # Jen Novák má vytvořené PDF posudku vedoucího.
    pdf = tmp_path / "Novak_posudek-vedouciho.pdf"
    pdf.write_bytes(b"%PDF-1")
    service.attach_document(t1.id, pdf, kind=AttachmentKind.SUPERVISOR_REVIEW)

    tree = ThesesTreeWidget(service)
    tree.refresh()
    assert tree.selectionMode() == QAbstractItemView.SelectionMode.ExtendedSelection
    # Export je defaultně vypnutý (zapíná se jen v „Aktuálně vedené práce").
    assert tree.enable_review_export is False

    def leaf(value):
        found = []

        def walk(item):
            for i in range(item.childCount()):
                walk(item.child(i))
            if item.data(0, ROLE_THESIS_ID) == value:
                found.append(item)

        root = tree.invisibleRootItem()
        for i in range(root.childCount()):
            walk(root.child(i))
        return found[0]

    leaf(t1.id).setSelected(True)
    leaf(t2.id).setSelected(True)

    dest = tmp_path / "dest"
    dest.mkdir()
    with mock.patch(
        "bpdpmanager.ui.export_reviews.QFileDialog.getExistingDirectory",
        return_value=str(dest),
    ), mock.patch("bpdpmanager.ui.export_reviews.QMessageBox.information") as info:
        tree._export_my_review_pdfs()
        summary = info.call_args[0][2]

    copied = list(dest.iterdir())
    assert len(copied) == 1
    assert copied[0].name.startswith("Novák") and copied[0].suffix == ".pdf"
    assert "Exportováno 1" in summary
    assert "Petr Svoboda" in summary  # přeskočen (bez PDF)


def test_opposing_tab_multiselect_export(qapp, tmp_path) -> None:
    """Záložka oponentur: extended selection + export PDF oponentského posudku."""
    from bpdpmanager.models import OpposingThesis
    from bpdpmanager.models.enums import AttachmentKind, ThesisType
    from bpdpmanager.services import ThesisService
    from bpdpmanager.storage import JsonRepository
    from bpdpmanager.ui.opposing_tab import ROLE_ID, OpposingTab

    repo = JsonRepository(
        path=tmp_path / "db.json", backup_path=tmp_path / "db.json.bak"
    )
    service = ThesisService(repo)
    year = service.current_academic_year()
    op1 = OpposingThesis(type=ThesisType.BP, academic_year=year,
                         student_first_name="Jan", student_last_name="Novák",
                         title_cs="A")
    op2 = OpposingThesis(type=ThesisType.BP, academic_year=year,
                         student_first_name="Petr", student_last_name="Svoboda",
                         title_cs="B")
    service.upsert_opposing_thesis(op1)
    service.upsert_opposing_thesis(op2)
    pdf = tmp_path / "Novak_posudek-oponenta.pdf"
    pdf.write_bytes(b"%PDF-1")
    service.opposing_attach_document(
        op1.id, pdf, kind=AttachmentKind.OPPONENT_REVIEW
    )

    tab = OpposingTab(service)
    tab.refresh()
    assert (
        tab.tree.selectionMode()
        == QAbstractItemView.SelectionMode.ExtendedSelection
    )

    found = []

    def walk(item):
        for i in range(item.childCount()):
            walk(item.child(i))
        if item.data(0, ROLE_ID):
            found.append(item)

    root = tab.tree.invisibleRootItem()
    for i in range(root.childCount()):
        walk(root.child(i))
    for it in found:
        it.setSelected(True)
    assert len(found) == 2

    dest = tmp_path / "dest"
    dest.mkdir()
    with mock.patch(
        "bpdpmanager.ui.export_reviews.QFileDialog.getExistingDirectory",
        return_value=str(dest),
    ), mock.patch("bpdpmanager.ui.export_reviews.QMessageBox.information") as info:
        tab._export_my_review_pdfs()
        summary = info.call_args[0][2]

    copied = list(dest.iterdir())
    assert len(copied) == 1 and copied[0].name.startswith("Novák")
    assert "Exportováno 1" in summary
    assert "Petr Svoboda" in summary
