from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QPlainTextEdit,
    QVBoxLayout,
)

from ..models import Opponent
from ..services import ThesisService


class OpponentDialog(QDialog):
    def __init__(self, service: ThesisService, opponent: Opponent | None = None, parent=None) -> None:
        super().__init__(parent)
        self.service = service
        self.opponent = opponent or Opponent(name="")
        self.setWindowTitle("Oponent" if opponent else "Nový oponent")
        self.setMinimumWidth(420)

        form = QFormLayout()
        self.ed_name = QLineEdit(self.opponent.name)
        self.ed_email = QLineEdit(self.opponent.email or "")
        self.ed_affiliation = QLineEdit(self.opponent.affiliation or "")
        self.ed_note = QPlainTextEdit(self.opponent.note or "")
        self.ed_note.setMaximumHeight(80)

        form.addRow("Jméno", self.ed_name)
        form.addRow("Email", self.ed_email)
        form.addRow("Pracoviště", self.ed_affiliation)
        form.addRow("Poznámka", self.ed_note)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _on_accept(self) -> None:
        self.opponent.name = self.ed_name.text().strip()
        self.opponent.email = self.ed_email.text().strip() or None
        self.opponent.affiliation = self.ed_affiliation.text().strip() or None
        self.opponent.note = self.ed_note.toPlainText().strip() or None
        if not self.opponent.name:
            return
        self.service.upsert_opponent(self.opponent)
        self.accept()
