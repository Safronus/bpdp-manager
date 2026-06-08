"""Real-time našeptávač v horním vyhledávání + search_index služby."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from bpdpmanager.models import OpposingThesis, Student, Thesis
from bpdpmanager.models.enums import ThesisStatus, ThesisType
from bpdpmanager.services import ThesisService
from bpdpmanager.storage import JsonRepository


@pytest.fixture(scope="module")
def qapp():
    yield QApplication.instance() or QApplication([])


@pytest.fixture
def service(tmp_path):
    repo = JsonRepository(path=tmp_path / "db.json", backup_path=tmp_path / "db.json.bak")
    return ThesisService(repo)


def _seed(service):
    s = Student(first_name="Jan", last_name="Novák")
    service.upsert_student(s)
    t = Thesis(type=ThesisType.BP, status=ThesisStatus.IN_PROGRESS,
               academic_year=service.current_academic_year(),
               student_id=s.id, title_cs="Detekce anomálií")
    service.upsert_thesis(t)
    op = OpposingThesis(type=ThesisType.DP,
                        academic_year=service.current_academic_year(),
                        student_first_name="Petr", student_last_name="Svoboda",
                        title_cs="Neuronové sítě")
    service.upsert_opposing_thesis(op)
    return t, op


def test_search_index_has_type_and_all_works(service):
    t, op = _seed(service)
    idx = service.search_index()
    assert len(idx) == 2
    by_id = {h["id"]: h for h in idx}
    assert by_id[t.id]["type"] == "BP" and by_id[t.id]["kind"] == "thesis"
    assert by_id[op.id]["type"] == "DP" and by_id[op.id]["kind"] == "opposing"


def test_search_works_partial_match(service):
    _seed(service)
    # kousek příjmení
    assert len(service.search_works("novák")) == 1
    # kousek názvu
    assert len(service.search_works("neuron")) == 1
    # nic
    assert service.search_works("xyzq") == []


def test_completer_filters_and_navigates(qapp, service):
    from bpdpmanager.ui.main_window import MainWindow

    t, op = _seed(service)
    win = MainWindow(service)
    assert win._search_model.rowCount() == 2

    comp = win._completer
    comp.setCompletionPrefix("novák")         # kousek příjmení
    assert comp.completionCount() == 1
    comp.setCompletionPrefix("neuron")        # kousek názvu (oponentury)
    assert comp.completionCount() == 1

    # aktivace položky → skok na práci + vyčištění pole
    comp.setCompletionPrefix("novák")
    win._on_search_activated(comp.completionModel().index(0, 0))
    assert win.tab_current.tree.selected_thesis_id() == t.id
    assert win.ed_search.text() == ""

    # label obsahuje záložku, roli, typ, studenta i název
    label = win._search_label(service.search_index()[0])
    assert "Vedená" in label and "BP" in label and "Novák" in label
