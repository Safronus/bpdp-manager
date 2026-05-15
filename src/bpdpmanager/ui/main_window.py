from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
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
from .opponent_dialog import OpponentDialog
from .student_dialog import StudentDialog
from .thesis_detail import ThesisDetail
from .tree_view import ThesesTreeWidget


class _ThesesTab(QWidget):
    """Jedna záložka = strom + detail, s vlastním filtrem."""

    def __init__(self, service: ThesisService, filter_predicate, parent=None) -> None:
        super().__init__(parent)
        self.service = service

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.tree = ThesesTreeWidget(service)
        self.tree.set_filter(filter_predicate)
        self.detail = ThesisDetail(service)

        splitter.addWidget(self.tree)
        splitter.addWidget(self.detail)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(splitter)

        self.tree.thesis_selected.connect(self._on_thesis_selected)
        self.detail.saved.connect(lambda _: self.tree.refresh())
        self.detail.deleted.connect(lambda _: self.tree.refresh())

    def _on_thesis_selected(self, thesis_id: str) -> None:
        thesis = self.service.get_thesis(thesis_id)
        self.detail.set_thesis(thesis)

    def refresh(self) -> None:
        self.tree.refresh()


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
            or (t.academic_year and t.academic_year < current_year and t.status not in {ThesisStatus.INTERESTED}),
        )
        self.tab_all = _ThesesTab(service, lambda t: True)

        self.tabs.addTab(self.tab_current, f"Aktuální ({current_year})")
        self.tabs.addTab(self.tab_future, f"Budoucí ({next_year})")
        self.tabs.addTab(self.tab_history, "Historie")
        self.tabs.addTab(self.tab_all, "Vše")

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
        act_new_interest.triggered.connect(lambda: self._new_thesis(next_year, ThesisStatus.INTERESTED))
        toolbar.addAction(act_new_interest)

        toolbar.addSeparator()

        act_students = QAction("Studenti", self)
        act_students.triggered.connect(self._manage_students)
        toolbar.addAction(act_students)

        act_opponents = QAction("Oponenti", self)
        act_opponents.triggered.connect(self._manage_opponents)
        toolbar.addAction(act_opponents)

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
            tab: _ThesesTab = self.tabs.widget(i)  # type: ignore[assignment]
            if tab.tree.select_thesis(thesis_id):
                self.tabs.setCurrentIndex(i)
                tab.detail.set_thesis(self.service.get_thesis(thesis_id))
                return

    def _manage_students(self) -> None:
        ManageDialog(
            self,
            title="Studenti",
            items_loader=self.service.list_students,
            item_label=lambda s: f"{s.full_name} — {s.display_obor}"
            + (f"  [{s.university_id}]" if s.university_id else ""),
            editor=lambda s: StudentDialog(self.service, s, self),
            new_editor=lambda: StudentDialog(self.service, None, self),
            deleter=lambda s: self.service.delete_student(s.id),
        ).exec()
        self._refresh_all()

    def _manage_opponents(self) -> None:
        ManageDialog(
            self,
            title="Oponenti",
            items_loader=self.service.list_opponents,
            item_label=lambda o: o.name + (f" ({o.affiliation})" if o.affiliation else ""),
            editor=lambda o: OpponentDialog(self.service, o, self),
            new_editor=lambda: OpponentDialog(self.service, None, self),
            deleter=lambda o: self.service.delete_opponent(o.id),
        ).exec()
        self._refresh_all()

    def _refresh_all(self) -> None:
        self.service.reload()
        for i in range(self.tabs.count()):
            tab: _ThesesTab = self.tabs.widget(i)  # type: ignore[assignment]
            tab.refresh()
        self._update_status()

    def _update_status(self) -> None:
        total = len(self.service.list_theses())
        students = len(self.service.list_students())
        opponents = len(self.service.list_opponents())
        self.statusBar().showMessage(
            f"Práce: {total} • Studenti: {students} • Oponenti: {opponents}"
        )


class ManageDialog(QWidget):
    """Velmi jednoduchý správce seznamu (studenti/oponenti)."""

    def __init__(self, parent, title, items_loader, item_label, editor, new_editor, deleter):
        from PySide6.QtWidgets import QDialog

        self._dialog = QDialog(parent)
        self._dialog.setWindowTitle(title)
        self._dialog.setMinimumSize(520, 480)

        self.items_loader = items_loader
        self.item_label = item_label
        self.editor = editor
        self.new_editor = new_editor
        self.deleter = deleter

        layout = QVBoxLayout(self._dialog)
        layout.addWidget(QLabel(title))

        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self._edit)
        layout.addWidget(self.list_widget)

        row = QHBoxLayout()
        btn_new = QPushButton("Nový…")
        btn_edit = QPushButton("Upravit…")
        btn_delete = QPushButton("Smazat")
        btn_close = QPushButton("Zavřít")
        btn_new.clicked.connect(self._new)
        btn_edit.clicked.connect(self._edit)
        btn_delete.clicked.connect(self._delete)
        btn_close.clicked.connect(self._dialog.accept)
        row.addWidget(btn_new)
        row.addWidget(btn_edit)
        row.addWidget(btn_delete)
        row.addStretch()
        row.addWidget(btn_close)
        layout.addLayout(row)

        self._refresh()

    def exec(self) -> int:
        return self._dialog.exec()

    def _refresh(self) -> None:
        self.list_widget.clear()
        for item in self.items_loader():
            li = QListWidgetItem(self.item_label(item))
            li.setData(Qt.ItemDataRole.UserRole, item)
            self.list_widget.addItem(li)

    def _current(self):
        item = self.list_widget.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _new(self) -> None:
        dlg = self.new_editor()
        if dlg.exec():
            self._refresh()

    def _edit(self) -> None:
        current = self._current()
        if current is None:
            return
        dlg = self.editor(current)
        if dlg.exec():
            self._refresh()

    def _delete(self) -> None:
        current = self._current()
        if current is None:
            return
        confirm = QMessageBox.question(
            self._dialog,
            "Smazat",
            "Opravdu smazat tuto položku?",
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.deleter(current)
            self._refresh()
