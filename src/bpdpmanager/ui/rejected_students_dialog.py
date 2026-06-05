"""Evidence odmítnutých zájemců o vedení (jméno, obor, akademický rok)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
)

from ..models import RejectedStudent
from ..services import ThesisService


class RejectedStudentsDialog(QDialog):
    """Správa seznamu odmítnutých zájemců — souvisí s kapacitou vedení."""

    def __init__(self, service: ThesisService, parent=None) -> None:
        super().__init__(parent)
        self.service = service
        self.setWindowTitle("Odmítnutí zájemci")
        self.setMinimumSize(620, 460)

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "Evidence zájemců, které jsi <b>odmítl(a)</b> vést (souvisí "
                "s kapacitou vedení). Promítá se do <b>Statistik</b>.",
                textFormat=Qt.TextFormat.RichText,
            )
        )

        self.tree = QTreeWidget()
        self.tree.setColumnCount(3)
        self.tree.setHeaderLabels(["Jméno", "Obor", "Akademický rok"])
        self.tree.setRootIsDecorated(False)
        self.tree.setAlternatingRowColors(True)
        h = self.tree.header()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.tree, stretch=1)

        # ── Přidat ──────────────────────────────────────────────────────────
        add_row = QHBoxLayout()
        self.ed_name = QLineEdit()
        self.ed_name.setPlaceholderText("Jméno a příjmení")
        self.cb_obor = QComboBox()
        self.cb_obor.setEditable(True)
        self.cb_obor.addItem("")
        for o in self.service.list_obor_objects():
            self.cb_obor.addItem(o.name)
        self.cb_obor.lineEdit().setPlaceholderText("Obor")
        self.cb_obor.setMinimumWidth(140)
        self.ed_year = QLineEdit(ThesisService.next_academic_year())
        self.ed_year.setPlaceholderText("2026/2027")
        self.ed_year.setMaximumWidth(110)
        self.ed_name.returnPressed.connect(self._add)
        btn_add = QPushButton("+ Přidat")
        btn_add.clicked.connect(self._add)
        add_row.addWidget(self.ed_name, stretch=2)
        add_row.addWidget(self.cb_obor, stretch=1)
        add_row.addWidget(self.ed_year)
        add_row.addWidget(btn_add)
        layout.addLayout(add_row)

        # ── Tlačítka ────────────────────────────────────────────────────────
        row = QHBoxLayout()
        btn_remove = QPushButton("Odebrat vybrané")
        btn_remove.clicked.connect(self._remove)
        btn_close = QPushButton("Zavřít")
        btn_close.clicked.connect(self.accept)
        row.addWidget(btn_remove)
        row.addStretch()
        row.addWidget(btn_close)
        layout.addLayout(row)

        self._refresh()

    def _refresh(self) -> None:
        self.tree.clear()
        for r in self.service.list_rejected_students():
            item = QTreeWidgetItem([r.name or "—", r.obor or "—", r.academic_year or "—"])
            item.setData(0, Qt.ItemDataRole.UserRole, r.id)
            self.tree.addTopLevelItem(item)

    def _add(self) -> None:
        name = self.ed_name.text().strip()
        if not name:
            QMessageBox.information(self, "Odmítnutí zájemci", "Zadej alespoň jméno.")
            return
        self.service.upsert_rejected_student(
            RejectedStudent(
                name=name,
                obor=self.cb_obor.currentText().strip(),
                academic_year=self.ed_year.text().strip(),
            )
        )
        self.ed_name.clear()
        self.ed_name.setFocus()
        self._refresh()

    def _remove(self) -> None:
        item = self.tree.currentItem()
        if item is None:
            return
        rej_id = item.data(0, Qt.ItemDataRole.UserRole)
        if rej_id:
            self.service.remove_rejected_student(rej_id)
            self._refresh()
