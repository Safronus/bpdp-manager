from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QPlainTextEdit,
    QVBoxLayout,
)

from ..models import Student
from ..models.enums import StudyForm
from ..services import ThesisService


class StudentDialog(QDialog):
    """Vytvoření nebo úprava studenta."""

    def __init__(self, service: ThesisService, student: Student | None = None, parent=None) -> None:
        super().__init__(parent)
        self.service = service
        self.student = student or Student(first_name="", last_name="")
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

        self.cb_form = QComboBox()
        self.cb_form.addItem("— neuvedeno —", None)
        for f in StudyForm:
            self.cb_form.addItem(f.label, f.value)
        if self.student.form:
            idx = self.cb_form.findData(self.student.form.value)
            if idx >= 0:
                self.cb_form.setCurrentIndex(idx)

        self.ed_university_id = QLineEdit(self.student.university_id or "")
        self.ed_university_id.setPlaceholderText("např. A24390")
        self.ed_email = QLineEdit(self.student.email or "")
        self.ed_phone = QLineEdit(self.student.phone or "")
        self.ed_note = QPlainTextEdit(self.student.note or "")
        self.ed_note.setMaximumHeight(80)

        form.addRow("Jméno", self.ed_first)
        form.addRow("Příjmení", self.ed_last)
        form.addRow("Obor", self.cb_obor)
        form.addRow("Forma", self.cb_form)
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

    def _on_accept(self) -> None:
        self.student.first_name = self.ed_first.text().strip()
        self.student.last_name = self.ed_last.text().strip()
        obor = self.cb_obor.currentText().strip()
        self.student.obor = obor
        if obor:
            self.service.add_obor(obor)
        form_value = self.cb_form.currentData()
        self.student.form = StudyForm(form_value) if form_value else None
        self.student.university_id = self.ed_university_id.text().strip() or None
        self.student.email = self.ed_email.text().strip() or None
        self.student.phone = self.ed_phone.text().strip() or None
        self.student.note = self.ed_note.toPlainText().strip() or None
        self.service.upsert_student(self.student)
        self.accept()
