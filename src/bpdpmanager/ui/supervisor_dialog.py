"""Dialog pro vytvoření/úpravu vedoucího cizí BP/DP (registr pro oponentské posudky)."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QPlainTextEdit,
    QVBoxLayout,
)

from ..models import Supervisor
from ..services import ThesisService


class SupervisorDialog(QDialog):
    def __init__(
        self,
        service: ThesisService,
        supervisor: Supervisor | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.service = service
        self.supervisor = supervisor or Supervisor(name="")
        self.setWindowTitle("Vedoucí" if supervisor else "Nový vedoucí")
        self.setMinimumWidth(460)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.ed_name = QLineEdit(self.supervisor.name)
        self.ed_name.setPlaceholderText("např. doc. Ing. Petr Novák, Ph.D.")
        form.addRow("Jméno", self.ed_name)

        self.ed_email = QLineEdit(self.supervisor.email or "")
        self.ed_email.setPlaceholderText("novak@utb.cz")
        form.addRow("Email", self.ed_email)

        self.ed_affiliation = QLineEdit(self.supervisor.affiliation or "")
        self.ed_affiliation.setPlaceholderText("např. FAI UTB / FAV ZČU / externí")
        form.addRow("Pracoviště", self.ed_affiliation)

        self.ed_phone = QLineEdit(self.supervisor.phone or "")
        self.ed_phone.setPlaceholderText("+420 …")
        form.addRow("Telefon", self.ed_phone)

        self.ed_note = QPlainTextEdit(self.supervisor.note or "")
        self.ed_note.setMaximumHeight(80)
        form.addRow("Poznámka", self.ed_note)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_accept(self) -> None:
        name = self.ed_name.text().strip()
        if not name:
            return
        self.supervisor.name = name
        self.supervisor.email = self.ed_email.text().strip() or None
        self.supervisor.affiliation = self.ed_affiliation.text().strip() or None
        self.supervisor.phone = self.ed_phone.text().strip() or None
        self.supervisor.note = self.ed_note.toPlainText().strip() or None
        self.service.upsert_supervisor(self.supervisor)
        self.accept()
