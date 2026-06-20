"""Testy importu souborů ze STAG — náhled výběru a párování práce v DB."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from bpdpmanager.models import OpposingThesis, Student, Thesis  # noqa: E402
from bpdpmanager.models.enums import AttachmentKind, ThesisType  # noqa: E402
from bpdpmanager.services import ThesisService  # noqa: E402
from bpdpmanager.services import stag_api  # noqa: E402
from bpdpmanager.storage import JsonRepository  # noqa: E402
from bpdpmanager.ui.stag_import_dialog import (  # noqa: E402
    _SECTION_TO_KIND,
    StagDownloadDialog,
    StagImportDialog,
    StagFilesPreviewDialog,
    _DownloadedStagFile,
)


@pytest.fixture(scope="module")
def qapp():
    yield QApplication.instance() or QApplication([])


@pytest.fixture
def service(tmp_path: Path) -> ThesisService:
    repo = JsonRepository(path=tmp_path / "db.json", backup_path=tmp_path / "db.json.bak")
    return ThesisService(repo)


def _mk_file(tmp_path: Path, name: str, section: str) -> _DownloadedStagFile:
    p = tmp_path / name
    p.write_bytes(b"x")
    return _DownloadedStagFile(
        path=p, filename=name,
        kind=_SECTION_TO_KIND.get(section, AttachmentKind.OTHER),
        section=section, size=1,
    )


def test_section_to_kind_mapping() -> None:
    assert _SECTION_TO_KIND["text"] == AttachmentKind.THESIS_TEXT
    assert _SECTION_TO_KIND["appendix"] == AttachmentKind.THESIS_APPENDIX
    assert _SECTION_TO_KIND["supervisor_review"] == AttachmentKind.SUPERVISOR_REVIEW
    assert _SECTION_TO_KIND["opponent_review"] == AttachmentKind.OPPONENT_REVIEW
    assert _SECTION_TO_KIND["other"] == AttachmentKind.OTHER


def test_status_baseline_suppressed_during_bg_downloads(qapp, service) -> None:
    """Při běžícím stahování příloh ze STAG (lišta vlevo dole) se základní
    souhrn ve stavovém řádku NEpřepisuje — jinak se text slíval přes progres
    (viz „progress vypisuje aktualizace přes sebe")."""
    from bpdpmanager.ui.main_window import MainWindow

    win = MainWindow(service)
    sb = win.statusBar()
    win._update_status()
    assert "Vedené práce:" in sb.currentMessage()          # normálně se ukáže
    # simuluj běžící dávku stahování příloh (lišta drží stavový řádek)
    win._stag_file_mgr = object()
    sb.showMessage("⬇ STAG soubory 3/10")
    win._update_status()
    assert sb.currentMessage() == "⬇ STAG soubory 3/10"    # NEpřepsáno souhrnem
    # po doběhnutí dávky se souhrn zase obnoví
    win._stag_file_mgr = None
    win._update_status()
    assert "Vedené práce:" in sb.currentMessage()


def test_preview_default_all_selected(qapp, tmp_path: Path) -> None:
    f1 = _mk_file(tmp_path, "text.pdf", "text")
    f2 = _mk_file(tmp_path, "prilohy.zip", "appendix")
    dlg = StagFilesPreviewDialog([("Novák Jan (DP)", [f1, f2])])
    # Defaultně vše zaškrtnuto
    for r in range(dlg.table.rowCount()):
        assert dlg.table.item(r, 0).checkState() == Qt.CheckState.Checked
    dlg._accept()
    assert f1.selected and f2.selected
    assert f1.kind == AttachmentKind.THESIS_TEXT


def test_preview_uncheck_one(qapp, tmp_path: Path) -> None:
    f1 = _mk_file(tmp_path, "text.pdf", "text")
    f2 = _mk_file(tmp_path, "posudek.pdf", "opponent_review")
    dlg = StagFilesPreviewDialog([("Novák Jan", [f1, f2])])
    dlg.table.item(0, 0).setCheckState(Qt.CheckState.Unchecked)
    dlg._accept()
    assert not f1.selected
    assert f2.selected


def test_preview_set_all_none(qapp, tmp_path: Path) -> None:
    f1 = _mk_file(tmp_path, "a.pdf", "text")
    dlg = StagFilesPreviewDialog([("X", [f1])])
    dlg._set_all(False)
    dlg._accept()
    assert not f1.selected


def test_find_db_target_by_adipidno(qapp, service: ThesisService) -> None:
    student = Student(first_name="Jan", last_name="Novák", university_id="A1")
    service.upsert_student(student)
    t = Thesis(type=ThesisType.DP, academic_year="2024/2025",
               student_id=student.id, adipidno="66896")
    service.upsert_thesis(t)

    dlg = StagDownloadDialog(service=service)
    r = stag_api.StagThesisResult(adipidno="66896", surname="Novák", name="Jan",
                                  type_label="Diplomová práce")
    assert dlg._find_db_target(r) == (t.id, None)


def test_find_db_target_opposing_by_name_type(qapp, service: ThesisService) -> None:
    op = OpposingThesis(type=ThesisType.BP, academic_year="2024/2025",
                        student_first_name="Eva", student_last_name="Malá")
    service.upsert_opposing_thesis(op)

    dlg = StagDownloadDialog(service=service)
    r = stag_api.StagThesisResult(adipidno="99999", surname="Malá", name="Eva",
                                  type_label="Bakalářská práce")
    # adipIdno nesedí → fallback přes jméno + typ
    assert dlg._find_db_target(r) == (None, op.id)


def test_find_db_target_no_match(qapp, service: ThesisService) -> None:
    dlg = StagDownloadDialog(service=service)
    r = stag_api.StagThesisResult(adipidno="123", surname="Nikdo", name="Nový",
                                  type_label="Diplomová práce")
    assert dlg._find_db_target(r) == (None, None)


def _pending(name, kind, section, selected, sf) -> _DownloadedStagFile:
    return _DownloadedStagFile(
        path=None, filename=name, kind=kind, section=section,
        size=10, selected=selected, stag_file=sf,
    )


def test_build_download_jobs_respects_selection_and_role(
    qapp, service: ThesisService
) -> None:
    """Joby na pozadí: jen vybrané, správný cíl/role/typ; bez cíle se přeskočí."""
    dlg = StagImportDialog(service)
    sf1, sf3 = object(), object()
    dlg._stag_pending_files = {
        "A1": [
            _pending("text.pdf", AttachmentKind.THESIS_TEXT, "text", True, sf1),
            _pending("skip.pdf", AttachmentKind.OTHER, "other", False, object()),
        ],
        "B2": [
            _pending("posudek.pdf", AttachmentKind.OPPONENT_REVIEW,
                     "opponent_review", True, sf3),
        ],
        "C3": [  # bez cíle v DB → přeskočí se celé
            _pending("x.pdf", AttachmentKind.OTHER, "other", True, object()),
        ],
    }
    dlg._stag_pending_labels = {"A1": "Novák Jan", "B2": "Malá Eva", "C3": "X"}

    jobs = dlg._build_stag_download_jobs(
        thesis_by_adip={"A1": "tid-1"},
        opposing_by_adip={"B2": "oid-2"},
    )

    assert len(jobs) == 2
    j_text = next(j for j in jobs if j.adipidno == "A1")
    assert j_text.target_id == "tid-1" and j_text.is_opposing is False
    assert j_text.kind == AttachmentKind.THESIS_TEXT
    assert j_text.stag_file is sf1 and j_text.student_label == "Novák Jan"
    j_op = next(j for j in jobs if j.adipidno == "B2")
    assert j_op.target_id == "oid-2" and j_op.is_opposing is True
    assert j_op.kind == AttachmentKind.OPPONENT_REVIEW


def test_merged_dialog_two_steps(qapp, service: ThesisService) -> None:
    """Sloučené okno: dva kroky v QStackedWidget, start na hledání."""
    dlg = StagImportDialog(service)
    assert dlg._stack.count() == 2
    assert dlg._stack.currentWidget() is dlg._page_search   # start = krok 1
    assert dlg._search_panel._embedded is True
    # Krok 2 a zpět
    dlg._stack.setCurrentWidget(dlg._page_preview)
    dlg._go_back_to_search()
    assert dlg._stack.currentWidget() is dlg._page_search


def test_merged_dialog_files_only_closes_window(qapp, service: ThesisService) -> None:
    """„Jen soubory" v panelu → okno se zavře (accept) s focus_*."""
    dlg = StagImportDialog(service)
    dlg._search_panel.files_only_done = True
    dlg._search_panel.focus_thesis_id = "tid-X"
    seen = []
    dlg.accepted.connect(lambda: seen.append(True))
    dlg._on_search_panel_accepted()
    assert seen == [True]
    assert dlg.focus_thesis_id == "tid-X"


def test_merged_dialog_reject_when_empty_closes(qapp, service: ThesisService) -> None:
    """„Zrušit" v panelu při prázdném náhledu → zavře celé okno (reject)."""
    dlg = StagImportDialog(service)
    seen = []
    dlg.rejected.connect(lambda: seen.append(True))
    dlg._on_search_panel_rejected()
    assert seen == [True]


def _preview_with_records(dlg, n):
    """Naplní náhled `n` fiktivními řádky (přes _populate_preview)."""
    from bpdpmanager.services.stag_csv_importer import (
        ImportFile,
        ImportRole,
        ParsedRecord,
    )
    recs = [
        ParsedRecord(role=ImportRole.UNKNOWN, student_last=f"N{i}",
                     student_first="Jan", type_code="DP",
                     academic_year="2024/2025", title_cs=f"Téma {i}")
        for i in range(n)
    ]
    dlg.import_file = ImportFile(path=Path("x.csv"), encoding="utf-8", records=recs)
    dlg._populate_preview()


def test_bulk_set_role_status_action(qapp, service: ThesisService) -> None:
    """Hromadné nastavení role/stavu/akce u vybraných řádků náhledu."""
    from bpdpmanager.models.enums import ThesisStatus
    from bpdpmanager.services.stag_csv_importer import ImportRole
    from bpdpmanager.ui.stag_import_dialog import ACTION_SKIP

    dlg = StagImportDialog(service)
    _preview_with_records(dlg, 3)
    assert len(dlg.row_widgets) == 3

    dlg.table_select_all()
    # Role → Oponuji
    dlg.cmb_bulk_role.setCurrentIndex(
        dlg.cmb_bulk_role.findData(ImportRole.OPPONENT.value))
    assert all(w["cb_role"].currentData() == ImportRole.OPPONENT.value
               for w in dlg.row_widgets)
    assert dlg.cmb_bulk_role.currentIndex() == 0   # reset na placeholder
    # Stav → Obhájeno
    dlg.cmb_bulk_status.setCurrentIndex(
        dlg.cmb_bulk_status.findData(ThesisStatus.DEFENDED.value))
    assert all(w["cb_status"].currentData() == ThesisStatus.DEFENDED.value
               for w in dlg.row_widgets)
    # Akce → Přeskočit
    dlg.cmb_bulk_action.setCurrentIndex(dlg.cmb_bulk_action.findData("skip"))
    assert all(w["cb_action"].currentData() == ACTION_SKIP
               for w in dlg.row_widgets)


def test_bulk_only_selected_rows(qapp, service: ThesisService) -> None:
    """Hromadná změna se dotkne jen vybraných řádků (ne všech)."""
    from bpdpmanager.services.stag_csv_importer import ImportRole

    dlg = StagImportDialog(service)
    _preview_with_records(dlg, 3)
    dlg.table.clearSelection()
    dlg.table.selectRow(1)   # jen prostřední
    dlg.cmb_bulk_role.setCurrentIndex(
        dlg.cmb_bulk_role.findData(ImportRole.OPPONENT.value))
    roles = [w["cb_role"].currentData() for w in dlg.row_widgets]
    assert roles[1] == ImportRole.OPPONENT.value
    assert roles[0] == ImportRole.SUPERVISOR.value   # nedotčeno
    assert roles[2] == ImportRole.SUPERVISOR.value


def test_bulk_without_selection_is_noop(qapp, service: ThesisService) -> None:
    """Bez výběru řádků se nic nezmění a ukáže se hint."""
    from bpdpmanager.services.stag_csv_importer import ImportRole

    dlg = StagImportDialog(service)
    _preview_with_records(dlg, 2)
    before = [w["cb_role"].currentData() for w in dlg.row_widgets]
    dlg.table.clearSelection()
    dlg.cmb_bulk_role.setCurrentIndex(
        dlg.cmb_bulk_role.findData(ImportRole.OPPONENT.value))
    assert [w["cb_role"].currentData() for w in dlg.row_widgets] == before
    assert "Nejdřív vyber" in dlg.lbl_info.text()


def test_mainwindow_stag_attach_fn_attaches_and_cleans_temp(
    qapp, tmp_path: Path, service: ThesisService
) -> None:
    """`_stag_attach_fn` připojí stažený soubor k práci a smaže temp."""
    from bpdpmanager.ui.main_window import MainWindow
    from bpdpmanager.ui.stag_download_manager import StagFileJob, StagFileResult

    student = Student(first_name="Jan", last_name="Novák")
    service.upsert_student(student)
    t = Thesis(type=ThesisType.DP, academic_year="2024/2025", student_id=student.id)
    service.upsert_thesis(t)

    class _SF:
        filename = "text.pdf"
        section = "text"

    mw = MainWindow(service)
    try:
        job = StagFileJob(
            target_id=t.id, is_opposing=False, adipidno="X",
            student_label="Novák Jan", stag_file=_SF(),
            kind=AttachmentKind.THESIS_TEXT,
        )
        tmp = tmp_path / "stag_text.pdf"
        tmp.write_bytes(b"PDFDATA")
        mw._stag_attach_fn(StagFileResult(job=job, path=tmp, size=7))

        loaded = service.get_thesis(t.id)
        assert any(a.kind == AttachmentKind.THESIS_TEXT for a in loaded.attachments)
        assert not tmp.exists()   # temp uklizen po připojení
    finally:
        mw.close()
