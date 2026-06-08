"""Multi-select hromadné akce v kontextovém menu stromu prací + STAG subset."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from bpdpmanager.models import Student, Thesis
from bpdpmanager.models.enums import ThesisStatus, ThesisType
from bpdpmanager.services import ThesisService
from bpdpmanager.storage import JsonRepository
from bpdpmanager.ui.theses_tree import ROLE_THESIS_ID, ThesesTreeWidget


@pytest.fixture(scope="module")
def qapp():
    yield QApplication.instance() or QApplication([])


def _two_theses(service):
    s = Student(first_name="Jan", last_name="Novák")
    service.upsert_student(s)
    ids = []
    for _ in range(2):
        t = Thesis(type=ThesisType.BP, status=ThesisStatus.IN_PROGRESS,
                   academic_year="2024/2025", student_id=s.id)
        service.upsert_thesis(t)
        ids.append(t.id)
    return ids


def _leaves(tree):
    out = []

    def walk(item):
        for i in range(item.childCount()):
            walk(item.child(i))
        if item.data(0, ROLE_THESIS_ID):
            out.append(item)

    root = tree.invisibleRootItem()
    for i in range(root.childCount()):
        walk(root.child(i))
    return out


def _action(menu, needle):
    for a in menu.actions():
        if needle in a.text():
            return a
    raise AssertionError(f"akce '{needle}' nenalezena")


def test_multi_mark_sent_emits_all_ids(qapp, tmp_path) -> None:
    repo = JsonRepository(path=tmp_path / "db.json", backup_path=tmp_path / "db.json.bak")
    service = ThesisService(repo)
    ids = _two_theses(service)

    tree = ThesesTreeWidget(service)
    tree.refresh()
    leaves = _leaves(tree)
    for it in leaves:
        it.setSelected(True)

    captured = {}
    tree.mark_reviews_sent_requested.connect(
        lambda v, sent: captured.update(ids=v, sent=sent)
    )
    menu = tree._build_context_menu(leaves[0])
    _action(menu, "Označit posudky za odeslané").trigger()

    assert captured["sent"] is True
    assert sorted(captured["ids"]) == sorted(ids)


def test_multi_rollback_emits_all_ids(qapp, tmp_path) -> None:
    repo = JsonRepository(path=tmp_path / "db.json", backup_path=tmp_path / "db.json.bak")
    service = ThesisService(repo)
    ids = _two_theses(service)

    tree = ThesesTreeWidget(service)
    tree.refresh()
    leaves = _leaves(tree)
    for it in leaves:
        it.setSelected(True)

    captured = {}
    tree.rollback_many_requested.connect(lambda v: captured.update(ids=v))
    menu = tree._build_context_menu(leaves[0])
    _action(menu, "Roll-back").trigger()
    assert sorted(captured["ids"]) == sorted(ids)


def test_stag_sync_subset_collects_only_selected(qapp, tmp_path) -> None:
    from bpdpmanager.ui.stag_sync_dialog import ROLE_SUPERVISOR, StagSyncDialog

    repo = JsonRepository(path=tmp_path / "db.json", backup_path=tmp_path / "db.json.bak")
    service = ThesisService(repo)
    ids = _two_theses(service)
    # třetí práce, kterou do subsetu NEdáme
    s = service.get_student(service.list_students()[0].id)
    t3 = Thesis(type=ThesisType.DP, status=ThesisStatus.IN_PROGRESS,
                academic_year="2024/2025", student_id=s.id)
    service.upsert_thesis(t3)

    dlg = StagSyncDialog(service, ROLE_SUPERVISOR, subset=[ids[0]])
    targets = dlg._collect_targets()
    assert [t.obj_id for t in targets] == [ids[0]]
