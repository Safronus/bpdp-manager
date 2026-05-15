"""Dialogy pro správu seznamů (studenti, oponenti, obory)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..models import Opponent, Student
from ..models.enums import OpponentKind
from ..services import ThesisService
from .opponent_dialog import OpponentDialog
from .student_dialog import StudentDialog


class StudentsManageDialog(QDialog):
    def __init__(self, service: ThesisService, parent=None) -> None:
        super().__init__(parent)
        self.service = service
        self.setWindowTitle("Studenti")
        self.setMinimumSize(560, 480)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Seznam studentů"))

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
        btn_close.clicked.connect(self.accept)
        row.addWidget(btn_new)
        row.addWidget(btn_edit)
        row.addWidget(btn_delete)
        row.addStretch()
        row.addWidget(btn_close)
        layout.addLayout(row)

        self._refresh()

    def _refresh(self) -> None:
        self.list_widget.clear()
        for s in self.service.list_students():
            label = f"{s.full_name} — {s.display_obor}"
            if s.university_id:
                label += f"  [{s.university_id}]"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, s)
            self.list_widget.addItem(item)

    def _current(self) -> Student | None:
        item = self.list_widget.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _new(self) -> None:
        dlg = StudentDialog(self.service, parent=self)
        if dlg.exec():
            self._refresh()

    def _edit(self) -> None:
        s = self._current()
        if s is None:
            return
        dlg = StudentDialog(self.service, s, parent=self)
        if dlg.exec():
            self._refresh()

    def _delete(self) -> None:
        s = self._current()
        if s is None:
            return
        confirm = QMessageBox.question(
            self,
            "Smazat studenta",
            f"Opravdu smazat „{s.full_name}“? Práce, které ho mají přiřazeného, zůstanou (bez studenta).",
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.service.delete_student(s.id)
            self._refresh()


class OpponentsManageDialog(QDialog):
    """Správa oponentů — odděleně interní a externí."""

    def __init__(self, service: ThesisService, parent=None) -> None:
        super().__init__(parent)
        self.service = service
        self.setWindowTitle("Oponenti")
        self.setMinimumSize(640, 520)

        layout = QVBoxLayout(self)

        self.tabs = QTabWidget()
        self.list_internal = self._build_list_tab(OpponentKind.INTERNAL)
        self.list_external = self._build_list_tab(OpponentKind.EXTERNAL)
        self.tabs.addTab(self.list_internal, "Interní (UTB)")
        self.tabs.addTab(self.list_external, "Externí")
        layout.addWidget(self.tabs)

        row = QHBoxLayout()
        btn_new = QPushButton("Nový…")
        btn_edit = QPushButton("Upravit…")
        btn_delete = QPushButton("Smazat")
        btn_close = QPushButton("Zavřít")
        btn_new.clicked.connect(self._new)
        btn_edit.clicked.connect(self._edit)
        btn_delete.clicked.connect(self._delete)
        btn_close.clicked.connect(self.accept)
        row.addWidget(btn_new)
        row.addWidget(btn_edit)
        row.addWidget(btn_delete)
        row.addStretch()
        row.addWidget(btn_close)
        layout.addLayout(row)

        self._refresh()

    def _build_list_tab(self, kind: OpponentKind) -> QListWidget:
        lw = QListWidget()
        lw.itemDoubleClicked.connect(self._edit)
        lw.setProperty("opponent_kind", kind.value)
        return lw

    def _current_list(self) -> QListWidget:
        return self.tabs.currentWidget()  # type: ignore[return-value]

    def _current_kind(self) -> OpponentKind:
        return OpponentKind(self._current_list().property("opponent_kind"))

    def _refresh(self) -> None:
        for lw, kind in (
            (self.list_internal, OpponentKind.INTERNAL),
            (self.list_external, OpponentKind.EXTERNAL),
        ):
            lw.clear()
            for o in self.service.list_opponents(kind=kind):
                parts = [o.name]
                if o.affiliation:
                    parts.append(f"({o.affiliation})")
                if o.email:
                    parts.append(f"✉ {o.email}")
                if o.phone and kind == OpponentKind.EXTERNAL:
                    parts.append(f"☎ {o.phone}")
                item = QListWidgetItem(" ".join(parts))
                item.setData(Qt.ItemDataRole.UserRole, o)
                lw.addItem(item)

    def _current_opp(self) -> Opponent | None:
        lw = self._current_list()
        item = lw.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _new(self) -> None:
        dlg = OpponentDialog(self.service, default_kind=self._current_kind(), parent=self)
        if dlg.exec():
            self._refresh()

    def _edit(self) -> None:
        o = self._current_opp()
        if o is None:
            return
        dlg = OpponentDialog(self.service, o, parent=self)
        if dlg.exec():
            self._refresh()

    def _delete(self) -> None:
        o = self._current_opp()
        if o is None:
            return
        confirm = QMessageBox.question(
            self,
            "Smazat oponenta",
            f"Opravdu smazat „{o.name}“? Práce, které ho mají přiřazeného, zůstanou (bez oponenta).",
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.service.delete_opponent(o.id)
            self._refresh()


class OboryManageDialog(QDialog):
    """Správa číselníku studijních oborů."""

    def __init__(self, service: ThesisService, parent=None) -> None:
        super().__init__(parent)
        self.service = service
        self.setWindowTitle("Studijní obory")
        self.setMinimumSize(480, 480)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Seznam studijních oborů (např. NSWI-P, NKYB-K)"))

        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self._rename)
        layout.addWidget(self.list_widget)

        self.lbl_info = QLabel("")
        self.lbl_info.setStyleSheet("color: #888;")
        layout.addWidget(self.lbl_info)

        row = QHBoxLayout()
        btn_new = QPushButton("+ Přidat…")
        btn_rename = QPushButton("Přejmenovat…")
        btn_delete = QPushButton("Smazat")
        btn_close = QPushButton("Zavřít")
        btn_new.clicked.connect(self._new)
        btn_rename.clicked.connect(self._rename)
        btn_delete.clicked.connect(self._delete)
        btn_close.clicked.connect(self.accept)
        row.addWidget(btn_new)
        row.addWidget(btn_rename)
        row.addWidget(btn_delete)
        row.addStretch()
        row.addWidget(btn_close)
        layout.addLayout(row)

        self.list_widget.currentRowChanged.connect(self._update_info)
        self._refresh()

    def _refresh(self) -> None:
        self.list_widget.clear()
        for name in self.service.list_obory():
            count = self.service.obor_usage_count(name)
            label = f"{name}    (studentů: {count})"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, name)
            self.list_widget.addItem(item)
        self._update_info(self.list_widget.currentRow())

    def _current(self) -> str | None:
        item = self.list_widget.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _update_info(self, _row: int) -> None:
        name = self._current()
        if not name:
            self.lbl_info.setText("")
            return
        count = self.service.obor_usage_count(name)
        if count == 0:
            self.lbl_info.setText(f"Obor „{name}“ není přiřazen žádnému studentovi.")
        else:
            self.lbl_info.setText(f"Obor „{name}“ je přiřazen u {count} studentů.")

    def _new(self) -> None:
        text, ok = QInputDialog.getText(self, "Nový obor", "Zkratka oboru (např. NSWI-P):")
        if ok and text.strip():
            self.service.add_obor(text.strip())
            self._refresh()

    def _rename(self) -> None:
        current = self._current()
        if current is None:
            return
        text, ok = QInputDialog.getText(
            self,
            "Přejmenovat obor",
            f"Nový název pro „{current}“:",
            text=current,
        )
        if not ok or not text.strip() or text.strip() == current:
            return
        count = self.service.rename_obor(current, text.strip())
        QMessageBox.information(
            self,
            "Hotovo",
            f"Obor přejmenován. Aktualizováno studentů: {count}.",
        )
        self._refresh()

    def _delete(self) -> None:
        current = self._current()
        if current is None:
            return
        count = self.service.obor_usage_count(current)
        msg = f"Opravdu smazat obor „{current}“?"
        if count:
            msg += f"\n\nU {count} studentů bude pole „obor“ vyprázdněno."
        confirm = QMessageBox.question(self, "Smazat obor", msg)
        if confirm == QMessageBox.StandardButton.Yes:
            self.service.remove_obor(current)
            self._refresh()
