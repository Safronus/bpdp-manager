from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class StringListEditor(QWidget):
    """Editor seznamu řetězců — pro body zadání a literaturu."""

    changed = Signal()

    def __init__(self, items: list[str] | None = None, parent=None, placeholder: str = "Nová položka") -> None:
        super().__init__(parent)
        self._placeholder = placeholder

        self.list_widget = QListWidget()
        self.list_widget.setEditTriggers(
            QListWidget.EditTrigger.DoubleClicked | QListWidget.EditTrigger.SelectedClicked
        )
        self.list_widget.itemChanged.connect(lambda _: self.changed.emit())

        self.btn_add = QPushButton("+ Přidat")
        self.btn_remove = QPushButton("− Odebrat")
        self.btn_up = QPushButton("↑")
        self.btn_down = QPushButton("↓")

        self.btn_add.clicked.connect(self._add)
        self.btn_remove.clicked.connect(self._remove)
        self.btn_up.clicked.connect(lambda: self._move(-1))
        self.btn_down.clicked.connect(lambda: self._move(1))

        buttons = QHBoxLayout()
        buttons.addWidget(self.btn_add)
        buttons.addWidget(self.btn_remove)
        buttons.addStretch()
        buttons.addWidget(self.btn_up)
        buttons.addWidget(self.btn_down)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.list_widget)
        layout.addLayout(buttons)

        self.set_items(items or [])

    def set_items(self, items: list[str]) -> None:
        self.list_widget.clear()
        for text in items:
            self._append_item(text)

    def items(self) -> list[str]:
        return [
            self.list_widget.item(i).text()
            for i in range(self.list_widget.count())
            if self.list_widget.item(i).text().strip()
        ]

    def _append_item(self, text: str) -> None:
        item = QListWidgetItem(text)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
        self.list_widget.addItem(item)

    def _add(self) -> None:
        text, ok = QInputDialog.getMultiLineText(self, "Nová položka", self._placeholder)
        if ok and text.strip():
            self._append_item(text.strip())
            self.changed.emit()

    def _remove(self) -> None:
        row = self.list_widget.currentRow()
        if row >= 0:
            self.list_widget.takeItem(row)
            self.changed.emit()

    def _move(self, delta: int) -> None:
        row = self.list_widget.currentRow()
        new_row = row + delta
        if row < 0 or new_row < 0 or new_row >= self.list_widget.count():
            return
        item = self.list_widget.takeItem(row)
        self.list_widget.insertItem(new_row, item)
        self.list_widget.setCurrentRow(new_row)
        self.changed.emit()
