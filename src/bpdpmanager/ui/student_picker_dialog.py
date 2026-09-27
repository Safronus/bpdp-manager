"""Výběr studenta z tabulky s podrobnostmi.

Náhrada dlouhého comboboxu: hledání bez diakritiky (jméno, os. číslo, obor,
e-mail), tabulka s osobním číslem, oborem a dosavadními pracemi a panel
s detailem. Záznamy téže osoby (BP a DP mají různá osobní čísla) jsou tak
rozlišitelné. Umí založit nového studenta i nový záznam z vybraného (BP → DP).
"""

from __future__ import annotations

from html import escape

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from ..i18n import tr
from ..services import ThesisService
from ..services.student_lookup import (
    StudentSummary,
    filter_summaries,
    followup_student,
    same_name_count,
    student_summaries,
)
from .student_dialog import StudentDialog

_ID_ROLE = Qt.ItemDataRole.UserRole


class StudentPickerDialog(QDialog):
    """Dialog výběru studenta. Výsledek v ``selected_student_id``.

    ``allow_none`` přidá tlačítko „Bez studenta" (výsledek ``None`` + accept).
    ``changed`` je True, když dialog založil nového studenta (volající si
    má obnovit své seznamy).
    """

    COLUMNS = ("Jméno", "Os. číslo", "Obor", "Forma", "E-mail", "Práce")

    def __init__(
        self,
        service: ThesisService,
        parent: QWidget | None = None,
        *,
        current_id: str | None = None,
        allow_none: bool = True,
    ) -> None:
        super().__init__(parent)
        self.service = service
        self.selected_student_id: str | None = current_id
        self.changed = False
        self._summaries: list[StudentSummary] = []
        self.setWindowTitle(tr("Výběr studenta"))
        self.resize(1000, 560)

        self.ed_search = QLineEdit()
        self.ed_search.setPlaceholderText(
            tr("Hledat jméno, osobní číslo, obor nebo e-mail (bez diakritiky)…")
        )
        self.ed_search.setClearButtonEnabled(True)
        self.ed_search.textChanged.connect(lambda _t: self._fill_table())

        self.table = QTableWidget(0, len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels([tr(c) for c in self.COLUMNS])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()
        for col in range(len(self.COLUMNS) - 1):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(len(self.COLUMNS) - 1, QHeaderView.ResizeMode.Stretch)
        # Bez výchozího třídění — pořadí ze služby (příjmení, jméno, os. číslo);
        # kliknutím na hlavičku si uživatel seřadí po svém.
        header.setSortIndicator(-1, Qt.SortOrder.AscendingOrder)
        self.table.itemSelectionChanged.connect(self._on_selection)
        self.table.itemDoubleClicked.connect(lambda _i: self._accept_selected())

        self.detail = QTextBrowser()
        self.detail.setOpenLinks(False)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.table)
        splitter.addWidget(self.detail)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([700, 300])

        self.lbl_count = QLabel()
        self.lbl_count.setStyleSheet("color:#888;")

        self.btn_new = QPushButton(tr("+ Nový student"))
        self.btn_new.clicked.connect(self._new_student)
        self.btn_followup = QPushButton(tr("⤴ Nový záznam z vybraného (BP → DP)"))
        self.btn_followup.setToolTip(
            tr("Založí nový záznam téže osoby (jméno, e-mail, telefon) — pro "
               "navazující studium s jiným osobním číslem a oborem.")
        )
        self.btn_followup.clicked.connect(self._new_followup)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.btn_ok = self.buttons.button(QDialogButtonBox.StandardButton.Ok)
        self.btn_ok.setText(tr("Vybrat"))
        self.btn_ok.setDefault(True)
        self.buttons.accepted.connect(self._accept_selected)
        self.buttons.rejected.connect(self.reject)
        self.btn_none: QPushButton | None = None
        if allow_none:
            self.btn_none = self.buttons.addButton(
                tr("Bez studenta"), QDialogButtonBox.ButtonRole.ResetRole
            )
            self.btn_none.clicked.connect(self._accept_none)

        actions = QHBoxLayout()
        actions.addWidget(self.btn_new)
        actions.addWidget(self.btn_followup)
        actions.addStretch(1)
        actions.addWidget(self.lbl_count)

        layout = QVBoxLayout(self)
        layout.addWidget(self.ed_search)
        layout.addWidget(splitter, stretch=1)
        layout.addLayout(actions)
        layout.addWidget(self.buttons)

        self._reload(select_id=current_id)
        self.ed_search.setFocus()

    # --- data ----------------------------------------------------------------

    def _reload(self, select_id: str | None = None) -> None:
        self._summaries = student_summaries(self.service)
        self._fill_table(select_id=select_id)

    def _fill_table(self, select_id: str | None = None) -> None:
        keep = select_id or self._current_id()
        rows = filter_summaries(self._summaries, self.ed_search.text())
        bold = QFont()
        bold.setBold(True)
        dup_tip = tr("Stejné jméno má víc záznamů — rozliš podle osobního čísla, "
                     "oboru a prací.")

        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(rows))
        for r, summ in enumerate(rows):
            st = summ.student
            values = (
                st.full_name,
                st.university_id or "",
                st.obor,
                st.form.label if st.form else "",
                st.email or "",
                summ.theses_label or tr("(žádná práce)"),
            )
            duplicate = same_name_count(self._summaries, st) > 1
            for c, val in enumerate(values):
                item = QTableWidgetItem(val)
                item.setData(_ID_ROLE, st.id)
                if c == 0 and duplicate:
                    item.setFont(bold)
                    item.setToolTip(dup_tip)
                elif c == len(values) - 1:
                    item.setToolTip(val)
                self.table.setItem(r, c, item)
        self.table.setSortingEnabled(True)

        self.lbl_count.setText(
            tr("Zobrazeno {n} z {total}").format(n=len(rows), total=len(self._summaries))
        )
        if not self._select_row_by_id(keep):
            self._select_first_row()
        self._on_selection()

    def _select_row_by_id(self, student_id: str | None) -> bool:
        if not student_id:
            return False
        for r in range(self.table.rowCount()):
            item = self.table.item(r, 0)
            if item is not None and item.data(_ID_ROLE) == student_id:
                self.table.selectRow(r)
                self.table.scrollToItem(item)
                return True
        return False

    def _select_first_row(self) -> bool:
        if self.table.rowCount() == 0:
            self.table.clearSelection()
            return False
        self.table.selectRow(0)
        return True

    def _current_id(self) -> str | None:
        rows = self.table.selectionModel().selectedRows() if self.table.selectionModel() else []
        if not rows:
            return None
        item = self.table.item(rows[0].row(), 0)
        return item.data(_ID_ROLE) if item is not None else None

    def _summary(self, student_id: str | None) -> StudentSummary | None:
        return next((s for s in self._summaries if s.student.id == student_id), None)

    # --- detail --------------------------------------------------------------

    def _on_selection(self) -> None:
        summ = self._summary(self._current_id())
        self.btn_ok.setEnabled(summ is not None)
        self.btn_followup.setEnabled(summ is not None)
        self.detail.setHtml(self._detail_html(summ) if summ else
                            f"<p style='color:#888'>{escape(tr('Nikdo nevybrán.'))}</p>")

    def _detail_html(self, summ: StudentSummary) -> str:
        st = summ.student
        rows = [
            (tr("Osobní číslo"), st.university_id or "—"),
            (tr("Obor"), st.obor or "—"),
            (tr("Forma studia"), st.form.label if st.form else "—"),
            (tr("E-mail"), st.email or "—"),
            (tr("Telefon"), st.phone or "—"),
        ]
        parts = [f"<h3>{escape(st.full_name)}</h3><table>"]
        parts += [
            f"<tr><td style='color:#888;padding-right:8px'>{escape(k)}</td>"
            f"<td>{escape(v)}</td></tr>" for k, v in rows
        ]
        parts.append("</table>")
        dup = same_name_count(self._summaries, st)
        if dup > 1:
            parts.append(
                "<p style='color:#b26a00'>⚠ "
                + escape(tr("Stejné jméno má {n} záznamy v evidenci.").format(n=dup))
                + "</p>"
            )
        parts.append(f"<p><b>{escape(tr('Práce'))}</b></p>")
        if summ.theses:
            parts.append("<ul>")
            for t in summ.theses:
                title = t.title_cs.strip()
                line = f"{t.type.value} {t.academic_year} — {t.status.label}"
                parts.append(
                    f"<li>{escape(line)}"
                    + (f"<br><i>{escape(title)}</i>" if title else "")
                    + "</li>"
                )
            parts.append("</ul>")
        else:
            parts.append(f"<p style='color:#888'>{escape(tr('(žádná práce)'))}</p>")
        if st.note:
            parts.append(f"<p><b>{escape(tr('Poznámka'))}</b><br>"
                         f"{escape(st.note).replace(chr(10), '<br>')}</p>")
        return "".join(parts)

    # --- akce ----------------------------------------------------------------

    def _new_student(self) -> None:
        dlg = StudentDialog(self.service, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._after_create(dlg.student.id)

    def _new_followup(self) -> None:
        summ = self._summary(self._current_id())
        if summ is None:
            return
        dlg = StudentDialog(
            self.service, followup_student(summ.student), parent=self,
            title=tr("Nový záznam studenta (navazující studium)"),
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._after_create(dlg.student.id)

    def _after_create(self, student_id: str) -> None:
        self.changed = True
        self.ed_search.blockSignals(True)
        self.ed_search.clear()          # nový záznam musí být vidět
        self.ed_search.blockSignals(False)
        self._reload(select_id=student_id)

    def _accept_selected(self) -> None:
        sid = self._current_id()
        if sid is None:
            return
        self.selected_student_id = sid
        self.accept()

    def _accept_none(self) -> None:
        self.selected_student_id = None
        self.accept()
