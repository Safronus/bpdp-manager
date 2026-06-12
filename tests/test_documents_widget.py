"""Test: DocumentsWidget umí vedené práce i oponentury (stejný agregovaný strom)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from bpdpmanager.models import Attachment, OpposingThesis, Thesis  # noqa: E402
from bpdpmanager.models.enums import AttachmentKind, ThesisType  # noqa: E402
from bpdpmanager.services import ThesisService  # noqa: E402
from bpdpmanager.storage import JsonRepository  # noqa: E402
from bpdpmanager.ui.widgets import DocumentsWidget  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    yield QApplication.instance() or QApplication([])


@pytest.fixture
def service(tmp_path: Path) -> ThesisService:
    repo = JsonRepository(path=tmp_path / "db.json", backup_path=tmp_path / "db.json.bak")
    return ThesisService(repo)


def test_thesis_mode(qapp, service: ThesisService) -> None:
    t = Thesis(type=ThesisType.BP, academic_year="2025/2026")
    t.attachments = [
        Attachment(label="t.pdf", url_or_path="text/t.pdf",
                   kind=AttachmentKind.THESIS_TEXT, is_file=True),
    ]
    service.upsert_thesis(t)

    w = DocumentsWidget(service)
    w.set_thesis_id(t.id)
    assert w.opposing is False
    assert w._get_work().id == t.id
    assert w.tree.topLevelItemCount() == 1  # 1 skupina (Text práce)


def test_opposing_mode_routes_to_opposing_service(qapp, service: ThesisService) -> None:
    op = OpposingThesis(type=ThesisType.DP, academic_year="2025/2026")
    op.attachments = [
        Attachment(label="o.xlsx", url_or_path="posudky/o.xlsx",
                   kind=AttachmentKind.OPPONENT_REVIEW, is_file=True),
        Attachment(label="text.pdf", url_or_path="text/text.pdf",
                   kind=AttachmentKind.THESIS_TEXT, is_file=True),
    ]
    service.upsert_opposing_thesis(op)

    w = DocumentsWidget(service)
    w.set_opposing_id(op.id)
    assert w.opposing is True
    assert w._get_work().id == op.id
    # 2 skupiny (Text práce + Posudek oponenta)
    assert w.tree.topLevelItemCount() == 2
    # absolutní cesta míří do documents/opposing-{id}/
    abs_path = w._abs_path(op.attachments[0])
    assert abs_path is not None and f"opposing-{op.id}" in str(abs_path)


def test_bulk_remove_and_column_stretch(qapp, service: ThesisService, tmp_path) -> None:
    """Hromadné odebrání více vybraných souborů + poslední sloupec se roztáhne."""
    from unittest import mock

    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QHeaderView, QMessageBox

    t = Thesis(type=ThesisType.BP, academic_year="2025/2026")
    service.upsert_thesis(t)
    for name in ("a.zip", "b.zip", "c.zip"):
        p = tmp_path / name
        p.write_bytes(name.encode() * 50)
        service.attach_document(t.id, p, kind=AttachmentKind.THESIS_APPENDIX, label=name)

    w = DocumentsWidget(service)
    w.set_thesis_id(t.id)

    # poslední sloupec (cesta) se roztahuje, ať za ním není prázdné místo
    assert w.tree.header().sectionResizeMode(4) == QHeaderView.ResizeMode.Stretch

    leaves: list = []

    def walk(item):
        for i in range(item.childCount()):
            walk(item.child(i))
        if isinstance(item.data(0, Qt.ItemDataRole.UserRole), int):
            leaves.append(item)

    walk(w.tree.invisibleRootItem())
    for it in leaves:
        it.setSelected(True)
    assert w._selected_indices() == [0, 1, 2]

    with mock.patch.object(
        QMessageBox, "question", return_value=QMessageBox.StandardButton.No
    ):
        w._remove_many_selected()
    assert [a for a in service.get_thesis(t.id).attachments if a.is_file] == []


def test_open_selected_opens_all_selected(qapp, service: ThesisService, tmp_path) -> None:
    """Kontextová akce „Otevřít" otevře VŠECHNY vybrané dokumenty, ne jen jeden."""
    from unittest import mock

    from PySide6.QtCore import Qt

    t = Thesis(type=ThesisType.BP, academic_year="2025/2026")
    service.upsert_thesis(t)
    for name in ("a.pdf", "b.pdf", "c.pdf"):
        p = tmp_path / name
        p.write_bytes(name.encode() * 50)
        service.attach_document(t.id, p, kind=AttachmentKind.THESIS_APPENDIX, label=name)

    w = DocumentsWidget(service)
    w.set_thesis_id(t.id)

    leaves: list = []

    def walk(item):
        for i in range(item.childCount()):
            walk(item.child(i))
        if isinstance(item.data(0, Qt.ItemDataRole.UserRole), int):
            leaves.append(item)

    walk(w.tree.invisibleRootItem())
    assert len(leaves) == 3
    for it in leaves:
        it.setSelected(True)

    opened: list = []
    with mock.patch(
        "bpdpmanager.ui.widgets.documents_widget.open_path",
        side_effect=lambda p: opened.append(p),
    ):
        w._open_selected()

    # Všechny tři soubory se otevřely (dříve jen jeden = currentItem) — tři
    # různé existující cesty (názvy přejmenoval attach_document).
    assert len(opened) == 3
    assert len({str(p) for p in opened}) == 3
    assert all(Path(p).exists() for p in opened)
