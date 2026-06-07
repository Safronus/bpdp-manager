"""Test přesunu oponenta mezi Interní / Externí (drag&drop handler)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from bpdpmanager.models import Opponent
from bpdpmanager.models.enums import OpponentKind
from bpdpmanager.services import ThesisService
from bpdpmanager.storage import JsonRepository
from bpdpmanager.ui.manage_dialogs import (
    OpponentsManageDialog,
    StudentsManageDialog,
)


@pytest.fixture(scope="module")
def qapp():
    yield QApplication.instance() or QApplication([])


@pytest.fixture
def service(tmp_path: Path) -> ThesisService:
    repo = JsonRepository(path=tmp_path / "db.json", backup_path=tmp_path / "db.json.bak")
    return ThesisService(repo)


def test_opponent_work_count_column(qapp, service) -> None:
    """Správce oponentů ukazuje počet prací, které oponent oponuje."""
    from bpdpmanager.models import Student, Thesis
    from bpdpmanager.models.enums import ThesisType

    o = Opponent(name="Jan Novák", kind=OpponentKind.INTERNAL)
    service.upsert_opponent(o)
    s = Student(first_name="A", last_name="B")
    service.upsert_student(s)
    for _ in range(2):
        service.upsert_thesis(Thesis(type=ThesisType.BP, academic_year="2024/2025",
                                     student_id=s.id, opponent_id=o.id))

    dlg = OpponentsManageDialog(service)

    def _leaf_for(opp_id):
        # Strom: skupina (Interní/Externí) → podskupina (Pracoviště) → list.
        stack = [dlg.tree.invisibleRootItem()]
        while stack:
            item = stack.pop()
            for j in range(item.childCount()):
                child = item.child(j)
                data = child.data(0, Qt.ItemDataRole.UserRole)
                if data is not None and getattr(data, "id", None) == opp_id:
                    return child
                stack.append(child)
        return None

    leaf = _leaf_for(o.id)
    assert leaf is not None
    assert leaf.text(4) == "2"  # oponuje 2 práce


def test_opponent_affiliation_subgroups_and_checksum(qapp, service) -> None:
    """Skupina Interní/Externí má podskupiny dle Pracoviště + součet prací (Σ)."""
    from bpdpmanager.models import Student, Thesis
    from bpdpmanager.models.enums import ThesisType

    o1 = Opponent(name="A B", kind=OpponentKind.INTERNAL, affiliation="Ústav X")
    o2 = Opponent(name="C D", kind=OpponentKind.INTERNAL, affiliation="Ústav Y")
    for o in (o1, o2):
        service.upsert_opponent(o)
    s = Student(first_name="S", last_name="T")
    service.upsert_student(s)
    # o1 oponuje 2 práce, o2 jednu → Σ = 3 v interní skupině
    for opp, n in ((o1, 2), (o2, 1)):
        for _ in range(n):
            service.upsert_thesis(Thesis(type=ThesisType.BP, academic_year="2024/2025",
                                         student_id=s.id, opponent_id=opp.id))

    dlg = OpponentsManageDialog(service)
    root = dlg.tree.invisibleRootItem()
    internal = None
    for i in range(root.childCount()):
        if root.child(i).text(0).startswith("📍"):
            internal = root.child(i)
    assert internal is not None
    assert internal.text(4) == "Σ 3"  # kontrolní součet oponovaných prací
    # dvě podskupiny pracovišť
    sub_names = {internal.child(j).text(0).strip() for j in range(internal.childCount())}
    assert any("Ústav X" in n for n in sub_names)
    assert any("Ústav Y" in n for n in sub_names)


def test_students_surname_filter(qapp, service) -> None:
    """Real-time filtr příjmení ve správci studentů (necitlivý na diakritiku)."""
    from bpdpmanager.models import Student

    for ln in ("Novák", "Svoboda", "Dvořák"):
        service.upsert_student(Student(first_name="X", last_name=ln))

    dlg = StudentsManageDialog(service)

    def _visible_surnames() -> set[str]:
        out: set[str] = set()
        stack = [dlg.tree.invisibleRootItem()]
        while stack:
            it = stack.pop()
            for j in range(it.childCount()):
                ch = it.child(j)
                data = ch.data(0, Qt.ItemDataRole.UserRole)
                if data is not None and getattr(data, "last_name", None):
                    out.add(data.last_name)
                stack.append(ch)
        return out

    assert _visible_surnames() == {"Novák", "Svoboda", "Dvořák"}
    dlg.search_edit.setText("dvor")  # bez diakritiky
    assert _visible_surnames() == {"Dvořák"}
    dlg.search_edit.setText("")
    assert _visible_surnames() == {"Novák", "Svoboda", "Dvořák"}


def test_students_hide_history_filter(qapp, service) -> None:
    """„Skrýt historické studenty" skryje obhájené i nedokončené práce."""
    from bpdpmanager.models import Student, Thesis
    from bpdpmanager.models.enums import ThesisStatus, ThesisType

    cases = {
        "Aktivni": ThesisStatus.IN_PROGRESS,
        "Obhajeny": ThesisStatus.DEFENDED,
        "Nedokonceny": ThesisStatus.CANCELLED,
        "Neobhajeny": ThesisStatus.FAILED,
    }
    for ln, status in cases.items():
        s = Student(first_name="X", last_name=ln)
        service.upsert_student(s)
        service.upsert_thesis(Thesis(type=ThesisType.BP, academic_year="2024/2025",
                                     student_id=s.id, status=status))

    dlg = StudentsManageDialog(service)

    def _visible() -> set[str]:
        out: set[str] = set()
        stack = [dlg.tree.invisibleRootItem()]
        while stack:
            it = stack.pop()
            for j in range(it.childCount()):
                ch = it.child(j)
                data = ch.data(0, Qt.ItemDataRole.UserRole)
                if data is not None and getattr(data, "last_name", None):
                    out.add(data.last_name)
                stack.append(ch)
        return out

    assert _visible() == {"Aktivni", "Obhajeny", "Nedokonceny", "Neobhajeny"}
    dlg.chk_hide_history.setChecked(True)
    # obhájený i nedokončený se skryjí; aktivní zůstává
    visible = _visible()
    assert "Obhajeny" not in visible
    assert "Nedokonceny" not in visible
    assert "Aktivni" in visible


def test_move_opponent_changes_kind(qapp, service) -> None:
    o = Opponent(name="Jan Novák", kind=OpponentKind.INTERNAL)
    service.upsert_opponent(o)

    dlg = OpponentsManageDialog(service)
    dlg._move_opponent(o, OpponentKind.EXTERNAL.value)

    assert service.get_opponent(o.id).kind == OpponentKind.EXTERNAL
    # Skupiny ve stromu nesou svůj kind (cíl drop) v ROLE.
    from bpdpmanager.ui.manage_dialogs import _ROLE_GROUP_KIND

    kinds = {
        dlg.tree.topLevelItem(i).data(0, _ROLE_GROUP_KIND)
        for i in range(dlg.tree.topLevelItemCount())
    }
    assert OpponentKind.INTERNAL.value in kinds
    assert OpponentKind.EXTERNAL.value in kinds
