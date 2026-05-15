"""Tabulkový pohled na práce — nahrazuje stromové zobrazení."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
)

from ..models import Thesis
from ..services import ThesisService

ROLE_THESIS_ID = Qt.ItemDataRole.UserRole + 1


class ThesesTableWidget(QTableWidget):
    """Tabulka prací se sloupci: Student | Téma | Stav | Oponent | Obor.

    - Sloupec *Stav* má barevné pozadí podle ``ThesisStatus.color``.
    - Šířka sloupců se přizpůsobuje obsahu, jen *Téma* vyplní zbývající prostor.
    - Tabulka je tříditelná kliknutím na hlavičku; defaultní řazení je
      podle akademického roku DESC, pak stavu v procesním pořadí, pak názvu.
    """

    thesis_selected = Signal(str)

    HEADERS = ["Student", "Téma", "Stav", "Oponent", "Obor"]
    COL_STUDENT = 0
    COL_TITLE = 1
    COL_STATUS = 2
    COL_OPPONENT = 3
    COL_OBOR = 4

    def __init__(self, service: ThesisService, parent=None) -> None:
        super().__init__(0, len(self.HEADERS), parent)
        self.service = service
        self._filter_predicate = lambda t: True

        self.setHorizontalHeaderLabels(self.HEADERS)
        self.verticalHeader().setVisible(False)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(True)
        self.setShowGrid(False)
        self.setWordWrap(False)

        h = self.horizontalHeader()
        h.setSectionResizeMode(self.COL_STUDENT, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(self.COL_TITLE, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(self.COL_STATUS, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(self.COL_OPPONENT, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(self.COL_OBOR, QHeaderView.ResizeMode.ResizeToContents)
        h.setStretchLastSection(False)

        self.itemSelectionChanged.connect(self._on_selection)

    # --- veřejné API ---------------------------------------------------------

    def set_filter(self, predicate) -> None:
        self._filter_predicate = predicate
        self.refresh()

    def refresh(self) -> None:
        selected_id = self.selected_thesis_id()
        self.setSortingEnabled(False)
        self.setRowCount(0)

        items = [t for t in self.service.list_theses() if self._filter_predicate(t)]
        items.sort(
            key=lambda t: (
                self._year_sort_key(t.academic_year or ""),
                t.status.order,
                t.display_title.lower(),
            )
        )

        for thesis in items:
            self._add_row(thesis)

        self.setSortingEnabled(True)
        if selected_id:
            self.select_thesis(selected_id)

    def select_thesis(self, thesis_id: str) -> bool:
        for row in range(self.rowCount()):
            item = self.item(row, self.COL_STUDENT)
            if item and item.data(ROLE_THESIS_ID) == thesis_id:
                self.selectRow(row)
                self.scrollToItem(item, QAbstractItemView.ScrollHint.PositionAtCenter)
                return True
        return False

    def selected_thesis_id(self) -> str | None:
        row = self.currentRow()
        if row < 0:
            return None
        item = self.item(row, self.COL_STUDENT)
        return item.data(ROLE_THESIS_ID) if item else None

    # --- privátní ------------------------------------------------------------

    @staticmethod
    def _year_sort_key(year_str: str) -> int:
        try:
            return -int(year_str.split("/")[0])
        except (ValueError, AttributeError, IndexError):
            return 9999

    def _add_row(self, thesis: Thesis) -> None:
        row = self.rowCount()
        self.insertRow(row)

        student = self.service.get_student(thesis.student_id) if thesis.student_id else None
        opponent = self.service.get_opponent(thesis.opponent_id) if thesis.opponent_id else None

        student_name = student.full_name if student else "—"
        title = thesis.display_title
        opponent_name = opponent.name if opponent else "—"
        obor = student.obor if student and student.obor else "—"

        # Student
        student_item = QTableWidgetItem(student_name)
        if student:
            tip_lines = [student.full_name]
            if student.university_id:
                tip_lines.append(f"Os. č.: {student.university_id}")
            if student.form:
                tip_lines.append(f"Forma: {student.form.label}")
            student_item.setToolTip("\n".join(tip_lines))
        else:
            student_item.setToolTip("(bez studenta)")

        # Téma (+ tooltip s plným názvem, kdyby se nevešlo)
        title_item = QTableWidgetItem(title)
        title_item.setToolTip(title)

        # Stav: barevné pozadí + bílý bold text, centrováno
        status_item = QTableWidgetItem(f"  {thesis.status.label}  ")
        status_color = QColor(thesis.status.color)
        status_item.setBackground(QBrush(status_color))
        status_item.setForeground(QBrush(QColor("white")))
        f = status_item.font()
        f.setBold(True)
        status_item.setFont(f)
        status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

        # Oponent
        opponent_item = QTableWidgetItem(opponent_name)
        if opponent:
            tip = opponent.name
            if opponent.affiliation:
                tip += f"\n{opponent.affiliation}"
            tip += f"\n({opponent.kind.label})"
            opponent_item.setToolTip(tip)

        # Obor
        obor_item = QTableWidgetItem(obor)

        items = [student_item, title_item, status_item, opponent_item, obor_item]
        for col, item in enumerate(items):
            item.setData(ROLE_THESIS_ID, thesis.id)
            self.setItem(row, col, item)

    def _on_selection(self) -> None:
        tid = self.selected_thesis_id()
        if tid:
            self.thesis_selected.emit(tid)
