from __future__ import annotations

import html
import re
from datetime import date, datetime
from pathlib import Path

_NUM_PREFIX_RE = re.compile(r"^\s*\d+\.\s+")


def _split_items(text: str | None) -> list[str]:
    """Rozdělí volný text na položky — co řádek, to bod.

    Pro zpětnou kompatibilitu odstraňuje případnou pořadovou číslici
    na začátku řádku (``"1. "``, ``"2. "`` …), aby se v Souhrnu
    nečíslovalo dvakrát.
    """
    if not text:
        return []
    out = []
    for line in text.split("\n"):
        cleaned = _NUM_PREFIX_RE.sub("", line.strip())
        if cleaned:
            out.append(cleaned)
    return out


def _format_numbered(text: str | None) -> str:
    """Vrátí číslovaný plain text (1. ..., 2. ...) — pro clipboard / export."""
    items = _split_items(text)
    return "\n".join(f"{i + 1}. {item}" for i, item in enumerate(items))

from PySide6.QtCore import Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
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


# Year mode konstanty — určují rozsah a chování comba pro akademický rok.
YEAR_MODE_CURRENT = "current"   # jen aktuální rok, combo disabled
YEAR_MODE_FUTURE = "future"     # next + next+1 (budoucí 2 roky)
YEAR_MODE_HISTORY = "history"   # 2009/2010 .. current-1
YEAR_MODE_ALL = "all"           # 2009/2010 .. current+2, plně editovatelné


def _current_year_start() -> int:
    today = date.today()
    return today.year if today.month >= 9 else today.year - 1


def _academic_year_choices(mode: str) -> list[str]:
    """Vrátí seznam ak. roků pro daný mode, vždy sestupně (nejaktuálnější nahoře)."""
    s = _current_year_start()
    current = f"{s}/{s + 1}"
    next_year = f"{s + 1}/{s + 2}"
    next_next = f"{s + 2}/{s + 3}"

    if mode == YEAR_MODE_CURRENT:
        return [current]
    if mode == YEAR_MODE_FUTURE:
        return [next_year, next_next]
    if mode == YEAR_MODE_HISTORY:
        years = [f"{y}/{y + 1}" for y in range(2009, s)]  # 2009/2010 .. (current-1)/current
        return list(reversed(years))
    # YEAR_MODE_ALL
    end = s + 2
    years = [f"{y}/{y + 1}" for y in range(2009, end + 1)]
    return list(reversed(years))


def _setup_searchable_combo(combo: QComboBox) -> None:
    """Editable combo s našeptáváním přes 'contains' filter (case-insensitive)."""
    combo.setEditable(True)
    combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
    completer = combo.completer()
    if completer is not None:
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setCompletionMode(
            completer.CompletionMode.PopupCompletion
        )

from ..models import Thesis
from ..models.enums import ALLOWED_TRANSITIONS, ThesisStatus, ThesisType
from ..services import ThesisService
from ..services.thesis_service import TransitionError
from .opponent_dialog import OpponentDialog
from .student_dialog import StudentDialog
from .widgets import DocumentsWidget, StatusBadge


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

    def __init__(
        self,
        service: ThesisService,
        year_mode: str = YEAR_MODE_ALL,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.service = service
        self.thesis: Thesis | None = None
        self._year_mode = year_mode

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

        # Hlavička, transition box, taby a save row jsou pevné — nescrollují.
        # Scrollování řeší jednotlivé taby uvnitř (Souhrn QTextBrowser
        # interně; Téma zadání má vlastní QScrollArea v _build_topic_tab).
        self.container = QWidget()
        outer.addWidget(self.container)

        layout = QVBoxLayout(self.container)

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

        self.tabs.addTab(self._build_summary_tab(), "📋 Souhrn")
        self.tabs.addTab(self._build_topic_tab(), "📝 Téma zadání")
        self.tabs.addTab(self._build_notes_tab(), "Poznámky")
        self.tabs.addTab(self._build_plagiarism_tab(), "🔍 Plagiátorství")
        self.tabs.addTab(self._build_documents_tab(), "📎 Dokumenty")
        self.tabs.currentChanged.connect(self._on_tab_changed)

        # Uložit
        save_row = QHBoxLayout()
        save_row.addStretch()
        self.btn_save = QPushButton("Uložit změny")
        self.btn_save.setDefault(True)
        self.btn_save.clicked.connect(self._save)
        save_row.addWidget(self.btn_save)
        layout.addLayout(save_row)

    def _build_topic_tab(self) -> QWidget:
        """Sloučená záložka Téma zadání s vlastní vnitřní QScrollArea.

        Hlavička detailu, transition tlačítka a save tlačítko zůstávají
        pevně, scrolluje jen obsah této záložky (sekce uvnitř).
        """
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        inner = QWidget()
        inner_layout = QVBoxLayout(inner)
        inner_layout.setContentsMargins(8, 8, 8, 8)
        inner_layout.setSpacing(12)

        inner_layout.addWidget(self._build_basic_section())
        inner_layout.addWidget(self._build_listing_section(), stretch=1)
        inner_layout.addWidget(self._build_assignment_section(), stretch=2)

        scroll.setWidget(inner)
        return scroll

    # --- sekce uvnitř Téma zadání -------------------------------------------

    def _build_basic_section(self) -> QGroupBox:
        """Kompaktní jednořádkové info: Typ (radio) + Rok (combo) + Student + Oponent."""
        box = QGroupBox("Základní info")
        layout = QVBoxLayout(box)
        layout.setContentsMargins(8, 12, 8, 8)

        row = QHBoxLayout()
        row.setSpacing(10)

        # Typ — radio BP / DP
        row.addWidget(QLabel("Typ:"))
        self.rb_bp = QRadioButton("BP")
        self.rb_dp = QRadioButton("DP")
        self._type_group = QButtonGroup(self)
        self._type_group.addButton(self.rb_bp, 0)
        self._type_group.addButton(self.rb_dp, 1)
        self.rb_bp.setChecked(True)
        row.addWidget(self.rb_bp)
        row.addWidget(self.rb_dp)
        row.addSpacing(12)

        # Rok — combobox s rozsahem podle year_mode
        row.addWidget(QLabel("Rok:"))
        self.cb_year = QComboBox()
        for y in _academic_year_choices(self._year_mode):
            self.cb_year.addItem(y)
        self.cb_year.setMinimumContentsLength(9)  # "2027/2028"
        self.cb_year.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )

        if self._year_mode == YEAR_MODE_CURRENT:
            # Aktuální tab — rok je vždy aktuální a nelze měnit
            self.cb_year.setEnabled(False)
            self.cb_year.setToolTip("Aktuální akademický rok — zamčeno")
        elif self._year_mode == YEAR_MODE_ALL:
            # Vše tab — editovatelné, kdyby uživatel chtěl ojedinělý rok
            self.cb_year.setEditable(True)
            self.cb_year.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        else:
            # Budoucí / Historie — jen výběr z dropdownu, needitovatelné
            self.cb_year.setEditable(False)

        row.addWidget(self.cb_year)
        row.addSpacing(12)

        # Student — combobox s našeptáváním + tlačítko
        row.addWidget(QLabel("Student:"))
        self.cb_student = QComboBox()
        self.cb_student.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.cb_student.setMinimumWidth(180)
        _setup_searchable_combo(self.cb_student)
        if self.cb_student.lineEdit() is not None:
            self.cb_student.lineEdit().setPlaceholderText("(bez studenta)")
        self.btn_new_student = QPushButton("+")
        self.btn_new_student.setFixedWidth(28)
        self.btn_new_student.clicked.connect(self._new_student)
        row.addWidget(self.cb_student, stretch=1)
        row.addWidget(self.btn_new_student)
        row.addSpacing(12)

        # Oponent — totéž
        row.addWidget(QLabel("Oponent:"))
        self.cb_opponent = QComboBox()
        self.cb_opponent.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.cb_opponent.setMinimumWidth(180)
        _setup_searchable_combo(self.cb_opponent)
        if self.cb_opponent.lineEdit() is not None:
            self.cb_opponent.lineEdit().setPlaceholderText("(bez oponenta)")
        self.btn_new_opponent = QPushButton("+")
        self.btn_new_opponent.setFixedWidth(28)
        self.btn_new_opponent.clicked.connect(self._new_opponent)
        row.addWidget(self.cb_opponent, stretch=1)
        row.addWidget(self.btn_new_opponent)

        layout.addLayout(row)
        return box

    def _build_listing_section(self) -> QGroupBox:
        box = QGroupBox("Vypsané téma (název CZ/EN, anotace CZ/EN)")
        layout = QVBoxLayout(box)
        layout.setContentsMargins(8, 12, 8, 8)

        form = _make_form_layout()
        self.ed_title_cs = QLineEdit()
        self.ed_title_en = QLineEdit()
        form.addRow("Název (CZ)", self.ed_title_cs)
        form.addRow("Název (EN)", self.ed_title_en)
        layout.addLayout(form)

        # Anotace CZ a EN vedle sebe — šetří svislé místo
        annot_row = QHBoxLayout()
        annot_row.setSpacing(12)

        cz_col = QVBoxLayout()
        cz_col.setSpacing(2)
        lbl_cs = QLabel("Anotace (CZ)")
        lbl_cs.setContentsMargins(2, 4, 0, 0)
        cz_col.addWidget(lbl_cs)
        self.ed_annotation = QPlainTextEdit()
        self.ed_annotation.setMinimumHeight(120)
        self.ed_annotation.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        cz_col.addWidget(self.ed_annotation, stretch=1)
        annot_row.addLayout(cz_col, stretch=1)

        en_col = QVBoxLayout()
        en_col.setSpacing(2)
        lbl_en = QLabel("Anotace (EN)")
        lbl_en.setContentsMargins(2, 4, 0, 0)
        en_col.addWidget(lbl_en)
        self.ed_annotation_en = QPlainTextEdit()
        self.ed_annotation_en.setMinimumHeight(120)
        self.ed_annotation_en.setPlaceholderText(
            "English version of the annotation (optional)."
        )
        self.ed_annotation_en.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        en_col.addWidget(self.ed_annotation_en, stretch=1)
        annot_row.addLayout(en_col, stretch=1)

        layout.addLayout(annot_row, stretch=1)
        return box

    def _build_assignment_section(self) -> QGroupBox:
        box = QGroupBox("Oficiální zadání (body zadání, literatura)")
        layout = QVBoxLayout(box)
        layout.setContentsMargins(8, 12, 8, 8)

        lbl_obj = QLabel(
            "Body zadání  —  každý bod na nové řádce, číslování se přidá "
            "automaticky v Souhrnu."
        )
        lbl_obj.setContentsMargins(8, 4, 8, 0)
        layout.addWidget(lbl_obj)
        self.ed_objectives = QPlainTextEdit()
        self.ed_objectives.setMinimumHeight(120)
        self.ed_objectives.setPlaceholderText(
            "Nastudujte a popište problematiku testování softwaru.\n"
            "Prozkoumejte možnosti testování pomocí umělé inteligence.\n"
            "Rozeberte vhodné nástroje AI využitelné pro testování softwaru.\n"
            "…"
        )
        self.ed_objectives.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        layout.addWidget(self.ed_objectives, stretch=1)

        lbl_ref = QLabel(
            "Literární zdroje  —  každá citace na nové řádce, číslování se "
            "přidá automaticky v Souhrnu."
        )
        lbl_ref.setContentsMargins(8, 4, 8, 0)
        layout.addWidget(lbl_ref)
        self.ed_references = QPlainTextEdit()
        self.ed_references.setMinimumHeight(120)
        self.ed_references.setPlaceholderText(
            "SMITH, Adam Leon; BLACK, Rex et al. Artificial Intelligence and "
            "Software Testing… BCS, 2022. ISBN 1780175787.\n"
            "ZERILLI, John; DANAHER, John et al. A citizen's guide to artificial "
            "intelligence. Cambridge, Massachusetts: The MIT Press, 2020.\n"
            "…"
        )
        self.ed_references.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        layout.addWidget(self.ed_references, stretch=1)
        return box

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

    def _build_plagiarism_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        # Shoda %
        perc_row = QHBoxLayout()
        perc_row.addWidget(QLabel("Procento shody:"))
        self.spin_plag_pct = QDoubleSpinBox()
        self.spin_plag_pct.setRange(0.0, 100.0)
        self.spin_plag_pct.setDecimals(1)
        self.spin_plag_pct.setSingleStep(0.5)
        self.spin_plag_pct.setSuffix(" %")
        self.spin_plag_pct.setFixedWidth(140)
        # Speciální text pro hodnotu 0.0 — "nezadáno"
        self.spin_plag_pct.setSpecialValueText("(nezadáno)")
        perc_row.addWidget(self.spin_plag_pct)
        perc_row.addStretch()
        layout.addLayout(perc_row)

        # Komentář
        lbl_c = QLabel("Komentář k výsledku plagiátorství:")
        lbl_c.setContentsMargins(0, 8, 0, 0)
        layout.addWidget(lbl_c)
        self.ed_plag_comment = QPlainTextEdit()
        self.ed_plag_comment.setPlaceholderText(
            "Např. „Drobné shody v citacích a standardních formulacích, žádné podezření.\""
        )
        self.ed_plag_comment.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        layout.addWidget(self.ed_plag_comment, stretch=1)

        # PDF protokol
        pdf_lbl = QLabel("PDF protokol o plagiátorství:")
        pdf_lbl.setContentsMargins(0, 8, 0, 0)
        layout.addWidget(pdf_lbl)

        pdf_row = QHBoxLayout()
        self.lbl_plag_pdf = QLabel("(žádný soubor)")
        self.lbl_plag_pdf.setStyleSheet("color: #888;")
        pdf_row.addWidget(self.lbl_plag_pdf, stretch=1)

        self.btn_plag_upload = QPushButton("📎 Vybrat PDF…")
        self.btn_plag_upload.clicked.connect(self._plag_upload)
        pdf_row.addWidget(self.btn_plag_upload)

        self.btn_plag_open = QPushButton("📂 Otevřít")
        self.btn_plag_open.clicked.connect(self._plag_open)
        pdf_row.addWidget(self.btn_plag_open)

        self.btn_plag_remove = QPushButton("🗑 Odebrat")
        self.btn_plag_remove.clicked.connect(self._plag_remove)
        pdf_row.addWidget(self.btn_plag_remove)

        layout.addLayout(pdf_row)
        return w

    def _build_summary_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)

        self.summary_view = QTextBrowser()
        self.summary_view.setOpenExternalLinks(False)
        self.summary_view.setOpenLinks(False)  # anchory zpracujeme sami
        self.summary_view.anchorClicked.connect(self._on_summary_anchor_clicked)
        self.summary_view.setStyleSheet(
            "QTextBrowser { padding: 12px; font-family: -apple-system, "
            "'Segoe UI', sans-serif; }"
        )
        layout.addWidget(self.summary_view, stretch=1)
        return w

    # --- načítání / zobrazení -------------------------------------------------

    def _show_empty(self) -> None:
        self.placeholder.setVisible(True)
        self.container.setVisible(False)

    def _show_form(self) -> None:
        self.placeholder.setVisible(False)
        self.container.setVisible(True)

    def refresh_combos(self) -> None:
        """Znovu načti seznamy studentů a oponentů z DB.

        Aktuální výběr se **zachová** — voláno typicky po zavření dialogu
        správy studentů/oponentů, aby se nový záznam okamžitě objevil
        v rozbalovacím seznamu, aniž by se ztratila vazba na aktuálně
        editované práci.
        """
        # Zachyť aktuální výběr před clearem (přes ID)
        current_student_id = self._resolve_combo_id(self.cb_student)
        current_opponent_id = self._resolve_combo_id(self.cb_opponent)

        # Suprimuj _mark_dirty signály během programového refillu
        was_loading = self._loading
        self._loading = True
        try:
            self.cb_student.clear()
            for s in self.service.list_students():
                self.cb_student.addItem(s.full_name, s.id)
            self._set_combo_to_id(self.cb_student, current_student_id)

            self.cb_opponent.clear()
            for o in self.service.list_opponents():
                self.cb_opponent.addItem(o.name, o.id)
            self._set_combo_to_id(self.cb_opponent, current_opponent_id)
        finally:
            self._loading = was_loading

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

            if thesis.type == ThesisType.BP:
                self.rb_bp.setChecked(True)
            else:
                self.rb_dp.setChecked(True)
            self._set_year(thesis.academic_year or "")

            self._set_combo_to_id(self.cb_student, thesis.student_id)
            self._set_combo_to_id(self.cb_opponent, thesis.opponent_id)

            self.ed_title_cs.setText(thesis.title_cs)
            self.ed_annotation.setPlainText(thesis.annotation)
            self.ed_annotation_en.setPlainText(thesis.annotation_en or "")
            self.ed_title_en.setText(thesis.title_en)
            self.ed_objectives.setPlainText(thesis.objectives or "")
            self.ed_references.setPlainText(thesis.references or "")
            self.ed_notes.setPlainText(thesis.notes)

            # Plagiátorství
            self.spin_plag_pct.setValue(
                thesis.plagiarism_similarity_pct or 0.0
            )
            self.ed_plag_comment.setPlainText(thesis.plagiarism_comment or "")
            self._update_plagiarism_pdf_display()

            self.documents_widget.set_thesis_id(thesis.id)
        finally:
            self._loading = False

        self._dirty = False
        self._debounce_timer.stop()
        self._update_save_state_label(idle=True)
        self._update_transition_buttons()
        # Po výběru práce ze seznamu přepneme na Souhrn — uživatel
        # vidí jako první rozhled celé práce, pak může jít editovat.
        # _refresh_summary voláme přímo, protože setCurrentIndex(0) v případě,
        # že už jsme na 0, nevyvolá _on_tab_changed.
        self.tabs.setCurrentIndex(0)
        self._refresh_summary()

    def _update_transition_buttons(self) -> None:
        if self.thesis is None:
            return
        allowed = ALLOWED_TRANSITIONS.get(self.thesis.status, set())
        for status, btn in self.transition_buttons.items():
            btn.setEnabled(status in allowed and status != self.thesis.status)

    # --- autosave ------------------------------------------------------------

    def _connect_dirty_signals(self) -> None:
        """Napojí změny všech polí na ``_mark_dirty``."""
        self.rb_bp.toggled.connect(self._mark_dirty)
        self.rb_dp.toggled.connect(self._mark_dirty)
        self.cb_year.currentTextChanged.connect(self._mark_dirty)
        self.spin_plag_pct.valueChanged.connect(self._mark_dirty)
        self.ed_plag_comment.textChanged.connect(self._mark_dirty)
        self.cb_student.currentIndexChanged.connect(self._mark_dirty)
        self.cb_opponent.currentIndexChanged.connect(self._mark_dirty)
        self.ed_title_cs.textChanged.connect(self._mark_dirty)
        self.ed_annotation.textChanged.connect(self._mark_dirty)
        self.ed_annotation_en.textChanged.connect(self._mark_dirty)
        self.ed_title_en.textChanged.connect(self._mark_dirty)
        self.ed_objectives.textChanged.connect(self._mark_dirty)
        self.ed_references.textChanged.connect(self._mark_dirty)
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
        # Souhrn se po uložení změn musí přegenerovat (aby seděl s realitou)
        if self.tabs.currentIndex() == 0:
            self._refresh_summary()
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

    # --- souhrn (read-only přehled) -----------------------------------------

    def _on_tab_changed(self, index: int) -> None:
        # Souhrn (tab 0) — vždy přegeneruj při zobrazení
        if index == 0:
            self._refresh_summary()

    def _refresh_summary(self) -> None:
        if not hasattr(self, "summary_view"):
            return
        if self.thesis is None:
            self.summary_view.setHtml(
                "<p style='color:#888;padding:24px;'>"
                "Vyberte práci ve stromu vlevo, nebo přidejte novou."
                "</p>"
            )
            return
        self.summary_view.setHtml(self._build_summary_html(self.thesis))

    @staticmethod
    def _copy_btn(field: str, tooltip: str) -> str:
        """HTML pro malé „📋" tlačítko, které spustí copy:field anchor."""
        return (
            f'&nbsp;<a href="copy:{field}" title="{tooltip}" '
            'style="text-decoration:none;font-size:11pt;'
            'color:#42a5f5;">📋</a>'
        )

    def _build_summary_html(self, thesis) -> str:
        """Sestaví HTML přehled práce — styl podobný uživatelovu zápisníku."""
        student = self.service.get_student(thesis.student_id) if thesis.student_id else None
        opponent = self.service.get_opponent(thesis.opponent_id) if thesis.opponent_id else None

        status = thesis.status
        status_color = status.color

        type_label = thesis.type.value
        year = thesis.academic_year or "—"
        title_cs = thesis.title_cs or "(bez názvu CZ)"
        title_en = thesis.title_en or ""

        student_name = student.full_name if student else "(nepřiřazený student)"
        obor = student.obor if student and student.obor else "—"
        uni_id = student.university_id if student and student.university_id else "—"
        opp_name = opponent.name if opponent else ""

        annotation = thesis.annotation.strip() if thesis.annotation else ""
        annotation_en = thesis.annotation_en.strip() if thesis.annotation_en else ""
        objectives_text = (thesis.objectives or "").strip()
        references_text = (thesis.references or "").strip()

        # validace připravenosti
        ready_listing, missing_listing = thesis.is_ready_for_listing()
        ready_assignment, missing_assignment = thesis.is_ready_for_assignment()

        e = html.escape
        cp = self._copy_btn

        # ── status bar (velký, barevný, hned patrný) ────────────────────────
        status_bar = (
            f'<table width="100%" cellpadding="14" cellspacing="0" '
            f'style="background-color:{status_color};margin-bottom:18px;">'
            f"<tr>"
            f'<td style="color:white;font-weight:bold;font-size:16pt;'
            f"letter-spacing:1.5px;\">⬢  {e(status.label.upper())}</td>"
            f'<td align="right" style="color:white;font-size:11pt;">'
            f"Akademický rok: <b>{e(year)}</b></td>"
            f"</tr></table>"
        )

        # ── připravenost (varování, co chybí pro listing/assignment) ────────
        readiness_html = ""
        if not ready_assignment and missing_assignment:
            readiness_html = (
                f'<div style="background:#fff3e0;border-left:4px solid #ef6c00;'
                f"padding:10px 14px;margin-bottom:14px;color:#555;\">"
                f'<b style="color:#ef6c00;">Pro oficiální zadání chybí:</b> '
                f"{e(', '.join(missing_assignment))}"
                f"</div>"
            )

        # ── nadpisová sekce ────────────────────────────────────────────────
        title_cs_with_copy = (
            f"{e(title_cs)}{cp('title_cs', 'Zkopírovat název (CZ)')}"
        )
        header_line = (
            f'<h2 style="color:{status_color};margin:0 0 4px 0;line-height:1.35;">'
            f"{e(type_label)} — {title_cs_with_copy} — "
            f'<span>{e(student_name)}</span> '
            f'<span style="color:#9e9e9e;">({e(obor)})</span> '
            f'<span style="color:#9e9e9e;">→ {e(uni_id)}</span> '
            f'<span style="color:#9e9e9e;">(Oponent - {e(opp_name)})</span>'
            f"</h2>"
        )
        en_line = ""
        if title_en:
            en_line = (
                f'<p style="color:#9e9e9e;font-style:italic;'
                f'margin:0 0 18px 0;">{e(title_en)}'
                f"{cp('title_en', 'Zkopírovat název (EN)')}</p>"
            )

        # ── Anotace ────────────────────────────────────────────────────────
        if annotation:
            anot_html = (
                e(annotation)
                .replace("\n\n", "</p><p style='text-indent:2em;'>")
                .replace("\n", "<br>")
            )
            anot_html = f"<p style='text-indent:2em;'>{anot_html}</p>"
        else:
            anot_html = "<p style='color:#888;font-style:italic;'>(bez anotace)</p>"

        # ── Anotace (EN) ───────────────────────────────────────────────────
        if annotation_en:
            anot_en_html = (
                e(annotation_en)
                .replace("\n\n", "</p><p style='text-indent:2em;'>")
                .replace("\n", "<br>")
            )
            anot_en_html = f"<p style='text-indent:2em;'>{anot_en_html}</p>"
        else:
            anot_en_html = ""

        # ── Body zadání — auto-číslováno pomocí <ol> ───────────────────────
        obj_items = _split_items(objectives_text)
        if obj_items:
            items_html = "".join(
                f"<li style='margin-bottom:4px;'>{e(line)}</li>" for line in obj_items
            )
            obj_html = (
                f"<ol style='margin-left:1.2em;line-height:1.55;'>{items_html}</ol>"
            )
        else:
            obj_html = "<p style='color:#888;font-style:italic;'>(žádné body zadání)</p>"

        # ── Literární zdroje — auto-číslováno pomocí <ol> ──────────────────
        ref_items = _split_items(references_text)
        if ref_items:
            items_html = "".join(
                f"<li style='margin-bottom:6px;'>{e(line)}</li>" for line in ref_items
            )
            ref_html = (
                f"<ol style='margin-left:1.2em;line-height:1.55;'>{items_html}</ol>"
            )
        else:
            ref_html = "<p style='color:#888;font-style:italic;'>(žádné literární zdroje)</p>"

        section_header_style = "color:#ffa726;margin-top:18px;margin-bottom:6px;"

        anot_en_section = ""
        if annotation_en:
            anot_en_section = (
                f'<h3 style="{section_header_style}">Anotace (EN):'
                f"{cp('annotation_en', 'Zkopírovat anotaci EN')}</h3>"
                f"{anot_en_html}"
            )

        # ── Plagiátorství (jen pokud něco vyplněno) ────────────────────────
        plag_section = ""
        has_plag_pct = thesis.plagiarism_similarity_pct is not None
        has_plag_comment = bool((thesis.plagiarism_comment or "").strip())
        has_plag_pdf = bool(thesis.plagiarism_pdf_filename)
        if has_plag_pct or has_plag_comment or has_plag_pdf:
            pct_str = (
                f"{thesis.plagiarism_similarity_pct:.1f} %"
                if has_plag_pct
                else "—"
            )
            comment_html = (
                e(thesis.plagiarism_comment.strip()).replace("\n", "<br>")
                if has_plag_comment
                else "<span style='color:#888;font-style:italic;'>(bez komentáře)</span>"
            )
            pdf_html = (
                f"📄 {e(thesis.plagiarism_pdf_filename)}"
                if has_plag_pdf
                else "<span style='color:#888;font-style:italic;'>(žádné PDF)</span>"
            )
            plag_section = (
                f'<h3 style="{section_header_style}">🔍 Plagiátorství:</h3>'
                f"<p><b>Shoda:</b> {pct_str}</p>"
                f"<p><b>Komentář:</b> {comment_html}</p>"
                f"<p><b>PDF protokol:</b> {pdf_html}</p>"
            )

        return (
            "<html><body>"
            f"{status_bar}"
            f"{readiness_html}"
            f"{header_line}"
            f"{en_line}"
            f'<h3 style="{section_header_style}">Anotace:'
            f"{cp('annotation', 'Zkopírovat anotaci')}</h3>"
            f"{anot_html}"
            f"{anot_en_section}"
            f'<h3 style="{section_header_style}">Body zadání:'
            f"{cp('objectives', 'Zkopírovat body zadání')}</h3>"
            f"{obj_html}"
            f'<h3 style="{section_header_style}">Literární zdroje:'
            f"{cp('references', 'Zkopírovat literární zdroje')}</h3>"
            f"{ref_html}"
            f"{plag_section}"
            "</body></html>"
        )

    def _on_summary_anchor_clicked(self, url: QUrl) -> None:
        """Click na 'copy:<field>' v Souhrnu → zkopíruje hodnotu do schránky."""
        s = url.toString()
        if not s.startswith("copy:"):
            return
        field = s[len("copy:"):]
        if self.thesis is None:
            return

        text, label = self._summary_field_value(field)
        if text is None:
            return

        QApplication.clipboard().setText(text)
        QToolTip.showText(
            QCursor.pos(),
            f"📋  Zkopírováno: {label}",
            self.summary_view,
        )

    def _summary_field_value(self, field: str) -> tuple[str | None, str]:
        """Vrátí (text-do-schránky, popisek-pro-tooltip) pro daný field."""
        t = self.thesis
        if t is None:
            return None, ""
        if field == "title_cs":
            return t.title_cs or "", "název (CZ)"
        if field == "title_en":
            return t.title_en or "", "název (EN)"
        if field == "annotation":
            return t.annotation or "", "anotace"
        if field == "annotation_en":
            return t.annotation_en or "", "anotace (EN)"
        if field == "objectives":
            return _format_numbered(t.objectives), "body zadání"
        if field == "references":
            return _format_numbered(t.references), "literární zdroje"
        return None, ""

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

    def _set_year(self, year: str) -> None:
        """Nastav cb_year na danou hodnotu i kdyby nebyla v dropdownu.

        - Editable combo: setEditText / setCurrentText pohodlně funguje.
        - Non-editable combo: pokud chybí v seznamu, dočasně ji přidáme,
          aby se zobrazila správná hodnota i pro historické práce mimo
          standardní rozsah year_mode.
        """
        if not year:
            self.cb_year.setCurrentIndex(-1)
            return
        idx = self.cb_year.findText(year)
        if idx < 0 and not self.cb_year.isEditable():
            # Nebyla v seznamu — vlož ji na začátek, ať je vidět správná hodnota
            self.cb_year.insertItem(0, year)
            idx = 0
        if idx >= 0:
            self.cb_year.setCurrentIndex(idx)
        else:
            # editable combo — prostě nastav text
            self.cb_year.setCurrentText(year)

    @staticmethod
    def _set_combo_to_id(combo: QComboBox, target_id: str | None) -> None:
        """Nastav combo na položku s daným ID, nebo ho vyprázdni (None)."""
        if target_id:
            idx = combo.findData(target_id)
            if idx >= 0:
                combo.setCurrentIndex(idx)
                return
        combo.setCurrentIndex(-1)
        if combo.lineEdit() is not None:
            combo.lineEdit().clear()

    @staticmethod
    def _resolve_combo_id(combo: QComboBox) -> str | None:
        """Vrátí ID (UserData) pro položku odpovídající aktuálnímu textu combo.

        - Prázdný text → ``None`` (explicitní „bez studenta / oponenta").
        - Text se přesně shoduje s položkou → ID té položky.
        - Text se neshoduje (user píše a ještě nedopsal) → poslední vybraná
          položka přes ``currentData()`` (nemažeme vazbu během psaní).
        """
        text = combo.currentText().strip().lower()
        if not text:
            return None
        for i in range(combo.count()):
            if combo.itemText(i).strip().lower() == text:
                return combo.itemData(i)
        return combo.currentData()

    def _collect_into_thesis(self) -> None:
        assert self.thesis is not None
        self.thesis.type = ThesisType.BP if self.rb_bp.isChecked() else ThesisType.DP
        self.thesis.academic_year = self.cb_year.currentText().strip()
        self.thesis.student_id = self._resolve_combo_id(self.cb_student)
        self.thesis.opponent_id = self._resolve_combo_id(self.cb_opponent)
        self.thesis.title_cs = self.ed_title_cs.text().strip()
        self.thesis.annotation = self.ed_annotation.toPlainText().strip()
        self.thesis.annotation_en = self.ed_annotation_en.toPlainText().strip()
        self.thesis.title_en = self.ed_title_en.text().strip()
        self.thesis.objectives = self.ed_objectives.toPlainText()
        self.thesis.references = self.ed_references.toPlainText()
        self.thesis.notes = self.ed_notes.toPlainText().strip()

        # Plagiátorství — hodnota 0 znamená "nezadáno" (specialValueText)
        pct = self.spin_plag_pct.value()
        self.thesis.plagiarism_similarity_pct = pct if pct > 0 else None
        self.thesis.plagiarism_comment = self.ed_plag_comment.toPlainText().strip()
        # attachments spravuje DocumentsWidget okamžitě skrz service,
        # zde je proto nepřepisujeme — jen znovu načteme aktuální stav.
        fresh = self.service.get_thesis(self.thesis.id)
        if fresh is not None:
            self.thesis.attachments = fresh.attachments

    # --- plagiátorství akce -------------------------------------------------

    def _update_plagiarism_pdf_display(self) -> None:
        """Aktualizuje label a stav tlačítek podle stavu PDF."""
        has_pdf = bool(
            self.thesis and self.thesis.plagiarism_pdf_filename
        )
        if has_pdf:
            self.lbl_plag_pdf.setText(f"📄 {self.thesis.plagiarism_pdf_filename}")
            self.lbl_plag_pdf.setStyleSheet("")
        else:
            self.lbl_plag_pdf.setText("(žádný soubor)")
            self.lbl_plag_pdf.setStyleSheet("color: #888;")
        self.btn_plag_open.setEnabled(has_pdf)
        self.btn_plag_remove.setEnabled(has_pdf)

    def _plag_upload(self) -> None:
        if self.thesis is None:
            return
        path_str, _ = QFileDialog.getOpenFileName(
            self,
            "Vyber PDF s výsledkem plagiátorství",
            str(Path.home()),
            "PDF soubory (*.pdf);;Všechny soubory (*.*)",
        )
        if not path_str:
            return
        try:
            self.service.set_plagiarism_pdf(self.thesis.id, Path(path_str))
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(
                self, "Chyba", f"Nepodařilo se uložit PDF:\n{exc}"
            )
            return
        fresh = self.service.get_thesis(self.thesis.id)
        if fresh is not None:
            self.thesis = fresh
        self._update_plagiarism_pdf_display()
        # Pokud je viditelný Souhrn, přegeneruj ho
        if self.tabs.currentIndex() == 0:
            self._refresh_summary()

    def _plag_open(self) -> None:
        if self.thesis is None:
            return
        path = self.service.plagiarism_pdf_path(self.thesis.id)
        if path is None or not path.exists():
            QMessageBox.information(
                self, "Otevřít PDF", "Žádné PDF není nahrané."
            )
            return
        self._open_path_in_os(path)

    def _plag_remove(self) -> None:
        if self.thesis is None or not self.thesis.plagiarism_pdf_filename:
            return
        confirm = QMessageBox.question(
            self,
            "Odebrat PDF",
            f'Odebrat protokol „{self.thesis.plagiarism_pdf_filename}"?\n\n'
            f"Smazat i samotný soubor ze složky?",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No
            | QMessageBox.StandardButton.Cancel,
        )
        if confirm == QMessageBox.StandardButton.Cancel:
            return
        delete_file = confirm == QMessageBox.StandardButton.Yes
        self.service.remove_plagiarism_pdf(self.thesis.id, delete_file=delete_file)
        fresh = self.service.get_thesis(self.thesis.id)
        if fresh is not None:
            self.thesis = fresh
        self._update_plagiarism_pdf_display()
        if self.tabs.currentIndex() == 0:
            self._refresh_summary()

    @staticmethod
    def _open_path_in_os(path: Path) -> None:
        import os
        import subprocess
        import sys

        target = str(path)
        if sys.platform == "darwin":
            subprocess.run(["open", target], check=False)
        elif sys.platform.startswith("linux"):
            subprocess.run(["xdg-open", target], check=False)
        elif sys.platform == "win32":
            try:
                os.startfile(target)  # type: ignore[attr-defined]
            except OSError:
                pass

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
