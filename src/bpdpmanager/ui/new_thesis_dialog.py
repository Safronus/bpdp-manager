"""Dialog „Nová práce" — jediné místo pro založení vedené práce.

Nahrazuje dřívější „Nová práce" / „🌱 Zájemce" / „🕘 Minulá práce". Stav se
volí v dialogu (výchozí podle záložky), nabídka roků se řídí stavem. Student
se vybírá dialogem s osobním číslem, oborem a dosavadními pracemi. Pravidla
(roky, výchozí hodnoty, upozornění, validace) jsou v ``services.new_thesis``.
"""

from __future__ import annotations

from html import escape

from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from ..i18n import tr
from ..models import Thesis
from ..models.enums import ThesisStatus, ThesisType
from ..services import ThesisService
from ..services.new_thesis import (
    CREATABLE_STATUSES,
    NewThesisError,
    TabKind,
    WarningKind,
    create_thesis,
    default_year,
    student_warnings,
    tab_default_status,
    year_choices,
)
from .student_picker_dialog import StudentPickerDialog


class NewThesisDialog(QDialog):
    """Založení práce. Po přijetí je uložená práce v ``thesis``."""

    def __init__(
        self,
        service: ThesisService,
        parent: QWidget | None = None,
        *,
        tab: TabKind = TabKind.OTHER,
    ) -> None:
        super().__init__(parent)
        self.service = service
        self.thesis: Thesis | None = None
        self.student_id: str | None = None
        self.setWindowTitle(tr("Nová práce"))
        self.setMinimumWidth(560)

        # Typ
        self.rb_bp = QRadioButton(tr("Bakalářská práce"))
        self.rb_dp = QRadioButton(tr("Diplomová práce"))
        self.rb_bp.setChecked(True)
        self._type_group = QButtonGroup(self)
        self._type_group.addButton(self.rb_bp)
        self._type_group.addButton(self.rb_dp)
        type_row = QHBoxLayout()
        type_row.setContentsMargins(0, 0, 0, 0)
        type_row.addWidget(self.rb_bp)
        type_row.addWidget(self.rb_dp)
        type_row.addStretch(1)
        type_widget = QWidget()
        type_widget.setLayout(type_row)

        # Stav + rok
        self.cb_status = QComboBox()
        for s in CREATABLE_STATUSES:
            self.cb_status.addItem(s.label, s.value)
        self.cb_year = QComboBox()
        self.cb_year.setMinimumContentsLength(9)
        # Ručně zvolený rok se při změně stavu zachová (je-li v nabídce);
        # jinak se použije výchozí rok nového stavu.
        self._year_touched = False
        self.cb_year.activated.connect(self._on_year_activated)

        # Student — výběrový dialog
        self.ed_student = QLineEdit()
        self.ed_student.setReadOnly(True)
        self.ed_student.setPlaceholderText(tr("(bez studenta)"))
        self.btn_pick = QPushButton(tr("Vybrat…"))
        self.btn_pick.clicked.connect(self._pick_student)
        self.btn_clear = QPushButton("✕")
        self.btn_clear.setFixedWidth(28)
        self.btn_clear.setToolTip(tr("Bez studenta"))
        self.btn_clear.clicked.connect(lambda: self._set_student(None))
        student_row = QHBoxLayout()
        student_row.setContentsMargins(0, 0, 0, 0)
        student_row.addWidget(self.ed_student, stretch=1)
        student_row.addWidget(self.btn_pick)
        student_row.addWidget(self.btn_clear)
        student_widget = QWidget()
        student_widget.setLayout(student_row)

        self.cb_obor = QComboBox()
        self.cb_obor.setEditable(True)
        self.cb_obor.addItem("")
        for o in self.service.list_obor_objects():
            self.cb_obor.addItem(o.name)
        self.cb_obor.lineEdit().setPlaceholderText(tr("Obor (nepovinné)"))

        self.lbl_warning = QLabel()
        self.lbl_warning.setWordWrap(True)
        self.lbl_warning.setStyleSheet("color:#b26a00;")
        self.lbl_warning.linkActivated.connect(lambda _l: self._pick_student())
        self.lbl_warning.hide()

        self.ed_title = QLineEdit()
        self.ed_anot = QPlainTextEdit()
        self.ed_anot.setMaximumHeight(110)

        form = QFormLayout()
        # macOS má výchozí „pole v přirozené šířce" → úzká pole a ořezaný student.
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        form.addRow(tr("Typ"), type_widget)
        form.addRow(tr("Stav"), self.cb_status)
        form.addRow(tr("Akademický rok"), self.cb_year)
        form.addRow(tr("Student"), student_widget)
        form.addRow("", self.lbl_warning)
        form.addRow(tr("Obor"), self.cb_obor)
        form.addRow(tr("Název"), self.ed_title)
        form.addRow(tr("Anotace"), self.ed_anot)

        hint = QLabel(tr(
            "Nepovinné — co nevyplníš, zůstane prázdné. Obor se ukládá ke "
            "zvolenému studentovi (jen pokud je zvolen)."
        ))
        hint.setStyleSheet("color:#888;")
        hint.setWordWrap(True)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(hint)
        layout.addWidget(buttons)

        self.cb_status.currentIndexChanged.connect(lambda _i: self._on_status_changed())
        self._type_group.buttonToggled.connect(lambda *_a: self._update_warnings())

        self._set_status(tab_default_status(tab))

    # --- hodnoty -------------------------------------------------------------

    @property
    def status(self) -> ThesisStatus:
        return ThesisStatus(self.cb_status.currentData())

    @property
    def thesis_type(self) -> ThesisType:
        return ThesisType.DP if self.rb_dp.isChecked() else ThesisType.BP

    def _set_status(self, status: ThesisStatus) -> None:
        idx = self.cb_status.findData(status.value)
        if idx == self.cb_status.currentIndex():
            self._on_status_changed()      # signál by nepřišel
        else:
            self.cb_status.setCurrentIndex(idx)

    def _on_year_activated(self, _index: int) -> None:
        self._year_touched = True

    def _on_status_changed(self) -> None:
        """Nabídka roků podle stavu; ručně zvolený rok zůstane, pokud v ní je."""
        keep = self.cb_year.currentText()
        choices = year_choices(self.status)
        self.cb_year.blockSignals(True)
        self.cb_year.clear()
        self.cb_year.addItems(choices)
        self.cb_year.blockSignals(False)
        if self._year_touched and keep in choices:
            target = keep
        else:
            target = default_year(self.status)
        self.cb_year.setCurrentIndex(max(0, self.cb_year.findText(target)))

    # --- student -------------------------------------------------------------

    def _pick_student(self) -> None:
        dlg = StudentPickerDialog(self.service, parent=self, current_id=self.student_id)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._set_student(dlg.selected_student_id)

    def _set_student(self, student_id: str | None) -> None:
        st = self.service.get_student(student_id) if student_id else None
        self.student_id = st.id if st else None
        if st is None:
            self.ed_student.clear()
        else:
            extra = ", ".join(x for x in (st.university_id, st.obor) if x)
            self.ed_student.setText(f"{st.full_name} ({extra})" if extra else st.full_name)
            self.cb_obor.setCurrentText(st.obor or "")
        self._update_warnings()

    def _update_warnings(self) -> None:
        lines: list[str] = []
        for w in student_warnings(self.service, self.student_id, self.thesis_type):
            works = ", ".join(
                f"{t.type.value} {t.academic_year} {t.status.label}" for t in w.theses
            )
            if w.kind == WarningKind.OPEN_SAME_TYPE:
                lines.append(escape(
                    tr("⚠ Student už má neukončenou práci stejného typu: {works}.")
                    .format(works=works)
                ))
            elif w.kind == WarningKind.BP_RECORD_FOR_DP:
                lines.append(
                    escape(tr("⚠ Tento záznam studenta má BP ({works}) — pro DP bývá "
                              "ve STAGu nové osobní číslo.").format(works=works))
                    + " <a href='pick'>"
                    + escape(tr("Vybrat jiný záznam / Nový záznam z vybraného…"))
                    + "</a>"
                )
        self.lbl_warning.setText("<br>".join(lines))
        self.lbl_warning.setVisible(bool(lines))

    # --- uložení -------------------------------------------------------------

    def _on_accept(self) -> None:
        try:
            self.thesis = create_thesis(
                self.service,
                thesis_type=self.thesis_type,
                status=self.status,
                academic_year=self.cb_year.currentText(),
                student_id=self.student_id,
                obor=self.cb_obor.currentText(),
                title=self.ed_title.text(),
                annotation=self.ed_anot.toPlainText(),
            )
        except NewThesisError as exc:
            QMessageBox.warning(self, tr("Nová práce"), str(exc))
            return
        self.accept()
