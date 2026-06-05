"""Detail panel pro jeden oponentský posudek.

Liší se od ``ThesisDetail`` zjednodušeným obsahem:
- žádné stavy / přechody / autosave debounce na bázi 1.5 s (jen explicitní)
- žádná anotace, literatura, plagiátorství, poznámky
- inline údaje o studentovi + vedoucím (ne přes Student/Opponent entity)
- známky vedoucího + oponenta
- dokumenty: plný text, posudek vedoucího, posudek oponenta
"""

from __future__ import annotations

import html
from datetime import datetime

from PySide6.QtCore import QTimer, QUrl, Signal
from PySide6.QtGui import QCursor, QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QTabWidget,
    QTextBrowser,
    QToolTip,
    QVBoxLayout,
    QWidget,
)

from ..models import OpposingThesis
from ..models.enums import ThesisType
from ..services import ThesisService
from .supervisor_dialog import SupervisorDialog
from .thesis_detail import (
    YEAR_MODE_ALL,
    _academic_year_choices,
    _format_numbered,
    _setup_searchable_combo,
    _split_items,
)
from .widgets import DocumentsWidget

AUTOSAVE_DEBOUNCE_MS = 1500


def _make_form() -> QFormLayout:
    f = QFormLayout()
    f.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
    f.setHorizontalSpacing(12)
    f.setVerticalSpacing(8)
    return f


class OpposingDetail(QWidget):
    """Editor oponentského posudku — vlastní záložky Souhrn / Detail / Dokumenty."""

    saved = Signal(str)  # opposing thesis id
    deleted = Signal(str)
    generate_review_requested = Signal(str)  # opposing thesis id

    def __init__(self, service: ThesisService, parent=None) -> None:
        super().__init__(parent)
        self.service = service
        self.op: OpposingThesis | None = None
        self._loading = False
        self._dirty = False
        self._last_save_at: datetime | None = None

        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(AUTOSAVE_DEBOUNCE_MS)
        self._debounce.timeout.connect(self._autosave)

        self._build_ui()
        self._show_empty()

    # --- konstrukce UI -------------------------------------------------------

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self.placeholder = QLabel(
            "Vyber posudek ze seznamu vlevo, nebo přidej nový."
        )
        self.placeholder.setStyleSheet("color: #888; padding: 24px;")
        outer.addWidget(self.placeholder)

        self.container = QWidget()
        outer.addWidget(self.container)

        layout = QVBoxLayout(self.container)

        # Hlavička
        header = QHBoxLayout()
        self.lbl_title = QLabel("")
        self.lbl_title.setStyleSheet("font-size: 16px; font-weight: bold;")
        header.addWidget(self.lbl_title, stretch=1)
        self.lbl_save_state = QLabel("")
        self.lbl_save_state.setStyleSheet("color:#888;font-size:11px;")
        header.addWidget(self.lbl_save_state)
        self.btn_generate_review = QPushButton("📝 Napsat posudek…")
        self.btn_generate_review.setToolTip(
            "Vyplnit oponentský posudek z šablony (kritéria, body, známka) "
            "a připojit jako přílohu."
        )
        self.btn_generate_review.clicked.connect(self._generate_review)
        header.addWidget(self.btn_generate_review)
        self.btn_delete = QPushButton("Smazat")
        self.btn_delete.clicked.connect(self._delete)
        header.addWidget(self.btn_delete)
        layout.addLayout(header)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_summary_tab(), "📋 Souhrn")
        self.tabs.addTab(self._build_detail_tab(), "📝 Detail")
        self.tabs.addTab(self._build_documents_tab(), "📎 Dokumenty")
        self.tabs.currentChanged.connect(self._on_tab_changed)
        layout.addWidget(self.tabs, stretch=1)

        # Save button
        save_row = QHBoxLayout()
        save_row.addStretch()
        self.btn_save = QPushButton("Uložit změny")
        self.btn_save.setDefault(True)
        self.btn_save.clicked.connect(self._save_now)
        save_row.addWidget(self.btn_save)
        layout.addLayout(save_row)

        self._connect_dirty_signals()

    def _build_summary_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        self.summary_view = QTextBrowser()
        self.summary_view.setOpenExternalLinks(False)
        self.summary_view.setOpenLinks(False)
        self.summary_view.anchorClicked.connect(self._on_summary_anchor_clicked)
        self.summary_view.setStyleSheet(
            "QTextBrowser { padding: 12px; font-family: -apple-system, sans-serif; }"
        )
        layout.addWidget(self.summary_view)
        return w

    def _build_detail_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        inner = QWidget()
        v = QVBoxLayout(inner)
        v.setContentsMargins(8, 8, 8, 8)
        v.setSpacing(12)

        # Sekce: Základní info (1. řádek: Typ + Rok ; 2. řádek: STAG ; 3. řádek student ; 4. řádek vedoucí)
        box_basic = QGroupBox("Základní info")
        bl = QVBoxLayout(box_basic)
        bl.setContentsMargins(8, 12, 8, 8)

        # row1: Typ + Rok
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Typ:"))
        self.rb_bp = QRadioButton("BP")
        self.rb_dp = QRadioButton("DP")
        self._type_group = QButtonGroup(self)
        self._type_group.addButton(self.rb_bp, 0)
        self._type_group.addButton(self.rb_dp, 1)
        self.rb_bp.setChecked(True)
        row1.addWidget(self.rb_bp)
        row1.addWidget(self.rb_dp)
        row1.addSpacing(16)
        row1.addWidget(QLabel("Rok:"))
        self.cb_year = QComboBox()
        self.cb_year.setEditable(True)
        for y in _academic_year_choices(YEAR_MODE_ALL):
            self.cb_year.addItem(y)
        self.cb_year.setMinimumContentsLength(9)
        row1.addWidget(self.cb_year)
        row1.addStretch()
        bl.addLayout(row1)

        # row2: STAG
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("STAG:"))
        self.ed_stag_url = QLineEdit()
        self.ed_stag_url.setPlaceholderText("odkaz na práci v IS/STAG (volitelné)")
        row2.addWidget(self.ed_stag_url, stretch=1)
        bl.addLayout(row2)

        v.addWidget(box_basic)

        # Sekce: Student
        box_student = QGroupBox("Student")
        sl = QHBoxLayout(box_student)
        sl.setContentsMargins(8, 12, 8, 8)
        self.ed_student_first = QLineEdit()
        self.ed_student_first.setPlaceholderText("Jméno")
        self.ed_student_last = QLineEdit()
        self.ed_student_last.setPlaceholderText("Příjmení")
        self.ed_student_obor = QLineEdit()
        self.ed_student_obor.setPlaceholderText("Obor (např. NSWI-K)")
        self.ed_student_obor.setMaximumWidth(160)
        self.ed_student_uni_id = QLineEdit()
        self.ed_student_uni_id.setPlaceholderText("Os. č.")
        self.ed_student_uni_id.setMaximumWidth(120)
        sl.addWidget(self.ed_student_first, stretch=2)
        sl.addWidget(self.ed_student_last, stretch=2)
        sl.addWidget(self.ed_student_obor, stretch=1)
        sl.addWidget(self.ed_student_uni_id, stretch=0)
        v.addWidget(box_student)

        # Sekce: Vedoucí (combo se searchable našeptáváním z registru)
        box_sup = QGroupBox("Vedoucí")
        spl = QHBoxLayout(box_sup)
        spl.setContentsMargins(8, 12, 8, 8)
        self.cb_sup_name = QComboBox()
        _setup_searchable_combo(self.cb_sup_name)
        if self.cb_sup_name.lineEdit() is not None:
            self.cb_sup_name.lineEdit().setPlaceholderText(
                "Jméno (např. doc. Ing. Petr Novák, Ph.D.)"
            )
        self.cb_sup_name.activated.connect(self._on_supervisor_picked)
        self.btn_new_supervisor = QPushButton("+")
        self.btn_new_supervisor.setFixedWidth(28)
        self.btn_new_supervisor.setToolTip("Nový vedoucí v registru")
        self.btn_new_supervisor.clicked.connect(self._new_supervisor)
        self.ed_sup_email = QLineEdit()
        self.ed_sup_email.setPlaceholderText("email@utb.cz")
        self.ed_sup_email.setMaximumWidth(280)
        spl.addWidget(self.cb_sup_name, stretch=2)
        spl.addWidget(self.btn_new_supervisor)
        spl.addSpacing(8)
        spl.addWidget(self.ed_sup_email, stretch=1)
        v.addWidget(box_sup)

        # Sekce: Téma + body zadání + známky
        box_topic = QGroupBox("Téma a body zadání")
        tl = QVBoxLayout(box_topic)
        tl.setContentsMargins(8, 12, 8, 8)
        # Název
        title_form = _make_form()
        self.ed_title_cs = QLineEdit()
        title_form.addRow("Název (CZ)", self.ed_title_cs)
        tl.addLayout(title_form)
        # Body zadání
        lbl_obj = QLabel(
            "Body zadání — každý bod na nové řádce, číslování se přidá automaticky v Souhrnu."
        )
        lbl_obj.setContentsMargins(8, 4, 8, 0)
        tl.addWidget(lbl_obj)
        self.ed_objectives = QPlainTextEdit()
        self.ed_objectives.setMinimumHeight(120)
        self.ed_objectives.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        tl.addWidget(self.ed_objectives, stretch=1)
        v.addWidget(box_topic, stretch=1)

        # Sekce: Známky
        box_grades = QGroupBox("Známky")
        gl = QHBoxLayout(box_grades)
        gl.setContentsMargins(8, 12, 8, 8)
        gl.addWidget(QLabel("Vedoucí:"))
        self.cb_grade_sup = self._make_grade_combo()
        gl.addWidget(self.cb_grade_sup)
        gl.addSpacing(20)
        gl.addWidget(QLabel("Oponent (moje):"))
        self.cb_grade_opp = self._make_grade_combo()
        gl.addWidget(self.cb_grade_opp)
        gl.addStretch()
        v.addWidget(box_grades)

        scroll.setWidget(inner)
        return scroll

    def _refresh_supervisors_combo(self) -> None:
        """Naplní combo aktuálním registrem vedoucích (zachová text v editLine)."""
        prev_text = self.cb_sup_name.currentText() if self.cb_sup_name.isEditable() else ""
        was_loading = self._loading
        self._loading = True
        try:
            self.cb_sup_name.clear()
            for sup in self.service.list_supervisors():
                # Jméno vč. titulů — propíše se do supervisor_name (i do posudku).
                self.cb_sup_name.addItem(sup.display_name, sup.id)
            # Obnov text, kdyby byl něčím vyplněn (např. ručně zadané jméno)
            if prev_text:
                idx = self.cb_sup_name.findText(prev_text)
                if idx >= 0:
                    self.cb_sup_name.setCurrentIndex(idx)
                else:
                    if self.cb_sup_name.lineEdit() is not None:
                        self.cb_sup_name.lineEdit().setText(prev_text)
            else:
                self.cb_sup_name.setCurrentIndex(-1)
        finally:
            self._loading = was_loading

    def _on_supervisor_picked(self, index: int) -> None:
        """Když uživatel vybere vedoucího ze suggestion / dropdownu, auto-vyplň email."""
        if index < 0:
            return
        sup_id = self.cb_sup_name.itemData(index)
        if not sup_id:
            return
        sup = self.service.get_supervisor(sup_id)
        if sup is None:
            return
        # Pokud má email a uživatel zatím nemá nic / má jiný → auto-fill
        if sup.email and self.ed_sup_email.text().strip() != sup.email:
            self.ed_sup_email.setText(sup.email)

    def _new_supervisor(self) -> None:
        """Otevři dialog pro vytvoření nového vedoucího + ihned ho vyber."""
        dlg = SupervisorDialog(self.service, parent=self)
        if not dlg.exec():
            return
        self._refresh_supervisors_combo()
        # vyber nově vytvořeného
        idx = self.cb_sup_name.findData(dlg.supervisor.id)
        if idx >= 0:
            self.cb_sup_name.setCurrentIndex(idx)
            self._on_supervisor_picked(idx)

    @staticmethod
    def _make_grade_combo() -> QComboBox:
        cb = QComboBox()
        cb.setEditable(True)
        cb.addItem("")  # nezvoleno
        for g in ("A", "B", "C", "D", "E", "F", "1", "2", "3", "4"):
            cb.addItem(g)
        cb.setMaximumWidth(110)
        return cb

    def _build_documents_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(8, 8, 8, 8)

        layout.addWidget(QLabel(
            "Dokumenty k oponentskému posudku (plný text práce, posudek vedoucího, "
            "tvůj posudek oponenta, příp. další):"
        ))

        # Stejný agregovaný widget jako u vedených prací (strom podle typu,
        # verzování, otevřít / Finder / odebrat, indikace chybějících…).
        self.documents_widget = DocumentsWidget(self.service)
        self.documents_widget.changed.connect(self._on_documents_changed)
        layout.addWidget(self.documents_widget, stretch=1)
        return w

    def _on_documents_changed(self) -> None:
        # Dokumenty se mění přímo přes službu — jen přenačti detail/souhrn.
        if self.op is not None:
            self.op = self.service.get_opposing_thesis(self.op.id)
            self._refresh_summary()

    # --- pomocné: zobrazení -------------------------------------------------

    def _show_empty(self) -> None:
        self.placeholder.setVisible(True)
        self.container.setVisible(False)

    def _show_form(self) -> None:
        self.placeholder.setVisible(False)
        self.container.setVisible(True)

    def set_opposing(self, op: OpposingThesis | None) -> None:
        # flush rozdělané z předchozího posudku
        if self._dirty and self.op is not None:
            self._autosave()

        self.op = op
        if op is None:
            self.documents_widget.set_opposing_id(None)
            self._show_empty()
            return
        self._show_form()

        self._loading = True
        try:
            if op.type == ThesisType.BP:
                self.rb_bp.setChecked(True)
            else:
                self.rb_dp.setChecked(True)
            self.cb_year.setCurrentText(op.academic_year or "")
            self.ed_stag_url.setText(op.stag_url or "")

            self.ed_student_first.setText(op.student_first_name or "")
            self.ed_student_last.setText(op.student_last_name or "")
            self.ed_student_obor.setText(op.student_obor or "")
            self.ed_student_uni_id.setText(op.student_university_id or "")

            self._refresh_supervisors_combo()
            # Nastav text vedoucího — pokud sedí s registrem, vybere se daná
            # položka (auto-fill emailu pro pohodlí), jinak zůstane jen v textu.
            if op.supervisor_name:
                idx = self.cb_sup_name.findText(op.supervisor_name)
                if idx >= 0:
                    self.cb_sup_name.setCurrentIndex(idx)
                else:
                    if self.cb_sup_name.lineEdit() is not None:
                        self.cb_sup_name.lineEdit().setText(op.supervisor_name)
            else:
                self.cb_sup_name.setCurrentIndex(-1)
                if self.cb_sup_name.lineEdit() is not None:
                    self.cb_sup_name.lineEdit().clear()
            self.ed_sup_email.setText(op.supervisor_email or "")

            self.ed_title_cs.setText(op.title_cs or "")
            self.ed_objectives.setPlainText(op.objectives or "")

            self.cb_grade_sup.setCurrentText(op.grade_supervisor or "")
            self.cb_grade_opp.setCurrentText(op.grade_opponent or "")

            self.documents_widget.set_opposing_id(op.id)
            self.lbl_title.setText(self._compose_header_label())
        finally:
            self._loading = False
        self._dirty = False
        self._debounce.stop()
        self._update_save_label(idle=True)

        # auto-switch na Souhrn
        self.tabs.setCurrentIndex(0)
        self._refresh_summary()

    # --- dirty / autosave ---------------------------------------------------

    def _connect_dirty_signals(self) -> None:
        for w in (
            self.ed_stag_url, self.ed_student_first, self.ed_student_last,
            self.ed_student_obor, self.ed_student_uni_id,
            self.ed_sup_email, self.ed_title_cs,
        ):
            w.textChanged.connect(self._mark_dirty)
        self.cb_sup_name.currentTextChanged.connect(self._mark_dirty)
        self.cb_year.currentTextChanged.connect(self._mark_dirty)
        self.cb_grade_sup.currentTextChanged.connect(self._mark_dirty)
        self.cb_grade_opp.currentTextChanged.connect(self._mark_dirty)
        self.ed_objectives.textChanged.connect(self._mark_dirty)
        self.rb_bp.toggled.connect(self._mark_dirty)
        self.rb_dp.toggled.connect(self._mark_dirty)

    def _mark_dirty(self, *_args) -> None:
        if self._loading or self.op is None:
            return
        self._dirty = True
        self._update_save_label(pending=True)
        self._debounce.start()

    def _autosave(self) -> None:
        if self.op is None or not self._dirty:
            return
        try:
            self._collect()
            self.service.upsert_opposing_thesis(self.op)
        except Exception as exc:  # noqa: BLE001
            self._update_save_label(error=str(exc))
            return
        self._dirty = False
        self._last_save_at = datetime.now()
        self._update_save_label()
        self.lbl_title.setText(self._compose_header_label())
        if self.tabs.currentIndex() == 0:
            self._refresh_summary()
        self.saved.emit(self.op.id)

    def _save_now(self) -> None:
        self._autosave()

    def _generate_review(self) -> None:
        """Klik na „📝 Napsat posudek…" → flush + emit (OpposingTab otevře dialog)."""
        if self.op is None:
            return
        # Flushni rozpracované změny, aby šablona dostala aktuální data.
        self.flush()
        self.generate_review_requested.emit(self.op.id)

    def flush(self) -> None:
        self._debounce.stop()
        if self._dirty:
            self._autosave()

    def _update_save_label(
        self, *, idle: bool = False, pending: bool = False, error: str | None = None
    ) -> None:
        if idle:
            self.lbl_save_state.setText("")
            return
        if error:
            self.lbl_save_state.setText(f"⚠ Chyba: {error}")
            self.lbl_save_state.setStyleSheet("color:#c62828;font-size:11px;")
            return
        if pending:
            self.lbl_save_state.setText("● Ukládám…")
            self.lbl_save_state.setStyleSheet("color:#ef6c00;font-size:11px;")
            return
        ts = self._last_save_at.strftime("%H:%M:%S") if self._last_save_at else ""
        self.lbl_save_state.setText(f"✓ Uloženo {ts}")
        self.lbl_save_state.setStyleSheet("color:#2e7d32;font-size:11px;")

    def _collect(self) -> None:
        assert self.op is not None
        self.op.type = ThesisType.BP if self.rb_bp.isChecked() else ThesisType.DP
        self.op.academic_year = self.cb_year.currentText().strip()
        self.op.stag_url = self.ed_stag_url.text().strip()
        self.op.student_first_name = self.ed_student_first.text().strip()
        self.op.student_last_name = self.ed_student_last.text().strip()
        self.op.student_obor = self.ed_student_obor.text().strip()
        self.op.student_university_id = self.ed_student_uni_id.text().strip()
        self.op.supervisor_name = self.cb_sup_name.currentText().strip()
        self.op.supervisor_email = self.ed_sup_email.text().strip()
        self.op.title_cs = self.ed_title_cs.text().strip()
        self.op.objectives = self.ed_objectives.toPlainText()
        self.op.grade_supervisor = self.cb_grade_sup.currentText().strip()
        self.op.grade_opponent = self.cb_grade_opp.currentText().strip()
        # attachments spravuje tabulka dokumentů, neměníme tady

    # --- header label -------------------------------------------------------

    def _compose_header_label(self) -> str:
        if self.op is None:
            return ""
        parts = []
        if self.op.type:
            parts.append(self.op.type.value)
        if self.op.title_cs:
            parts.append(self.op.title_cs)
        if self.op.student_last_name or self.op.student_first_name:
            parts.append(self.op.student_full_name)
        return " — ".join(parts) or "(bez názvu)"

    # --- delete -------------------------------------------------------------

    def _delete(self) -> None:
        if self.op is None:
            return
        confirm = QMessageBox.question(
            self,
            "Smazat posudek",
            f"Opravdu smazat oponentský posudek „{self._compose_header_label()}“?",
        )
        if confirm == QMessageBox.StandardButton.Yes:
            op_id = self.op.id
            self.service.delete_opposing_thesis(op_id)
            self.set_opposing(None)
            self.deleted.emit(op_id)

    # --- souhrn -------------------------------------------------------------

    def _on_tab_changed(self, index: int) -> None:
        if index == 0:
            self._refresh_summary()

    def _refresh_summary(self) -> None:
        if self.op is None:
            self.summary_view.setHtml(
                "<p style='color:#888;padding:24px;'>Vyber posudek vlevo.</p>"
            )
            return
        self.summary_view.setHtml(self._build_summary_html(self.op))

    @staticmethod
    def _copy_btn(field: str, tooltip: str) -> str:
        return (
            f'&nbsp;<a href="copy:{field}" title="{tooltip}" '
            'style="text-decoration:none;font-size:11pt;color:#42a5f5;">📋</a>'
        )

    def _build_reviews_summary_html(self, op: OpposingThesis) -> str:
        """Náhled uložených posudků (current verze) — body, kritéria, známka.

        Stejně jako u vedených prací: ukáže strukturovaný posudek vč. komentáře
        a navržené známky, aby byl v Souhrnu vidět i u oponentur.
        """
        e = html.escape
        reviews = [r for r in op.reviews if r.is_current]
        if not reviews:
            return ""
        reviews.sort(key=lambda r: 0 if r.role == "supervisor" else 1)

        grade_colors = {
            "A": "#2e7d32", "B": "#43a047", "C": "#fb8c00",
            "D": "#f57c00", "E": "#e65100", "F": "#c62828", "FX": "#c62828",
        }
        blocks: list[str] = []
        for r in reviews:
            role_label = (
                "🎓 Posudek vedoucího" if r.role == "supervisor"
                else "🧐 Posudek oponenta"
            )
            grade = r.suggested_grade
            grade_color = grade_colors.get(grade, "#666")
            grade_badge = (
                f'<span style="background-color:{grade_color};color:white;'
                f'padding:2px 10px;border-radius:8px;font-weight:bold;">{e(grade)}</span>'
            )
            crit_rows = ""
            for c in r.criteria:
                crit_rows += (
                    f"<tr><td style='padding:1px 10px 1px 0;color:#555;'>{e(c.label)}</td>"
                    f"<td style='padding:1px 6px;color:#888;text-align:center;'>×{c.weight:g}</td>"
                    f"<td style='padding:1px 6px;text-align:center;'><b>{c.score:g}</b>/5</td></tr>"
                )
            crit_table = (
                f"<table style='margin:4px 0 4px 12px;'>{crit_rows}</table>"
                if crit_rows else ""
            )
            comment_html = (
                e(r.overall_comment.strip()).replace("\n", "<br>")
                if r.overall_comment.strip()
                else "<span style='color:#888;font-style:italic;'>(bez komentáře)</span>"
            )
            files_bits = []
            if r.xlsx_filename:
                files_bits.append("📄 XLSX")
            if r.pdf_filename:
                files_bits.append("📕 PDF")
            files_str = (
                " · ".join(files_bits) if files_bits
                else "<span style='color:#888;'>(soubory nevygenerovány)</span>"
            )
            blocks.append(
                f"<div style='margin:6px 0 12px 0;padding:8px;"
                f"border-left:3px solid {grade_color};background:rgba(128,128,128,0.06);'>"
                f"<p style='margin:0 0 4px 0;'><b>{role_label}</b> &nbsp; "
                f"body {r.total_weighted_points:.1f}/{r.max_points:g} &nbsp; "
                f"procenta {r.percentage:.1f} % &nbsp; známka {grade_badge}</p>"
                f"{crit_table}"
                f"<p style='margin:4px 0 0 0;'><b>Hodnocení:</b> {comment_html}</p>"
                f"<p style='margin:2px 0 0 0;color:#888;font-size:11px;'>"
                f"{files_str} &nbsp;·&nbsp; {e(r.place_date)}</p>"
                f"</div>"
            )
        return "".join(blocks)

    def _build_summary_html(self, op: OpposingThesis) -> str:
        e = html.escape
        cp = self._copy_btn

        type_label = op.type.value
        year = op.academic_year or "—"
        student = op.student_full_name or "(student neuveden)"
        obor = op.student_obor or "—"
        uni_id = op.student_university_id or "—"
        sup_name = op.supervisor_name or "(vedoucí neuveden)"
        sup_email = op.supervisor_email or ""

        # Velký nadpisový pruh
        hdr_color = "#1976d2"
        header_bar = (
            f'<table width="100%" cellpadding="14" cellspacing="0" '
            f'style="background-color:{hdr_color};margin-bottom:18px;">'
            f"<tr>"
            f'<td style="color:white;font-weight:bold;font-size:16pt;'
            f"letter-spacing:1.5px;\">📋 OPONENTSKÝ POSUDEK</td>"
            f'<td align="right" style="color:white;font-size:11pt;">'
            f"Akademický rok: <b>{e(year)}</b></td>"
            f"</tr></table>"
        )

        title_line = (
            f'<h2 style="color:{hdr_color};margin:0 0 4px 0;line-height:1.35;">'
            f"{e(type_label)} — {e(op.title_cs or '(bez názvu)')}"
            f"{cp('title_cs', 'Zkopírovat název')} — "
            f"<span>{e(student)}</span> "
            f'<span style="color:#9e9e9e;">({e(obor)})</span> '
            f'<span style="color:#9e9e9e;">→ {e(uni_id)}</span>'
            f"</h2>"
        )
        sup_line = (
            f'<p style="color:#666;margin:0 0 12px 0;">'
            f"<b>Vedoucí:</b> {e(sup_name)}"
        )
        if sup_email:
            sup_line += (
                f' &nbsp;<a href="mailto:{e(sup_email)}" '
                f'style="color:#1976d2;">{e(sup_email)}</a>'
            )
        sup_line += "</p>"

        # STAG
        stag_html = ""
        if op.stag_url:
            stag_html = (
                f'<p style="margin:6px 0 14px 0;color:#666;">'
                f'<b>🔗 STAG:</b> '
                f'<a href="{e(op.stag_url)}" style="color:#1976d2;">{e(op.stag_url)}</a>'
                f"{cp('stag_url', 'Zkopírovat STAG URL')}"
                f"</p>"
            )

        # Body zadání
        items = _split_items(op.objectives)
        if items:
            items_html = "".join(
                f"<li style='margin-bottom:4px;'>{e(line)}</li>" for line in items
            )
            obj_html = f"<ol style='margin-left:1.2em;line-height:1.55;'>{items_html}</ol>"
        else:
            obj_html = "<p style='color:#888;font-style:italic;'>(bez bodů zadání)</p>"

        # Známky — velké barevné badge
        def grade_badge(label: str, value: str) -> str:
            color = self._grade_color(value)
            disp = e(value) if value else "—"
            return (
                f'<td style="padding-right:24px;">'
                f"<div style='color:#666;font-size:10pt;'>{label}</div>"
                f'<div style="background-color:{color};color:white;'
                f"font-weight:bold;font-size:18pt;padding:6px 16px;"
                f"border-radius:6px;display:inline-block;\">{disp}</div>"
                f"</td>"
            )

        grades_table = (
            "<table style='margin:12px 0;'><tr>"
            + grade_badge("Vedoucí:", op.grade_supervisor)
            + grade_badge("Oponent (moje):", op.grade_opponent)
            + "</tr></table>"
        )

        # Dokumenty
        if op.attachments:
            rows = ""
            for att in op.attachments:
                rows += (
                    f"<tr>"
                    f"<td style='padding:3px 14px 3px 0;'><b>{e(att.kind.label)}</b></td>"
                    f"<td style='padding:3px 0;'>{'📄 ' if att.is_file else '🔗 '}{e(att.label)}</td>"
                    f"</tr>"
                )
            docs_html = f"<table>{rows}</table>"
        else:
            docs_html = "<p style='color:#888;font-style:italic;'>(žádné dokumenty)</p>"

        section_style = "color:#ffa726;margin-top:18px;margin-bottom:6px;"

        # Napsaný posudek (strukturovaná data) — stejně jako u vedených prací.
        reviews_html = self._build_reviews_summary_html(op)
        reviews_section = (
            f'<h3 style="{section_style}">📝 Napsaný posudek</h3>{reviews_html}'
            if reviews_html else ""
        )

        return (
            "<html><body>"
            f"{header_bar}"
            f"{title_line}"
            f"{sup_line}"
            f"{stag_html}"
            f'<h3 style="{section_style}">Známky</h3>'
            f"{grades_table}"
            f"{reviews_section}"
            f'<h3 style="{section_style}">Body zadání'
            f"{cp('objectives', 'Zkopírovat body zadání')}</h3>"
            f"{obj_html}"
            f'<h3 style="{section_style}">📎 Dokumenty</h3>'
            f"{docs_html}"
            "</body></html>"
        )

    @staticmethod
    def _grade_color(value: str) -> str:
        v = (value or "").upper()
        if v in ("A", "1"):
            return "#2e7d32"  # zelená
        if v in ("B", "2"):
            return "#66bb6a"  # světle zelená
        if v in ("C", "3"):
            return "#fbc02d"  # žlutá
        if v in ("D",):
            return "#ef6c00"  # oranžová
        if v in ("E", "4"):
            return "#e64a19"  # tmavě oranžová
        if v in ("F",):
            return "#c62828"  # červená
        return "#9e9e9e"  # šedá (nezadáno)

    def _on_summary_anchor_clicked(self, url: QUrl) -> None:
        s = url.toString()
        if s.startswith("copy:"):
            field = s[len("copy:"):]
            if self.op is None:
                return
            text = self._field_value(field)
            if text is None:
                return
            QApplication.clipboard().setText(text)
            QToolTip.showText(QCursor.pos(), f"📋 Zkopírováno", self.summary_view)
            return
        if url.scheme() in ("http", "https", "file", "mailto"):
            QDesktopServices.openUrl(url)

    def _field_value(self, field: str) -> str | None:
        op = self.op
        if op is None:
            return None
        if field == "title_cs":
            return op.title_cs or ""
        if field == "stag_url":
            return op.stag_url or ""
        if field == "objectives":
            return _format_numbered(op.objectives)
        return None
