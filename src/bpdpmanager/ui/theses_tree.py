"""Stromový pohled na práce s grupováním (rok → BP/DP) a sloupci tabulky."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QTreeWidget,
    QTreeWidgetItem,
)

from ..models import Thesis
from ..models.enums import ThesisType
from ..services import ThesisService

ROLE_THESIS_ID = Qt.ItemDataRole.UserRole + 1
ROLE_KIND = Qt.ItemDataRole.UserRole + 2  # "year" | "type" | "thesis"


class ThesesTreeWidget(QTreeWidget):
    """Strom prací: Akademický rok → BP/DP → jednotlivé práce.

    Sloupce u prací: Student | Téma | Stav | Oponent | Obor.
    Stav má barevné pozadí podle ``ThesisStatus.color``.
    Sekční řádky (rok, typ) overspan přes celou šířku.
    """

    thesis_selected = Signal(str)

    HEADERS = ["Student / Skupina", "Téma", "Stav", "Oponent", "Obor"]
    COL_STUDENT = 0
    COL_TITLE = 1
    COL_STATUS = 2
    COL_OPPONENT = 3
    COL_OBOR = 4

    def __init__(self, service: ThesisService, parent=None) -> None:
        super().__init__(parent)
        self.service = service
        self._filter_predicate = lambda t: True

        self.setColumnCount(len(self.HEADERS))
        self.setHeaderLabels(self.HEADERS)
        self.setRootIsDecorated(True)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSortingEnabled(False)

        h = self.header()
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
        # zapamatuj si rozbalené roky (po refresh chceme zachovat stav)
        expanded_years = self._snapshot_expanded()
        self.clear()

        groups: dict[str, dict[str, list[Thesis]]] = {}
        for thesis in self.service.list_theses():
            if not self._filter_predicate(thesis):
                continue
            year = thesis.academic_year or "(bez roku)"
            groups.setdefault(year, {"BP": [], "DP": []})
            groups[year][thesis.type.value].append(thesis)

        for year in sorted(groups.keys(), reverse=True):
            total = sum(len(v) for v in groups[year].values())
            year_item = QTreeWidgetItem([f"📅 {year}    ({total})", "", "", "", ""])
            year_item.setData(0, ROLE_KIND, "year")
            year_item.setData(0, Qt.ItemDataRole.UserRole + 3, year)  # ulož klíč pro snapshot
            font = year_item.font(0)
            font.setBold(True)
            font.setPointSize(font.pointSize() + 1)
            year_item.setFont(0, font)
            year_item.setFirstColumnSpanned(True)
            self.addTopLevelItem(year_item)

            for type_code in ("BP", "DP"):
                theses = groups[year][type_code]
                if not theses:
                    continue
                theses.sort(key=lambda t: (t.status.order, t.display_title.lower()))

                type_label = ThesisType(type_code).label
                type_item = QTreeWidgetItem(
                    [f"  {type_label}  ({len(theses)})", "", "", "", ""]
                )
                type_item.setData(0, ROLE_KIND, "type")
                type_font = type_item.font(0)
                type_font.setItalic(True)
                type_item.setFont(0, type_font)
                type_item.setFirstColumnSpanned(True)
                year_item.addChild(type_item)

                for thesis in theses:
                    self._add_thesis_row(type_item, thesis)

                type_item.setExpanded(True)

            # rok rozbal pokud byl rozbalený před refresh (default: rozbalený)
            year_item.setExpanded(expanded_years.get(year, True))

        if selected_id:
            # Blokuj signál během programového re-výběru, aby autosave →
            # tree.refresh nezavolal set_thesis na detailu (jinak by se kurzor
            # v aktivním textovém poli vracel na začátek).
            self.blockSignals(True)
            try:
                self.select_thesis(selected_id)
            finally:
                self.blockSignals(False)

    def select_thesis(self, thesis_id: str) -> bool:
        for i in range(self.topLevelItemCount()):
            year_item = self.topLevelItem(i)
            for j in range(year_item.childCount()):
                type_item = year_item.child(j)
                for k in range(type_item.childCount()):
                    leaf = type_item.child(k)
                    if leaf.data(0, ROLE_THESIS_ID) == thesis_id:
                        self.setCurrentItem(leaf)
                        self.scrollToItem(
                            leaf, QAbstractItemView.ScrollHint.PositionAtCenter
                        )
                        return True
        return False

    def selected_thesis_id(self) -> str | None:
        item = self.currentItem()
        if item is None:
            return None
        return item.data(0, ROLE_THESIS_ID)

    # --- privátní ------------------------------------------------------------

    def _snapshot_expanded(self) -> dict[str, bool]:
        out: dict[str, bool] = {}
        for i in range(self.topLevelItemCount()):
            year_item = self.topLevelItem(i)
            year_key = year_item.data(0, Qt.ItemDataRole.UserRole + 3)
            if year_key:
                out[year_key] = year_item.isExpanded()
        return out

    def _add_thesis_row(self, parent: QTreeWidgetItem, thesis: Thesis) -> None:
        student = self.service.get_student(thesis.student_id) if thesis.student_id else None
        opponent = self.service.get_opponent(thesis.opponent_id) if thesis.opponent_id else None

        student_name = student.full_name if student else "—"
        title = thesis.display_title
        opponent_name = opponent.name if opponent else "—"
        obor = student.obor if student and student.obor else "—"

        leaf = QTreeWidgetItem(
            [student_name, title, f"  {thesis.status.label}  ", opponent_name, obor]
        )
        leaf.setData(0, ROLE_KIND, "thesis")
        leaf.setData(0, ROLE_THESIS_ID, thesis.id)

        # Barevný stav: pozadí + bílý bold text, centrováno
        status_color = QColor(thesis.status.color)
        leaf.setBackground(self.COL_STATUS, QBrush(status_color))
        leaf.setForeground(self.COL_STATUS, QBrush(QColor("white")))
        font = leaf.font(self.COL_STATUS)
        font.setBold(True)
        leaf.setFont(self.COL_STATUS, font)
        leaf.setTextAlignment(
            self.COL_STATUS, Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
        )

        # Tooltipy
        if student:
            tip = student.full_name
            if student.university_id:
                tip += f"\nOs. č.: {student.university_id}"
            if student.form:
                tip += f"\nForma: {student.form.label}"
            leaf.setToolTip(self.COL_STUDENT, tip)
        else:
            leaf.setToolTip(self.COL_STUDENT, "(bez studenta)")

        leaf.setToolTip(self.COL_TITLE, title)

        if opponent:
            tip = opponent.name
            if opponent.affiliation:
                tip += f"\n{opponent.affiliation}"
            tip += f"\n({opponent.kind.label})"
            leaf.setToolTip(self.COL_OPPONENT, tip)

        parent.addChild(leaf)

    def _on_selection(self) -> None:
        tid = self.selected_thesis_id()
        if tid:
            self.thesis_selected.emit(tid)
