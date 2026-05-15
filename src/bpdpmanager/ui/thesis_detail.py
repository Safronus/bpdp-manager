from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


def _make_form_layout() -> QFormLayout:
    """Form layout, který nechá fieldy roztáhnout na šířku panelu (na macOS jinak smrští)."""
    form = QFormLayout()
    form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
    form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.DontWrapRows)
    form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    form.setHorizontalSpacing(12)
    form.setVerticalSpacing(8)
    form.setContentsMargins(8, 8, 8, 8)
    return form

from ..models import Thesis
from ..models.enums import ALLOWED_TRANSITIONS, ThesisStatus, ThesisType
from ..services import ThesisService
from ..services.thesis_service import TransitionError
from .opponent_dialog import OpponentDialog
from .student_dialog import StudentDialog
from .widgets import DocumentsWidget, StatusBadge, StringListEditor


class ThesisDetail(QWidget):
    """Panel s detailem a editací jedné práce.

    Implementuje autosave: po každé změně pole se po krátké pauze (debounce)
    obsah uloží na pozadí; periodický timer slouží jako pojistka. Při přepnutí
    na jinou práci nebo při zavření aplikace se ještě jednou flushne.
    """

    saved = Signal(str)  # thesis id
    deleted = Signal(str)

    AUTOSAVE_DEBOUNCE_MS = 1500
    AUTOSAVE_SAFETY_MS = 30_000

    def __init__(self, service: ThesisService, parent=None) -> None:
        super().__init__(parent)
        self.service = service
        self.thesis: Thesis | None = None

        # Autosave state
        self._dirty = False
        self._loading = False  # potlačí dirty signály při programovém naplnění formuláře
        self._last_save_at: datetime | None = None

        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(self.AUTOSAVE_DEBOUNCE_MS)
        self._debounce_timer.timeout.connect(self._autosave)

        self._safety_timer = QTimer(self)
        self._safety_timer.setInterval(self.AUTOSAVE_SAFETY_MS)
        self._safety_timer.timeout.connect(self._autosave_if_dirty)
        self._safety_timer.start()

        self._build_ui()
        self._connect_dirty_signals()
        self._show_empty()

    # --- konstrukce UI -------------------------------------------------------

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self.placeholder = QLabel("Vyberte práci ve stromu vlevo, nebo přidejte novou.")
        self.placeholder.setStyleSheet("color: #888; padding: 24px;")
        outer.addWidget(self.placeholder)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        outer.addWidget(self.scroll)

        container = QWidget()
        self.scroll.setWidget(container)

        layout = QVBoxLayout(container)

        # Hlavička: stav + akce
        header = QHBoxLayout()
        self.status_badge = StatusBadge(ThesisStatus.INTERESTED)
        self.lbl_title = QLabel("")
        self.lbl_title.setStyleSheet("font-size: 16px; font-weight: bold;")
        header.addWidget(self.status_badge)
        header.addWidget(self.lbl_title, stretch=1)

        self.lbl_save_state = QLabel("")
        self.lbl_save_state.setStyleSheet("color: #888; font-size: 11px;")
        header.addWidget(self.lbl_save_state)

        self.btn_delete = QPushButton("Smazat")
        self.btn_delete.clicked.connect(self._delete)
        header.addWidget(self.btn_delete)
        layout.addLayout(header)

        # Přechody stavů
        transition_box = QGroupBox("Přechod do stavu")
        tl = QHBoxLayout(transition_box)
        self.transition_buttons: dict[ThesisStatus, QPushButton] = {}
        for status in ThesisStatus:
            btn = QPushButton(status.label)
            btn.clicked.connect(lambda _=False, s=status: self._transition(s))
            tl.addWidget(btn)
            self.transition_buttons[status] = btn
        layout.addWidget(transition_box)

        # Záložky
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self.tabs.addTab(self._build_basic_tab(), "Základní info")
        self.tabs.addTab(self._build_listing_tab(), "Vypsané téma")
        self.tabs.addTab(self._build_assignment_tab(), "Oficiální zadání")
        self.tabs.addTab(self._build_notes_tab(), "Poznámky")
        self.tabs.addTab(self._build_documents_tab(), "📎 Dokumenty")

        # Uložit
        save_row = QHBoxLayout()
        save_row.addStretch()
        self.btn_save = QPushButton("Uložit změny")
        self.btn_save.setDefault(True)
        self.btn_save.clicked.connect(self._save)
        save_row.addWidget(self.btn_save)
        layout.addLayout(save_row)

    def _build_basic_tab(self) -> QWidget:
        w = QWidget()
        outer = QVBoxLayout(w)
        outer.setContentsMargins(0, 0, 0, 0)
        form = _make_form_layout()

        self.cb_type = QComboBox()
        for t in ThesisType:
            self.cb_type.addItem(t.label, t.value)
        self.cb_type.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.ed_year = QLineEdit()
        self.ed_year.setPlaceholderText("např. 2024/2025")

        self.cb_student = QComboBox()
        self.cb_student.setEditable(False)
        self.cb_student.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.btn_new_student = QPushButton("+")
        self.btn_new_student.setFixedWidth(32)
        self.btn_new_student.clicked.connect(self._new_student)
        student_row = QHBoxLayout()
        student_row.addWidget(self.cb_student, stretch=1)
        student_row.addWidget(self.btn_new_student)

        self.cb_opponent = QComboBox()
        self.cb_opponent.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.btn_new_opponent = QPushButton("+")
        self.btn_new_opponent.setFixedWidth(32)
        self.btn_new_opponent.clicked.connect(self._new_opponent)
        opponent_row = QHBoxLayout()
        opponent_row.addWidget(self.cb_opponent, stretch=1)
        opponent_row.addWidget(self.btn_new_opponent)

        form.addRow("Typ", self.cb_type)
        form.addRow("Akademický rok", self.ed_year)
        form.addRow("Student", student_row)
        form.addRow("Oponent", opponent_row)

        outer.addLayout(form)
        outer.addStretch(1)
        return w

    def _build_listing_tab(self) -> QWidget:
        w = QWidget()
        outer = QVBoxLayout(w)
        outer.setContentsMargins(0, 0, 0, 0)

        form = _make_form_layout()
        self.ed_title_cs = QLineEdit()
        form.addRow("Název (CZ)", self.ed_title_cs)
        outer.addLayout(form)

        lbl = QLabel("Anotace")
        lbl.setContentsMargins(8, 4, 8, 0)
        outer.addWidget(lbl)

        self.ed_annotation = QPlainTextEdit()
        self.ed_annotation.setMinimumHeight(180)
        self.ed_annotation.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        outer.addWidget(self.ed_annotation, stretch=1)
        return w

    def _build_assignment_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)

        form = _make_form_layout()
        self.ed_title_en = QLineEdit()
        form.addRow("Název (EN)", self.ed_title_en)
        layout.addLayout(form)

        lbl_obj = QLabel("Body zadání")
        lbl_obj.setContentsMargins(8, 4, 8, 0)
        layout.addWidget(lbl_obj)
        self.ed_objectives = StringListEditor(placeholder="Bod zadání")
        self.ed_objectives.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.ed_objectives, stretch=1)

        lbl_ref = QLabel("Literární zdroje")
        lbl_ref.setContentsMargins(8, 4, 8, 0)
        layout.addWidget(lbl_ref)
        self.ed_references = StringListEditor(placeholder="Citace literárního zdroje")
        self.ed_references.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.ed_references, stretch=1)
        return w

    def _build_notes_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel("Poznámky a deník konzultací")
        lbl.setContentsMargins(8, 4, 8, 0)
        layout.addWidget(lbl)
        self.ed_notes = QPlainTextEdit()
        self.ed_notes.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.ed_notes, stretch=1)
        return w

    def _build_documents_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel("Dokumenty k práci (posudky, text práce, prezentace, odkazy…)")
        lbl.setContentsMargins(8, 4, 8, 0)
        layout.addWidget(lbl)
        self.documents_widget = DocumentsWidget(self.service)
        self.documents_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.documents_widget, stretch=1)
        return w

    # --- načítání / zobrazení -------------------------------------------------

    def _show_empty(self) -> None:
        self.placeholder.setVisible(True)
        self.scroll.setVisible(False)

    def _show_form(self) -> None:
        self.placeholder.setVisible(False)
        self.scroll.setVisible(True)

    def refresh_combos(self) -> None:
        """Znovu načti seznamy studentů a oponentů z DB."""
        self.cb_student.clear()
        self.cb_student.addItem("— bez studenta —", None)
        for s in self.service.list_students():
            self.cb_student.addItem(s.full_name, s.id)

        self.cb_opponent.clear()
        self.cb_opponent.addItem("— bez oponenta —", None)
        for o in self.service.list_opponents():
            self.cb_opponent.addItem(o.name, o.id)

    def set_thesis(self, thesis: Thesis | None) -> None:
        # Před přepnutím flushni rozpracované změny aktuální práce
        if self._dirty and self.thesis is not None:
            self._autosave()

        self.thesis = thesis
        if thesis is None:
            self._show_empty()
            self._update_save_state_label(idle=True)
            return
        self._show_form()

        self._loading = True
        try:
            self.refresh_combos()
            self.status_badge.setText(thesis.status.label)
            self.status_badge.setStyleSheet(
                f"QLabel {{ background-color: {thesis.status.color}; color: white; "
                f"font-weight: bold; padding: 2px 8px; border-radius: 8px; }}"
            )
            self.lbl_title.setText(thesis.display_title)

            idx = self.cb_type.findData(thesis.type.value)
            self.cb_type.setCurrentIndex(max(idx, 0))
            self.ed_year.setText(thesis.academic_year)

            idx = self.cb_student.findData(thesis.student_id)
            self.cb_student.setCurrentIndex(max(idx, 0))
            idx = self.cb_opponent.findData(thesis.opponent_id)
            self.cb_opponent.setCurrentIndex(max(idx, 0))

            self.ed_title_cs.setText(thesis.title_cs)
            self.ed_annotation.setPlainText(thesis.annotation)
            self.ed_title_en.setText(thesis.title_en)
            self.ed_objectives.set_items(thesis.objectives)
            self.ed_references.set_items(thesis.references)
            self.ed_notes.setPlainText(thesis.notes)
            self.documents_widget.set_thesis_id(thesis.id)
        finally:
            self._loading = False

        self._dirty = False
        self._debounce_timer.stop()
        self._update_save_state_label(idle=True)
        self._update_transition_buttons()

    def _update_transition_buttons(self) -> None:
        if self.thesis is None:
            return
        allowed = ALLOWED_TRANSITIONS.get(self.thesis.status, set())
        for status, btn in self.transition_buttons.items():
            btn.setEnabled(status in allowed and status != self.thesis.status)

    # --- autosave ------------------------------------------------------------

    def _connect_dirty_signals(self) -> None:
        """Napojí změny všech polí na ``_mark_dirty``."""
        self.cb_type.currentIndexChanged.connect(self._mark_dirty)
        self.ed_year.textChanged.connect(self._mark_dirty)
        self.cb_student.currentIndexChanged.connect(self._mark_dirty)
        self.cb_opponent.currentIndexChanged.connect(self._mark_dirty)
        self.ed_title_cs.textChanged.connect(self._mark_dirty)
        self.ed_annotation.textChanged.connect(self._mark_dirty)
        self.ed_title_en.textChanged.connect(self._mark_dirty)
        self.ed_objectives.changed.connect(self._mark_dirty)
        self.ed_references.changed.connect(self._mark_dirty)
        self.ed_notes.textChanged.connect(self._mark_dirty)
        # documents_widget si spravuje stav sám (ukládá okamžitě skrz service)

    def _mark_dirty(self, *_args) -> None:
        if self._loading or self.thesis is None:
            return
        self._dirty = True
        self._update_save_state_label(idle=False, pending=True)
        self._debounce_timer.start()  # restart debounce

    def _autosave_if_dirty(self) -> None:
        if self._dirty and self.thesis is not None:
            self._autosave()

    def _autosave(self) -> None:
        if self.thesis is None or not self._dirty:
            return
        try:
            self._collect_into_thesis()
            self.service.upsert_thesis(self.thesis)
        except Exception as exc:  # noqa: BLE001
            self._update_save_state_label(idle=False, pending=False, error=str(exc))
            return
        self._dirty = False
        self._last_save_at = datetime.now()
        self.lbl_title.setText(self.thesis.display_title)
        self._update_save_state_label(idle=False, pending=False)
        self.saved.emit(self.thesis.id)

    def flush(self) -> None:
        """Vynutí okamžitý zápis rozpracovaných změn (volat při zavření okna)."""
        self._debounce_timer.stop()
        if self._dirty:
            self._autosave()

    def _update_save_state_label(
        self,
        *,
        idle: bool = False,
        pending: bool = False,
        error: str | None = None,
    ) -> None:
        if idle:
            self.lbl_save_state.setText("")
            return
        if error:
            self.lbl_save_state.setText(f"⚠ Chyba ukládání: {error}")
            self.lbl_save_state.setStyleSheet("color: #c62828; font-size: 11px;")
            return
        if pending:
            self.lbl_save_state.setText("● Ukládám…")
            self.lbl_save_state.setStyleSheet("color: #ef6c00; font-size: 11px;")
            return
        # po úspěšném autosavu
        ts = self._last_save_at.strftime("%H:%M:%S") if self._last_save_at else ""
        self.lbl_save_state.setText(f"✓ Uloženo {ts}")
        self.lbl_save_state.setStyleSheet("color: #2e7d32; font-size: 11px;")

    # --- akce ----------------------------------------------------------------

    def _new_student(self) -> None:
        dlg = StudentDialog(self.service, parent=self)
        if dlg.exec():
            self._loading = True
            try:
                self.refresh_combos()
                idx = self.cb_student.findData(dlg.student.id)
            finally:
                self._loading = False
            if idx >= 0:
                # nastavení vybraného nového studenta už dirty být MÁ
                self.cb_student.setCurrentIndex(idx)

    def _new_opponent(self) -> None:
        dlg = OpponentDialog(self.service, parent=self)
        if dlg.exec():
            self._loading = True
            try:
                self.refresh_combos()
                idx = self.cb_opponent.findData(dlg.opponent.id)
            finally:
                self._loading = False
            if idx >= 0:
                self.cb_opponent.setCurrentIndex(idx)

    def _collect_into_thesis(self) -> None:
        assert self.thesis is not None
        self.thesis.type = ThesisType(self.cb_type.currentData())
        self.thesis.academic_year = self.ed_year.text().strip()
        self.thesis.student_id = self.cb_student.currentData()
        self.thesis.opponent_id = self.cb_opponent.currentData()
        self.thesis.title_cs = self.ed_title_cs.text().strip()
        self.thesis.annotation = self.ed_annotation.toPlainText().strip()
        self.thesis.title_en = self.ed_title_en.text().strip()
        self.thesis.objectives = self.ed_objectives.items()
        self.thesis.references = self.ed_references.items()
        self.thesis.notes = self.ed_notes.toPlainText().strip()
        # attachments spravuje DocumentsWidget okamžitě skrz service,
        # zde je proto nepřepisujeme — jen znovu načteme aktuální stav.
        fresh = self.service.get_thesis(self.thesis.id)
        if fresh is not None:
            self.thesis.attachments = fresh.attachments

    def _save(self) -> None:
        if self.thesis is None:
            return
        self._debounce_timer.stop()
        self._dirty = True  # vynutí, aby _autosave vůbec běžel
        self._autosave()

    def _delete(self) -> None:
        if self.thesis is None:
            return
        confirm = QMessageBox.question(
            self,
            "Smazat práci",
            f"Opravdu smazat „{self.thesis.display_title}“?\nTuto akci nelze vrátit.",
        )
        if confirm == QMessageBox.StandardButton.Yes:
            tid = self.thesis.id
            self.service.delete_thesis(tid)
            self.set_thesis(None)
            self.deleted.emit(tid)

    def _transition(self, target: ThesisStatus) -> None:
        if self.thesis is None:
            return
        self._collect_into_thesis()
        self.service.upsert_thesis(self.thesis)
        try:
            self.service.transition(self.thesis.id, target)
        except TransitionError as exc:
            QMessageBox.warning(self, "Přechod stavu", str(exc))
            return
        self.set_thesis(self.service.get_thesis(self.thesis.id))
        self.saved.emit(self.thesis.id)
