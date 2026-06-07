"""Testy ručního označení odeslání posudku + indikátoru v seznamu prací."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from bpdpmanager.models import OpposingThesis, Thesis  # noqa: E402
from bpdpmanager.models.enums import AttachmentKind, ThesisStatus, ThesisType  # noqa: E402
from bpdpmanager.services import ThesisService  # noqa: E402
from bpdpmanager.storage import JsonRepository  # noqa: E402
from bpdpmanager.ui.theses_tree import ThesesTreeWidget  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    yield QApplication.instance() or QApplication([])


@pytest.fixture
def service(tmp_path: Path) -> ThesisService:
    repo = JsonRepository(path=tmp_path / "db.json", backup_path=tmp_path / "db.json.bak")
    return ThesisService(repo)


def test_set_sent_toggle(service: ThesisService) -> None:
    t = Thesis(type=ThesisType.BP, academic_year="2024/2025", status=ThesisStatus.IN_PROGRESS)
    service.upsert_thesis(t)
    service.set_supervisor_review_sent(t.id, True)
    assert service.get_thesis(t.id).supervisor_review_sent_at is not None
    service.set_supervisor_review_sent(t.id, False)
    assert service.get_thesis(t.id).supervisor_review_sent_at is None

    op = OpposingThesis(type=ThesisType.BP, academic_year="2024/2025")
    service.upsert_opposing_thesis(op)
    service.set_opponent_review_sent(op.id, True)
    assert service.get_opposing_thesis(op.id).opponent_review_sent_at is not None


def test_tree_sent_indicator(qapp, service: ThesisService, tmp_path: Path) -> None:
    t = Thesis(type=ThesisType.BP, academic_year="2024/2025", status=ThesisStatus.IN_PROGRESS)
    service.upsert_thesis(t)
    # „done" posudek = nahraný soubor posudku vedoucího.
    src = tmp_path / "pv.pdf"
    src.write_bytes(b"%PDF dummy")
    service.attach_document(t.id, src, kind=AttachmentKind.SUPERVISOR_REVIEW)

    tree = ThesesTreeWidget(service)
    tree.set_filter(lambda th: True)

    def _sent_leaf():
        for i in range(tree.topLevelItemCount()):
            yr = tree.topLevelItem(i)
            for j in range(yr.childCount()):
                grp = yr.child(j)
                for k in range(grp.childCount()):
                    return grp.child(k)
        return None

    from bpdpmanager.models.enums import SENT_BG, UNSENT_BG

    leaf = _sent_leaf()
    # Obálka + barva pozadí (červená = neodesláno).
    assert leaf.text(tree.COL_SENT) == "✉"
    assert leaf.background(tree.COL_SENT).color().name() == UNSENT_BG

    service.set_supervisor_review_sent(t.id, True)
    tree.refresh()
    leaf = _sent_leaf()
    assert leaf.background(tree.COL_SENT).color().name() == SENT_BG  # zelená = odesláno
