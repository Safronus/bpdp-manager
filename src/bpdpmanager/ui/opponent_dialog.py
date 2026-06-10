from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QVBoxLayout,
)

from ..i18n import tr
from ..models import Opponent
from ..models.enums import OpponentKind
from ..services import ThesisService


class OpponentDialog(QDialog):
    """Dialog pro vytvoření/úpravu oponenta.

    Pole se mění podle typu:
      - Interní: jméno, email, pracoviště, poznámka
      - Externí: jméno, email, telefon, adresa, pracoviště, poznámka
    """

    def __init__(
        self,
        service: ThesisService,
        opponent: Opponent | None = None,
        default_kind: OpponentKind = OpponentKind.INTERNAL,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.service = service
        self.opponent = opponent or Opponent(name="", kind=default_kind)
        self.setWindowTitle("Oponent" if opponent else "Nový oponent")
        self.setMinimumWidth(460)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.cb_kind = QComboBox()
        for k in OpponentKind:
            self.cb_kind.addItem(k.label, k.value)
        idx = self.cb_kind.findData(self.opponent.kind.value)
        self.cb_kind.setCurrentIndex(max(idx, 0))
        self.cb_kind.currentIndexChanged.connect(self._on_kind_change)
        form.addRow(tr("Typ"), self.cb_kind)

        self.ed_title_before = QLineEdit(self.opponent.title_before)
        self.ed_title_before.setPlaceholderText(tr("např. doc. Ing."))
        form.addRow(tr("Tituly před"), self.ed_title_before)

        self.ed_name = QLineEdit(self.opponent.name)
        self.ed_name.setPlaceholderText(tr("např. Petr Novák"))
        form.addRow(tr("Jméno"), self.ed_name)

        self.ed_title_after = QLineEdit(self.opponent.title_after)
        self.ed_title_after.setPlaceholderText(tr("např. Ph.D."))
        form.addRow(tr("Tituly za"), self.ed_title_after)

        self.ed_email = QLineEdit(self.opponent.email or "")
        form.addRow("Email", self.ed_email)

        # Externí pole — viditelná jen pro externí
        self.ed_phone = QLineEdit(self.opponent.phone or "")
        self.lbl_phone = QLabel(tr("Telefon"))
        form.addRow(self.lbl_phone, self.ed_phone)

        self.ed_address = QPlainTextEdit(self.opponent.address or "")
        self.ed_address.setMaximumHeight(60)
        self.lbl_address = QLabel(tr("Adresa"))
        form.addRow(self.lbl_address, self.ed_address)

        self.ed_affiliation = QLineEdit(self.opponent.affiliation or "")
        form.addRow(tr("Pracoviště / firma"), self.ed_affiliation)

        self.ed_note = QPlainTextEdit(self.opponent.note or "")
        self.ed_note.setMaximumHeight(80)
        form.addRow(tr("Poznámka"), self.ed_note)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._apply_kind_visibility()

    def _on_kind_change(self) -> None:
        self._apply_kind_visibility()

    def _apply_kind_visibility(self) -> None:
        is_external = self.cb_kind.currentData() == OpponentKind.EXTERNAL.value
        self.lbl_phone.setVisible(is_external)
        self.ed_phone.setVisible(is_external)
        self.lbl_address.setVisible(is_external)
        self.ed_address.setVisible(is_external)

    def _on_accept(self) -> None:
        name = self.ed_name.text().strip()
        if not name:
            return
        kind = OpponentKind(self.cb_kind.currentData())
        self.opponent.kind = kind
        self.opponent.name = name
        self.opponent.title_before = self.ed_title_before.text().strip()
        self.opponent.title_after = self.ed_title_after.text().strip()
        self.opponent.email = self.ed_email.text().strip() or None
        self.opponent.affiliation = self.ed_affiliation.text().strip() or None
        if kind == OpponentKind.EXTERNAL:
            self.opponent.phone = self.ed_phone.text().strip() or None
            self.opponent.address = self.ed_address.toPlainText().strip() or None
        else:
            self.opponent.phone = None
            self.opponent.address = None
        self.opponent.note = self.ed_note.toPlainText().strip() or None
        self.service.upsert_opponent(self.opponent)
        self.accept()
