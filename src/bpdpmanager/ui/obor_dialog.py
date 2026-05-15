"""Dialog pro vytvoření a editaci studijního oboru (vč. sekretářky)."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QVBoxLayout,
)

from ..models import Obor
from ..services import ThesisService


class OborDialog(QDialog):
    """Editace oboru: název + volitelný kontakt na sekretářku."""

    def __init__(
        self,
        service: ThesisService,
        obor: Obor | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.service = service
        self.obor = obor or Obor(name="")
        self._original_name = self.obor.name
        self.setWindowTitle("Obor" if obor else "Nový obor")
        self.setMinimumWidth(440)

        layout = QVBoxLayout(self)

        # Základní info
        base_form = QFormLayout()
        self.ed_name = QLineEdit(self.obor.name)
        self.ed_name.setPlaceholderText("např. NSWI-P")
        base_form.addRow("Název oboru", self.ed_name)
        layout.addLayout(base_form)

        # Sekretářka
        sec_box = QGroupBox("Sekretářka oboru (volitelné)")
        sec_form = QFormLayout(sec_box)
        self.ed_sec_name = QLineEdit(self.obor.secretary_name or "")
        self.ed_sec_name.setPlaceholderText("Jméno a příjmení")
        self.ed_sec_email = QLineEdit(self.obor.secretary_email or "")
        self.ed_sec_email.setPlaceholderText("email@utb.cz")
        self.ed_sec_phone = QLineEdit(self.obor.secretary_phone or "")
        self.ed_sec_phone.setPlaceholderText("+420 …")
        sec_form.addRow("Jméno", self.ed_sec_name)
        sec_form.addRow("Email", self.ed_sec_email)
        sec_form.addRow("Telefon", self.ed_sec_phone)
        layout.addWidget(sec_box)

        # Poznámka
        self.ed_note = QPlainTextEdit(self.obor.note or "")
        self.ed_note.setMaximumHeight(80)
        layout.addWidget(QLabel("Poznámka"))
        layout.addWidget(self.ed_note)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_accept(self) -> None:
        new_name = self.ed_name.text().strip()
        if not new_name:
            return

        # Pokud došlo k přejmenování existujícího oboru, použij rename_obor,
        # aby se synchronizovali studenti.
        if self._original_name and self._original_name != new_name:
            self.service.rename_obor(self._original_name, new_name)
            # po renamenutí načti aktuální záznam, abychom nepřepsali sloučený
            existing = self.service.get_obor(new_name)
            if existing is not None:
                self.obor = existing

        self.obor.name = new_name
        self.obor.secretary_name = self.ed_sec_name.text().strip() or None
        self.obor.secretary_email = self.ed_sec_email.text().strip() or None
        self.obor.secretary_phone = self.ed_sec_phone.text().strip() or None
        self.obor.note = self.ed_note.toPlainText().strip() or None

        self.service.upsert_obor(self.obor)
        self.accept()
