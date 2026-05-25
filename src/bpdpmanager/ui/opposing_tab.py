"""Záložka 'Oponentské posudky' — strom kategorizovaný podle ak. roků + detail."""

from __future__ import annotations

import locale
import unicodedata

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QPushButton,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..models import OpposingThesis
from ..models.enums import ThesisType
from ..services import ThesisService
from .opposing_detail import OpposingDetail

ROLE_ID = Qt.ItemDataRole.UserRole + 1

# Reuse Czech locale setup from theses_tree
_HAS_CZECH_LOCALE = False
for _loc in ("cs_CZ.UTF-8", "cs_CZ.utf8", "cs_CZ"):
    try:
        locale.setlocale(locale.LC_COLLATE, _loc)
        _HAS_CZECH_LOCALE = True
        break
    except locale.Error:
        continue


def _czech_key(s: str) -> str:
    if not s:
        return ""
    if _HAS_CZECH_LOCALE:
        return locale.strxfrm(s.casefold())
    nfd = unicodedata.normalize("NFD", s)
    return "".join(c for c in nfd if not unicodedata.combining(c)).casefold()


class _NewOpposingDialog(QDialog):
    """Dialog na rychlé založení nového posudku — typ + rok."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Nový oponentský posudek")
        self.setMinimumWidth(380)
        v = QVBoxLayout(self)
        form = QFormLayout()
        self.cb_type = QComboBox()
        for t in ThesisType:
            self.cb_type.addItem(t.label, t.value)
        form.addRow("Typ", self.cb_type)
        self.ed_year = QLineEdit()
        from datetime import date
        today = date.today()
        start = today.year if today.month >= 9 else today.year - 1
        self.ed_year.setText(f"{start}/{start + 1}")
        form.addRow("Akademický rok", self.ed_year)
        v.addLayout(form)
        bb = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)

    @property
    def type_value(self) -> str:
        return self.cb_type.currentData()

    @property
    def year(self) -> str:
        return self.ed_year.text().strip()


class OpposingTab(QWidget):
    """Vertikální splitter: strom posudků nahoře + detail dole."""

    def __init__(self, service: ThesisService, parent=None) -> None:
        super().__init__(parent)
        self.service = service

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        # Toolbar uvnitř tabu
        top = QHBoxLayout()
        top.setContentsMargins(6, 6, 6, 0)
        btn_new = QPushButton("➕ Nový oponentský posudek…")
        btn_new.clicked.connect(self._new_opposing)
        top.addWidget(btn_new)
        top.addStretch()
        self.lbl_count = QLabel("")
        self.lbl_count.setStyleSheet("color:#888;font-size:11px;")
        top.addWidget(self.lbl_count)
        outer.addLayout(top)

        # Splitter
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setChildrenCollapsible(False)

        self.tree = QTreeWidget()
        self.tree.setColumnCount(5)
        self.tree.setHeaderLabels(["Student / Skupina", "Téma", "Vedoucí", "Známky", "Obor"])
        self.tree.setAlternatingRowColors(True)
        self.tree.setRootIsDecorated(True)
        self.tree.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tree.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tree.setMinimumHeight(160)
        h = self.tree.header()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        h.setStretchLastSection(False)
        self.tree.itemSelectionChanged.connect(self._on_selection_changed)
        splitter.addWidget(self.tree)

        self.detail = OpposingDetail(service)
        self.detail.setMinimumHeight(520)
        self.detail.saved.connect(lambda _: self.refresh())
        self.detail.deleted.connect(lambda _: self.refresh())
        splitter.addWidget(self.detail)

        splitter.setSizes([260, 640])
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        outer.addWidget(splitter, stretch=1)

        self.refresh()

    # --- načtení / refresh --------------------------------------------------

    def refresh(self) -> None:
        selected_id = self._selected_id()
        self.tree.blockSignals(True)
        try:
            self.tree.clear()
            opposings = self.service.list_opposing_theses()
            # group by academic_year
            groups: dict[str, list[OpposingThesis]] = {}
            for op in opposings:
                groups.setdefault(op.academic_year or "(bez roku)", []).append(op)

            for year in sorted(groups.keys(), reverse=True):
                year_item = QTreeWidgetItem(
                    [f"📅 {year}    ({len(groups[year])})", "", "", "", ""]
                )
                year_item.setFirstColumnSpanned(True)
                f = year_item.font(0)
                f.setBold(True)
                f.setPointSize(f.pointSize() + 1)
                year_item.setFont(0, f)
                self.tree.addTopLevelItem(year_item)

                ops = sorted(
                    groups[year],
                    key=lambda o: (
                        o.type.value,
                        _czech_key(o.student_last_name),
                        _czech_key(o.student_first_name),
                    ),
                )
                for op in ops:
                    name = (
                        f"{op.student_last_name}, {op.student_first_name}"
                        if op.student_last_name or op.student_first_name
                        else "(neuvedený student)"
                    )
                    title = op.title_cs or "(bez názvu)"
                    grades = self._format_grades(op)
                    obor = op.student_obor or "—"
                    type_prefix = op.type.value
                    leaf = QTreeWidgetItem(
                        [
                            f"{type_prefix} · {name}",
                            title,
                            op.supervisor_name or "—",
                            grades,
                            obor,
                        ]
                    )
                    leaf.setData(0, ROLE_ID, op.id)
                    year_item.addChild(leaf)
                year_item.setExpanded(True)

            self.lbl_count.setText(f"Posudků celkem: {len(opposings)}")

            if selected_id:
                self._select_id(selected_id)
        finally:
            self.tree.blockSignals(False)

    @staticmethod
    def _format_grades(op: OpposingThesis) -> str:
        sup = op.grade_supervisor or "—"
        opp = op.grade_opponent or "—"
        return f"V: {sup}  /  O: {opp}"

    def _selected_id(self) -> str | None:
        item = self.tree.currentItem()
        if item is None:
            return None
        return item.data(0, ROLE_ID)

    def _select_id(self, op_id: str) -> bool:
        for i in range(self.tree.topLevelItemCount()):
            year_item = self.tree.topLevelItem(i)
            for j in range(year_item.childCount()):
                leaf = year_item.child(j)
                if leaf.data(0, ROLE_ID) == op_id:
                    self.tree.setCurrentItem(leaf)
                    return True
        return False

    def _on_selection_changed(self) -> None:
        op_id = self._selected_id()
        if op_id is None:
            self.detail.set_opposing(None)
            return
        op = self.service.get_opposing_thesis(op_id)
        self.detail.set_opposing(op)

    # --- akce ---------------------------------------------------------------

    def _new_opposing(self) -> None:
        dlg = _NewOpposingDialog(self)
        if not dlg.exec():
            return
        if not dlg.year:
            return
        op = OpposingThesis(
            type=ThesisType(dlg.type_value),
            academic_year=dlg.year,
        )
        self.service.upsert_opposing_thesis(op)
        self.refresh()
        self._select_id(op.id)
