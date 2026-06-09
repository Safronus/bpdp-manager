"""Dialog tisku posudků MyQ — naplnění výběru + sběr vybraných úloh."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from bpdpmanager.models import OpposingThesis, Student, Thesis
from bpdpmanager.models.enums import AttachmentKind, ThesisStatus, ThesisType
from bpdpmanager.services import ThesisService
from bpdpmanager.storage import JsonRepository
from bpdpmanager.ui.myq_print_dialog import MyQPrintDialog

_ROLE_NAME = Qt.ItemDataRole.UserRole + 2


@pytest.fixture(scope="module")
def qapp():
    yield QApplication.instance() or QApplication([])


@pytest.fixture
def service(tmp_path: Path) -> ThesisService:
    repo = JsonRepository(
        path=tmp_path / "db.json", backup_path=tmp_path / "db.json.bak"
    )
    return ThesisService(repo)


def _seed(service: ThesisService, tmp_path: Path) -> None:
    year = service.current_academic_year()
    # Vedená práce S posudkem vedoucího.
    s1 = Student(first_name="Jan", last_name="Novák")
    service.upsert_student(s1)
    t1 = Thesis(type=ThesisType.BP, status=ThesisStatus.IN_PROGRESS,
                academic_year=year, student_id=s1.id)
    service.upsert_thesis(t1)
    pv = tmp_path / "pv.pdf"
    pv.write_bytes(b"%PDF-1")
    service.attach_document(t1.id, pv, kind=AttachmentKind.SUPERVISOR_REVIEW)
    # Vedená práce BEZ posudku → nesmí se nabídnout.
    s2 = Student(first_name="Eva", last_name="Dvořáková")
    service.upsert_student(s2)
    t2 = Thesis(type=ThesisType.BP, status=ThesisStatus.IN_PROGRESS,
                academic_year=year, student_id=s2.id)
    service.upsert_thesis(t2)
    # Oponovaná práce S posudkem oponenta (aktuální rok).
    op = OpposingThesis(type=ThesisType.BP, academic_year=year,
                        student_first_name="Petr", student_last_name="Svoboda",
                        title_cs="X")
    service.upsert_opposing_thesis(op)
    po = tmp_path / "po.pdf"
    po.write_bytes(b"%PDF-2")
    service.opposing_attach_document(op.id, po, kind=AttachmentKind.OPPONENT_REVIEW)


def test_dialog_lists_only_works_with_pdf(qapp, service, tmp_path) -> None:
    _seed(service, tmp_path)
    dlg = MyQPrintDialog(service)
    names = [leaf.data(0, _ROLE_NAME) for leaf in dlg._iter_leaves()]
    assert "Jan Novák" in names          # vedená s posudkem
    assert "Petr Svoboda" in names       # oponovaná s posudkem
    assert "Eva Dvořáková" not in names  # bez posudku → nenabízí se
    assert len(names) == 2


def test_subset_only_thesis_ids(qapp, service, tmp_path) -> None:
    """only_thesis_ids → jen vybraná vedená práce, oponované se vynechají."""
    _seed(service, tmp_path)
    t1 = next(t for t in service.list_theses()
              if service.current_supervisor_review_pdf(t) is not None)
    dlg = MyQPrintDialog(service, only_thesis_ids=[t1.id])
    names = [leaf.data(0, _ROLE_NAME) for leaf in dlg._iter_leaves()]
    assert names == ["Jan Novák"]
    assert "Petr Svoboda" not in names   # oponovaná vynechána


def test_subset_only_opposing_ids(qapp, service, tmp_path) -> None:
    """only_opposing_ids → jen vybraná oponovaná práce, vedené se vynechají."""
    _seed(service, tmp_path)
    op = service.list_opposing_theses()[0]
    dlg = MyQPrintDialog(service, only_opposing_ids=[op.id])
    names = [leaf.data(0, _ROLE_NAME) for leaf in dlg._iter_leaves()]
    assert names == ["Petr Svoboda"]
    assert "Jan Novák" not in names      # vedená vynechána


def test_not_printed_auto_checked(qapp, service, tmp_path) -> None:
    _seed(service, tmp_path)
    dlg = MyQPrintDialog(service)
    # Default: nevytištěné posudky jsou předzaškrtnuté.
    names = {it["name"] for it in dlg._selected()}
    assert names == {"Jan Novák", "Petr Svoboda"}
    assert all(it["pdf"].suffix == ".pdf" for it in dlg._selected())


def test_printed_work_in_separate_unchecked_section(qapp, service, tmp_path) -> None:
    _seed(service, tmp_path)
    # Označ oponovanou jako vytištěnou → musí být ve výběru NEzaškrtnutá.
    year = service.current_academic_year()
    op = next(o for o in service.list_opposing_theses()
              if o.academic_year == year)
    service.set_opponent_review_printed(op.id, True)

    dlg = MyQPrintDialog(service)
    names = {it["name"] for it in dlg._selected()}
    assert names == {"Jan Novák"}              # Petr (vytištěný) NEzaškrtnut
    dlg._set_all_checked(True)
    assert {it["name"] for it in dlg._selected()} == {"Jan Novák", "Petr Svoboda"}
    dlg._set_all_checked(False)
    assert dlg._selected() == []


def test_summary_wording_depends_on_destination(qapp, service, tmp_path) -> None:
    from unittest import mock

    from PySide6.QtWidgets import QMessageBox

    _seed(service, tmp_path)
    t = next(t for t in service.list_theses())
    dlg = MyQPrintDialog(service)
    dlg._jobs = [{"name": "Jan Novák", "pdf": tmp_path / "pv.pdf",
                  "kind": "supervised", "id": t.id}]

    summaries = {}
    for sysp in (False, True):
        dlg._is_system_print = sysp
        with mock.patch.object(QMessageBox, "information") as info, \
             mock.patch.object(QMessageBox, "question",
                               return_value=QMessageBox.StandardButton.No):
            dlg._on_done([(True, "")])
            summaries[sysp] = info.call_args[0][2]
    assert "Vytištěno" in summaries[True]
    assert "MyQ fronty" in summaries[False]


def test_confirm_print_text(qapp, service) -> None:
    from unittest import mock

    from PySide6.QtWidgets import QMessageBox

    dlg = MyQPrintDialog(service)
    with mock.patch.object(QMessageBox, "question",
                           return_value=QMessageBox.StandardButton.Yes) as q:
        assert dlg._confirm_print(2, "na tiskárnu „X“") is True
    assert "Vytisknout 2" in q.call_args[0][2]


def test_mark_printed_persists(qapp, service, tmp_path) -> None:
    _seed(service, tmp_path)
    t = next(t for t in service.list_theses())
    dlg = MyQPrintDialog(service)
    dlg._mark_printed([{"kind": "supervised", "id": t.id, "name": "Jan Novák"}])
    assert service.get_thesis(t.id).supervisor_review_printed_at is not None


def test_empty_when_no_reviews(qapp, service) -> None:
    dlg = MyQPrintDialog(service)
    assert list(dlg._iter_leaves()) == []


def test_subgroups_by_review_kind(qapp, service, tmp_path) -> None:
    """Uvnitř skupiny K tisku jsou podskupiny vedoucího / oponenta."""
    _seed(service, tmp_path)
    dlg = MyQPrintDialog(service)
    # první top-skupina = „K tisku — nevytištěné"
    ktisku = dlg.tree.topLevelItem(0)
    sub_titles = [ktisku.child(i).text(0) for i in range(ktisku.childCount())]
    assert any("Posudky vedoucího" in s for s in sub_titles)
    assert any("Posudky oponenta" in s for s in sub_titles)
    # leafy jsou pod podskupinami (2 úrovně) a stále se vyberou
    assert {it["name"] for it in dlg._selected()} == {"Jan Novák", "Petr Svoboda"}


def test_print_worker_auto_fallback_on_tls(qapp, monkeypatch, tmp_path) -> None:
    """Když selže ověření TLS, worker se sám připojí znovu bez ověření."""
    from typing import ClassVar

    import bpdpmanager.services.myq_client as mc
    from bpdpmanager.ui.myq_print_dialog import _PrintWorker

    class _FakeClient:
        instances: ClassVar[list] = []

        def __init__(self, *, verify_tls: bool = True) -> None:
            self.verify_tls = verify_tls
            _FakeClient.instances.append(self)

        def login(self, user: str, pin: str) -> None:
            if self.verify_tls:
                err = mc.MyQError("Selhalo ověření TLS certifikátu MyQ")
                err.is_tls = True
                raise err

        def upload(self, pdf) -> None:
            pass

    monkeypatch.setattr(mc, "MyQClient", _FakeClient)

    pdf = tmp_path / "x.pdf"
    pdf.write_bytes(b"%PDF-1")
    worker = _PrintWorker("user", "1234", [("Novák", pdf)], verify_tls=True)
    fired: dict = {}
    worker.tls_fallback.connect(lambda: fired.__setitem__("fb", True))
    worker.done.connect(lambda r: fired.__setitem__("done", r))
    worker.failed.connect(lambda m: fired.__setitem__("failed", m))

    worker.run()  # synchronně (na hlavním vlákně)

    assert fired.get("fb") is True               # došlo k fallbacku
    assert fired.get("done") == [(True, "")]      # a tisk pak prošel
    assert "failed" not in fired
    assert _FakeClient.instances[-1].verify_tls is False  # 2. klient bez ověření
