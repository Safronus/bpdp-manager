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

from ..models import Student
from ..models.student import derive_form_from_obor
from ..services import ThesisService


class StudentDialog(QDialog):
    """Vytvoření nebo úprava studenta.

    Forma studia se nezadává ručně — odvozuje se z přípony oboru
    (``-P`` = prezenční, ``-K`` = kombinovaná). Pod polem oboru je živý
    indikátor odvozené formy.
    """

    def __init__(
        self,
        service: ThesisService,
        student: Student | None = None,
        parent=None,
        *,
        persist: bool = True,
    ) -> None:
        super().__init__(parent)
        self.service = service
        self.student = student or Student(first_name="", last_name="")
        # persist=False → dialog jen naplní objekt ``student`` (neukládá na disk
        # ani neregistruje obor). Použito pro revizi v transakčním importu, kde
        # se zápis provádí až v dávce.
        self.persist = persist
        self.setWindowTitle("Student" if student else "Nový student")
        self.setMinimumWidth(420)

        form = QFormLayout()
        self.ed_first = QLineEdit(self.student.first_name)
        self.ed_last = QLineEdit(self.student.last_name)

        self.cb_obor = QComboBox()
        self.cb_obor.setEditable(True)
        for obor in service.list_obory():
            self.cb_obor.addItem(obor)
        if self.student.obor:
            self.cb_obor.setCurrentText(self.student.obor)
        else:
            self.cb_obor.setCurrentText("")

        self.lbl_form_derived = QLabel("")
        self.lbl_form_derived.setStyleSheet("color: #888; font-size: 11px;")
        self.cb_obor.currentTextChanged.connect(self._update_form_label)
        self.cb_obor.editTextChanged.connect(self._update_form_label)

        self.ed_university_id = QLineEdit(self.student.university_id or "")
        self.ed_university_id.setPlaceholderText("např. A24390")
        self.ed_email = QLineEdit(self.student.email or "")
        self.ed_phone = QLineEdit(self.student.phone or "")
        self.ed_note = QPlainTextEdit(self.student.note or "")
        self.ed_note.setMaximumHeight(80)

        form.addRow("Jméno", self.ed_first)
        form.addRow("Příjmení", self.ed_last)
        form.addRow("Obor", self.cb_obor)
        form.addRow("Forma studia", self.lbl_form_derived)
        form.addRow("Osobní číslo (UTB)", self.ed_university_id)
        form.addRow("Email", self.ed_email)
        form.addRow("Telefon", self.ed_phone)
        form.addRow("Poznámka", self.ed_note)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

        self._update_form_label(self.cb_obor.currentText())

    def _update_form_label(self, text: str) -> None:
        form = derive_form_from_obor(text)
        if form is None:
            if text.strip():
                self.lbl_form_derived.setText("(přípona -P/-K v oboru nenalezena)")
                self.lbl_form_derived.setStyleSheet("color: #c62828; font-size: 11px;")
            else:
                self.lbl_form_derived.setText("(odvodí se z přípony oboru: -P / -K)")
                self.lbl_form_derived.setStyleSheet("color: #888; font-size: 11px;")
        else:
            self.lbl_form_derived.setText(f"✓ {form.label}")
            self.lbl_form_derived.setStyleSheet("color: #2e7d32; font-size: 11px;")

    def _on_accept(self) -> None:
        self.student.first_name = self.ed_first.text().strip()
        self.student.last_name = self.ed_last.text().strip()
        obor = self.cb_obor.currentText().strip()
        self.student.obor = obor
        self.student.university_id = self.ed_university_id.text().strip() or None
        self.student.email = self.ed_email.text().strip() or None
        self.student.phone = self.ed_phone.text().strip() or None
        self.student.note = self.ed_note.toPlainText().strip() or None
        if self.persist:
            if obor:
                self.service.add_obor(obor)
            self.service.upsert_student(self.student)
        self.accept()
