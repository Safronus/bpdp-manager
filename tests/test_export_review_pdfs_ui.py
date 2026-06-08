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


def _labels(menu):
    return [a.text() for a in menu.actions() if not a.isSeparator()]


def test_supervised_menu_single_vs_multi(qapp, tmp_path) -> None:
    """Vedené práce: u jedné vybrané plné menu, u více jen hromadný export."""
    from bpdpmanager.models import Student, Thesis
    from bpdpmanager.models.enums import ThesisStatus, ThesisType
    from bpdpmanager.services import ThesisService
    from bpdpmanager.storage import JsonRepository
    from bpdpmanager.ui.theses_tree import ROLE_THESIS_ID, ThesesTreeWidget

    repo = JsonRepository(
        path=tmp_path / "db.json", backup_path=tmp_path / "db.json.bak"
    )
    service = ThesisService(repo)
    s = Student(first_name="Jan", last_name="Novák")
    service.upsert_student(s)
    t1 = Thesis(type=ThesisType.BP, status=ThesisStatus.IN_PROGRESS,
                academic_year="2024/2025", student_id=s.id)
    t2 = Thesis(type=ThesisType.BP, status=ThesisStatus.IN_PROGRESS,
                academic_year="2024/2025", student_id=s.id)
    service.upsert_thesis(t1)
    service.upsert_thesis(t2)

    tree = ThesesTreeWidget(service)
    tree.enable_review_export = True
    tree.refresh()

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

    l1 = leaf(t1.id)
    l1.setSelected(True)
    single = _labels(tree._build_context_menu(l1))
    assert len(single) > 1
    assert any("Export PDF" in x for x in single)
    assert any("Roll-back" in x for x in single)

    leaf(t2.id).setSelected(True)
    multi = _labels(tree._build_context_menu(l1))
    # Multi-select: hromadný export + hromadné akce nad vybranými.
    assert any("Export PDF" in x for x in multi)
    assert any("Aktualizace 2 prací ze STAG" in x for x in multi)
    assert any("Otevřít texty prací" in x for x in multi)
    assert any("Označit posudky za odeslané" in x for x in multi)
    assert any("Roll-back" in x and "2 prací" in x for x in multi)


def test_supervised_menu_multi_empty_without_export(qapp, tmp_path) -> None:
    """Mimo „Aktuálně vedené" (export vypnutý) je u více vybraných menu prázdné."""
    from bpdpmanager.models import Student, Thesis
    from bpdpmanager.models.enums import ThesisStatus, ThesisType
    from bpdpmanager.services import ThesisService
    from bpdpmanager.storage import JsonRepository
    from bpdpmanager.ui.theses_tree import ROLE_THESIS_ID, ThesesTreeWidget

    repo = JsonRepository(
        path=tmp_path / "db.json", backup_path=tmp_path / "db.json.bak"
    )
    service = ThesisService(repo)
    s = Student(first_name="Jan", last_name="Novák")
    service.upsert_student(s)
    t1 = Thesis(type=ThesisType.BP, status=ThesisStatus.IN_PROGRESS,
                academic_year="2024/2025", student_id=s.id)
    t2 = Thesis(type=ThesisType.BP, status=ThesisStatus.IN_PROGRESS,
                academic_year="2024/2025", student_id=s.id)
    service.upsert_thesis(t1)
    service.upsert_thesis(t2)

    tree = ThesesTreeWidget(service)  # enable_review_export zůstává False
    tree.refresh()

    leaves = []

    def walk(item):
        for i in range(item.childCount()):
            walk(item.child(i))
        if item.data(0, ROLE_THESIS_ID):
            leaves.append(item)

    root = tree.invisibleRootItem()
    for i in range(root.childCount()):
        walk(root.child(i))
    for it in leaves:
        it.setSelected(True)
    labels = _labels(tree._build_context_menu(leaves[0]))
    # Bez exportu (mimo „Aktuálně vedené") nabízí multi-select hromadné akce,
    # ale NE export PDF posudků.
    assert not any("Export PDF" in x for x in labels)
    assert any("Aktualizace 2 prací ze STAG" in x for x in labels)
    assert any("Roll-back" in x and "2 prací" in x for x in labels)


def test_opposing_menu_single_vs_multi(qapp, tmp_path) -> None:
    """Oponentury: u jedné vybrané plné menu, u více jen hromadný export."""
    from bpdpmanager.models import OpposingThesis
    from bpdpmanager.models.enums import ThesisType
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

    tab = OpposingTab(service)
    tab.refresh()

    found = []

    def walk(item):
        for i in range(item.childCount()):
            walk(item.child(i))
        if item.data(0, ROLE_ID):
            found.append(item)

    root = tab.tree.invisibleRootItem()
    for i in range(root.childCount()):
        walk(root.child(i))

    found[0].setSelected(True)
    single = _labels(tab._build_context_menu(found[0].data(0, ROLE_ID)))
    assert len(single) > 1
    assert any("Export PDF" in x for x in single)

    for it in found:
        it.setSelected(True)
    multi = _labels(tab._build_context_menu(found[0].data(0, ROLE_ID)))
    assert any("Export PDF" in x for x in multi)
    assert any("Aktualizace 2 prací ze STAG" in x for x in multi)
    assert any("Roll-back" in x and "2 prací" in x for x in multi)


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
