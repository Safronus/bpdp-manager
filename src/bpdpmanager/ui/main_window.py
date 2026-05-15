from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QCloseEvent
from PySide6.QtWidgets import (
    QInputDialog,
    QMainWindow,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from ..models import Thesis
from ..models.enums import ThesisStatus, ThesisType
from ..services import ThesisService
from .harmonogram_tab import HarmonogramTab
from .manage_dialogs import (
    OboryManageDialog,
    OpponentsManageDialog,
    StudentsManageDialog,
)
from .theses_table import ThesesTableWidget
from .thesis_detail import ThesisDetail


class _ThesesTab(QWidget):
    """Jedna záložka = tabulka prací nahoře + detail dole, s vlastním filtrem."""

    def __init__(self, service: ThesisService, filter_predicate, parent=None) -> None:
        super().__init__(parent)
        self.service = service

        splitter = QSplitter(Qt.Orientation.Vertical)
        self.table = ThesesTableWidget(service)
        self.table.set_filter(filter_predicate)
        self.detail = ThesisDetail(service)

        splitter.addWidget(self.table)
        splitter.addWidget(self.detail)
        splitter.setStretchFactor(0, 2)  # tabulka
        splitter.setStretchFactor(1, 3)  # detail mírně větší

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(splitter)

        self.table.thesis_selected.connect(self._on_thesis_selected)
        self.detail.saved.connect(lambda _: self.table.refresh())
        self.detail.deleted.connect(lambda _: self.table.refresh())

    def _on_thesis_selected(self, thesis_id: str) -> None:
        thesis = self.service.get_thesis(thesis_id)
        self.detail.set_thesis(thesis)

    def refresh(self) -> None:
        self.table.refresh()


class MainWindow(QMainWindow):
    def __init__(self, service: ThesisService) -> None:
        super().__init__()
        self.service = service
        self.setWindowTitle("BPDPManager — správa BP/DP")
        self.resize(1280, 800)

        current_year = ThesisService.current_academic_year()
        next_year = ThesisService.next_academic_year()

        active_states = {
            ThesisStatus.RESERVED,
            ThesisStatus.LISTED,
            ThesisStatus.ASSIGNED,
            ThesisStatus.IN_PROGRESS,
        }
        finished_states = {ThesisStatus.DEFENDED, ThesisStatus.CANCELLED}

        self.tabs = QTabWidget()
        self.tab_current = _ThesesTab(
            service,
            lambda t: t.academic_year == current_year and t.status in active_states,
        )
        self.tab_future = _ThesesTab(
            service,
            lambda t: t.academic_year == next_year
            or (t.status == ThesisStatus.INTERESTED and t.academic_year >= current_year),
        )
        self.tab_history = _ThesesTab(
            service,
            lambda t: t.status in finished_states
            or (
                t.academic_year
                and t.academic_year < current_year
                and t.status not in {ThesisStatus.INTERESTED}
            ),
        )
        self.tab_all = _ThesesTab(service, lambda t: True)
        self.tab_harmonogram = HarmonogramTab(service)

        self.tabs.addTab(self.tab_current, f"Aktuální ({current_year})")
        self.tabs.addTab(self.tab_future, f"Budoucí ({next_year})")
        self.tabs.addTab(self.tab_history, "Historie")
        self.tabs.addTab(self.tab_all, "Vše")
        self.tabs.addTab(self.tab_harmonogram, "📅 Harmonogram")

        self.setCentralWidget(self.tabs)
        self.setStatusBar(QStatusBar())

        self._build_toolbar(current_year, next_year)
        self._update_status()

    # --- toolbar -------------------------------------------------------------

    def _build_toolbar(self, current_year: str, next_year: str) -> None:
        toolbar = QToolBar("Hlavní")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        act_new_thesis = QAction("+ Nová práce", self)
        act_new_thesis.triggered.connect(lambda: self._new_thesis(current_year))
        toolbar.addAction(act_new_thesis)

        act_new_interest = QAction("+ Zájemce (budoucí rok)", self)
        act_new_interest.triggered.connect(
            lambda: self._new_thesis(next_year, ThesisStatus.INTERESTED)
        )
        toolbar.addAction(act_new_interest)

        toolbar.addSeparator()

        act_students = QAction("Studenti", self)
        act_students.triggered.connect(self._manage_students)
        toolbar.addAction(act_students)

        act_opponents = QAction("Oponenti", self)
        act_opponents.triggered.connect(self._manage_opponents)
        toolbar.addAction(act_opponents)

        act_obory = QAction("Obory", self)
        act_obory.triggered.connect(self._manage_obory)
        toolbar.addAction(act_obory)

        toolbar.addSeparator()

        act_refresh = QAction("Obnovit", self)
        act_refresh.triggered.connect(self._refresh_all)
        toolbar.addAction(act_refresh)

    # --- akce ----------------------------------------------------------------

    def _new_thesis(self, year: str, status: ThesisStatus = ThesisStatus.RESERVED) -> None:
        thesis_type_label, ok = QInputDialog.getItem(
            self,
            "Typ práce",
            "Vyber typ nové práce:",
            [t.label for t in ThesisType],
            0,
            False,
        )
        if not ok:
            return
        thesis_type = next(t for t in ThesisType if t.label == thesis_type_label)
        thesis = Thesis(type=thesis_type, status=status, academic_year=year)
        self.service.upsert_thesis(thesis)
        self._refresh_all()
        self._focus_thesis(thesis.id)

    def _focus_thesis(self, thesis_id: str) -> None:
        for i in range(self.tabs.count()):
            widget = self.tabs.widget(i)
            if isinstance(widget, _ThesesTab) and widget.table.select_thesis(thesis_id):
                self.tabs.setCurrentIndex(i)
                widget.detail.set_thesis(self.service.get_thesis(thesis_id))
                return

    def _manage_students(self) -> None:
        StudentsManageDialog(self.service, self).exec()
        self._refresh_all()

    def _manage_opponents(self) -> None:
        OpponentsManageDialog(self.service, self).exec()
        self._refresh_all()

    def _manage_obory(self) -> None:
        OboryManageDialog(self.service, self).exec()
        self._refresh_all()

    def _refresh_all(self) -> None:
        self.service.reload()
        for i in range(self.tabs.count()):
            widget = self.tabs.widget(i)
            if isinstance(widget, _ThesesTab):
                widget.refresh()
            elif isinstance(widget, HarmonogramTab):
                widget._refresh_year_combo()
        self._update_status()

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802 (Qt API)
        """Při zavření okna ještě flushne všechny dirty formuláře."""
        for i in range(self.tabs.count()):
            widget = self.tabs.widget(i)
            if isinstance(widget, _ThesesTab):
                widget.detail.flush()
        super().closeEvent(event)

    def _update_status(self) -> None:
        total = len(self.service.list_theses())
        students = len(self.service.list_students())
        opponents = len(self.service.list_opponents())
        obory = len(self.service.list_obory())
        self.statusBar().showMessage(
            f"Práce: {total} • Studenti: {students} • Oponenti: {opponents} • Obory: {obory}"
        )
