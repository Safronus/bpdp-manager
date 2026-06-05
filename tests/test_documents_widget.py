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
