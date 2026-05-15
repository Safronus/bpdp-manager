from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem

from ..models import Thesis
from ..models.enums import ThesisStatus, ThesisType
from ..services import ThesisService

ROLE_THESIS_ID = Qt.ItemDataRole.UserRole + 1
ROLE_KIND = Qt.ItemDataRole.UserRole + 2


class ThesesTreeWidget(QTreeWidget):
    """Strom: Akademický rok → BP/DP → jednotlivé práce."""

    thesis_selected = Signal(str)  # thesis id

    def __init__(self, service: ThesisService, parent=None) -> None:
        super().__init__(parent)
        self.service = service
        self.setHeaderLabels(["Téma / student", "Stav", "Osobní č."])
        self.setColumnWidth(0, 360)
        self.setColumnWidth(1, 160)
        self.setAlternatingRowColors(True)
        self.itemSelectionChanged.connect(self._on_selection)

        self._filter_predicate = lambda t: True  # type: ignore[assignment]

    # --- veřejné API ---------------------------------------------------------

    def set_filter(self, predicate) -> None:
        self._filter_predicate = predicate
        self.refresh()

    def refresh(self) -> None:
        selected_id = self.selected_thesis_id()
        self.clear()

        grouped: dict[str, dict[str, list[Thesis]]] = {}
        for thesis in self.service.list_theses():
            if not self._filter_predicate(thesis):
                continue
            year = thesis.academic_year or "(bez roku)"
            grouped.setdefault(year, {"BP": [], "DP": []})
            grouped[year][thesis.type.value].append(thesis)

        for year in sorted(grouped.keys(), reverse=True):
            year_item = QTreeWidgetItem([f"📅 {year}", "", ""])
            year_item.setData(0, ROLE_KIND, "year")
            font = year_item.font(0)
            font.setBold(True)
            year_item.setFont(0, font)
            self.addTopLevelItem(year_item)

            for type_code in ("BP", "DP"):
                theses = sorted(
                    grouped[year][type_code],
                    key=lambda t: (t.status.order, t.display_title.lower()),
                )
                if not theses:
                    continue
                type_label = ThesisType(type_code).label
                type_item = QTreeWidgetItem([f"{type_label} ({len(theses)})", "", ""])
                type_item.setData(0, ROLE_KIND, "type")
                year_item.addChild(type_item)

                for t in theses:
                    student = self.service.get_student(t.student_id) if t.student_id else None
                    student_str = student.full_name if student else "(bez studenta)"
                    title = t.display_title
                    text = f"{title} — {student_str}"
                    uni_id = student.university_id if student and student.university_id else ""

                    leaf = QTreeWidgetItem([text, t.status.label, uni_id])
                    leaf.setData(0, ROLE_THESIS_ID, t.id)
                    leaf.setData(0, ROLE_KIND, "thesis")
                    brush = QBrush(QColor(t.status.color))
                    leaf.setForeground(1, brush)
                    type_item.addChild(leaf)

                type_item.setExpanded(True)
            year_item.setExpanded(True)

        if selected_id:
            self.select_thesis(selected_id)

    def select_thesis(self, thesis_id: str) -> bool:
        for i in range(self.topLevelItemCount()):
            year_item = self.topLevelItem(i)
            for j in range(year_item.childCount()):
                type_item = year_item.child(j)
                for k in range(type_item.childCount()):
                    leaf = type_item.child(k)
                    if leaf.data(0, ROLE_THESIS_ID) == thesis_id:
                        self.setCurrentItem(leaf)
                        return True
        return False

    def selected_thesis_id(self) -> str | None:
        item = self.currentItem()
        if item is None:
            return None
        return item.data(0, ROLE_THESIS_ID)

    # --- privátní ------------------------------------------------------------

    def _on_selection(self) -> None:
        tid = self.selected_thesis_id()
        if tid:
            self.thesis_selected.emit(tid)
