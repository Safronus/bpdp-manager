from __future__ import annotations

import html
import re
from datetime import date, datetime
from pathlib import Path

from ..i18n import tr

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

from PySide6.QtCore import QLocale, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QCursor, QDoubleValidator
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QTabWidget,
    QTextBrowser,
    QToolButton,
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
from ..models.enums import (
    ALLOWED_TRANSITIONS,
    STATUSES_HISTORY,
    AttachmentKind,
    PlagiarismVerdict,
    ThesisStatus,
    ThesisType,
)
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
    # Vyžádané napsání posudku — MainWindow přepošle do GenerateReviewDialog.
    # Detail panel sám dialog neumí instancovat (kruhový import), proto
    # signal a MainWindow ho odchytí.
    generate_review_requested = Signal(str)  # thesis id
    # Id zobrazené práce ("" = prázdno) — sbalitelný panel (CollapsibleDetailPane)
    # podle toho skrývá sekci detailu a po sbalení rozbalí při výběru JINÉ práce.
    content_changed = Signal(str)

    AUTOSAVE_DEBOUNCE_MS = 1500
    AUTOSAVE_SAFETY_MS = 30_000

    def __init__(
        self,
        service: ThesisService,
        year_mode: str = YEAR_MODE_ALL,
        parent=None,
        *,
        profile_manager=None,
        show_transitions: bool = True,
    ) -> None:
        super().__init__(parent)
        self.service = service
        self.profile_manager = profile_manager
        self._show_transitions = show_transitions
        self.thesis: Thesis | None = None
        self._year_mode = year_mode

        # Autosave state
        self._dirty = False
        self._loading = False  # potlačí dirty signály při programovém naplnění formuláře
        self._last_save_at: datetime | None = None
        # Poslední automaticky předvyplněný komentář plagiátorství — auto-fill
        # přepíše jen prázdné pole nebo tento dřívější auto-text (ne ruční úpravy).
        self._auto_plag_comment = ""

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

        self.placeholder = QLabel(tr("Vyberte práci v seznamu nahoře, nebo přidejte novou."))
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

        # Prominent action: napsat posudek z šablony (otevře wizard
        # s auto-filtrem dle typu + oboru práce, vyplní šablonu a po
        # potvrzení rovnou otevře v Excelu).
        self.btn_generate_review = QPushButton(tr("📝 Napsat posudek…"))
        self.btn_generate_review.setToolTip(
            tr("Vybere se šablona z knihovny (auto-filtr dle typu a oboru), "
            "vyplní se daty z této práce a otevře se v Excelu k vyplnění "
            "bodů hodnocení. Posudek se připojí jako příloha.")
        )
        self.btn_generate_review.clicked.connect(self._generate_review)
        header.addWidget(self.btn_generate_review)

        self.btn_delete = QPushButton(tr("Smazat"))
        self.btn_delete.clicked.connect(self._delete)
        header.addWidget(self.btn_delete)
        layout.addLayout(header)

        # Přechody stavů (v záložce Historie se skrývají — viz show_transitions)
        transition_box = QGroupBox(tr("Přechod do stavu"))
        tl = QHBoxLayout(transition_box)
        self.transition_buttons: dict[ThesisStatus, QPushButton] = {}
        for status in ThesisStatus:
            btn = QPushButton(status.label)
            btn.clicked.connect(lambda _=False, s=status: self._transition(s))
            tl.addWidget(btn)
            self.transition_buttons[status] = btn
        self._transition_box = transition_box
        transition_box.setVisible(self._show_transitions)
        layout.addWidget(transition_box)

        # Záložky
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self.tabs.addTab(self._build_summary_tab(), tr("📋 Souhrn"))
        self.tabs.addTab(self._build_topic_tab(), tr("📝 Téma zadání"))
        self.tabs.addTab(self._build_notes_tab(), tr("Poznámky"))
        self.tabs.addTab(self._build_plagiarism_tab(), tr("🔍 Plagiátorství"))
        self.tabs.addTab(self._build_documents_tab(), tr("📎 Dokumenty"))
        self.tabs.currentChanged.connect(self._on_tab_changed)

        # Uložit
        save_row = QHBoxLayout()
        save_row.addStretch()
        self.btn_save = QPushButton(tr("Uložit změny"))
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
        box = QGroupBox(tr("Základní info"))
        layout = QVBoxLayout(box)
        layout.setContentsMargins(8, 12, 8, 8)

        row = QHBoxLayout()
        row.setSpacing(10)

        # Typ — radio BP / DP
        row.addWidget(QLabel(tr("Typ:")))
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
        row.addWidget(QLabel(tr("Rok:")))
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
            self.cb_year.setToolTip(tr("Aktuální akademický rok — zamčeno"))
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
        row.addWidget(QLabel(tr("Student:")))
        self.cb_student = QComboBox()
        self.cb_student.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.cb_student.setMinimumWidth(180)
        _setup_searchable_combo(self.cb_student)
        if self.cb_student.lineEdit() is not None:
            self.cb_student.lineEdit().setPlaceholderText(tr("(bez studenta)"))
        self.btn_new_student = QPushButton("+")
        self.btn_new_student.setFixedWidth(28)
        self.btn_new_student.clicked.connect(self._new_student)
        row.addWidget(self.cb_student, stretch=1)
        row.addWidget(self.btn_new_student)
        row.addSpacing(12)

        # Obor studenta — editovatelný combobox z evidovaných oborů (uloží se
        # ke studentovi). Dropdown nabízí jen obory založené v manažeru, aby
        # obor seděl na sekretářku (odesílání posudků); ruční hodnota zůstane.
        row.addWidget(QLabel(tr("Obor:")))
        self.cb_thesis_obor = QComboBox()
        self.cb_thesis_obor.setEditable(True)
        self.cb_thesis_obor.setMinimumWidth(130)
        self.cb_thesis_obor.setMaximumWidth(200)
        if self.cb_thesis_obor.lineEdit() is not None:
            self.cb_thesis_obor.lineEdit().setPlaceholderText("Obor")
        self.cb_thesis_obor.setToolTip(
            tr("Obor studenta — uloží se ke studentovi. Dropdown nabízí evidované "
            "obory (manažer Obory).")
        )
        row.addWidget(self.cb_thesis_obor)
        row.addSpacing(12)

        # Oponent — totéž
        row.addWidget(QLabel(tr("Oponent:")))
        self.cb_opponent = QComboBox()
        self.cb_opponent.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.cb_opponent.setMinimumWidth(180)
        _setup_searchable_combo(self.cb_opponent)
        if self.cb_opponent.lineEdit() is not None:
            self.cb_opponent.lineEdit().setPlaceholderText(tr("(bez oponenta)"))
        self.btn_new_opponent = QPushButton("+")
        self.btn_new_opponent.setFixedWidth(28)
        self.btn_new_opponent.clicked.connect(self._new_opponent)
        row.addWidget(self.cb_opponent, stretch=1)
        row.addWidget(self.btn_new_opponent)

        layout.addLayout(row)

        # 2. řádek: STAG URL
        stag_row = QHBoxLayout()
        stag_row.setSpacing(10)
        stag_row.addWidget(QLabel("STAG:"))
        self.ed_stag_url = QLineEdit()
        self.ed_stag_url.setPlaceholderText(
            tr("odkaz na práci v IS/STAG (volitelné, např. "
            "https://stag.utb.cz/portal/studium/prohlizeni.html?…)")
        )
        stag_row.addWidget(self.ed_stag_url, stretch=1)
        layout.addLayout(stag_row)
        return box

    def _build_listing_section(self) -> QGroupBox:
        box = QGroupBox(tr("Vypsané téma (název CZ/EN, anotace CZ/EN)"))
        layout = QVBoxLayout(box)
        layout.setContentsMargins(8, 12, 8, 8)

        form = _make_form_layout()
        self.ed_title_cs = QLineEdit()
        self.ed_title_en = QLineEdit()
        form.addRow(tr("Název (CZ)"), self.ed_title_cs)
        form.addRow(tr("Název (EN)"), self.ed_title_en)
        layout.addLayout(form)

        # Anotace CZ a EN vedle sebe — šetří svislé místo
        annot_row = QHBoxLayout()
        annot_row.setSpacing(12)

        cz_col = QVBoxLayout()
        cz_col.setSpacing(2)
        lbl_cs = QLabel(tr("Anotace (CZ)"))
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
        lbl_en = QLabel(tr("Anotace (EN)"))
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
        box = QGroupBox(tr("Oficiální zadání (body zadání, literatura)"))
        layout = QVBoxLayout(box)
        layout.setContentsMargins(8, 12, 8, 8)

        lbl_obj = QLabel(
            tr("Body zadání  —  každý bod na nové řádce, číslování se přidá "
            "automaticky v Souhrnu.")
        )
        lbl_obj.setContentsMargins(8, 4, 8, 0)
        layout.addWidget(lbl_obj)
        self.ed_objectives = QPlainTextEdit()
        self.ed_objectives.setMinimumHeight(120)
        self.ed_objectives.setPlaceholderText(
            tr("Nastudujte a popište problematiku testování softwaru.\n"
            "Prozkoumejte možnosti testování pomocí umělé inteligence.\n"
            "Rozeberte vhodné nástroje AI využitelné pro testování softwaru.\n"
            "…")
        )
        self.ed_objectives.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        layout.addWidget(self.ed_objectives, stretch=1)

        lbl_ref = QLabel(
            tr("Literární zdroje  —  každá citace na nové řádce, číslování se "
            "přidá automaticky v Souhrnu.")
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
        lbl = QLabel(tr("Poznámky a deník konzultací"))
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
        lbl = QLabel(tr("Dokumenty k práci (posudky, text práce, prezentace, odkazy…)"))
        lbl.setContentsMargins(8, 4, 8, 0)
        layout.addWidget(lbl)
        self.documents_widget = DocumentsWidget(
            self.service, profile_manager=self.profile_manager
        )
        self.documents_widget.changed.connect(self._on_documents_changed)
        self.documents_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.documents_widget, stretch=1)
        return w

    def _on_documents_changed(self) -> None:
        """Po nahrání/odebrání dokumentu (typicky posudku) obnov seznam prací.

        Nahrání PDF posudku vedoucího/oponenta může doplnit známku → re-sync
        a přes ``saved`` přenačte strom (sloupce Známky V/O + Posudky).
        """
        if self._loading or self.thesis is None:
            return
        synced = self.service.sync_thesis_grades(self.thesis.id)
        if synced is not None:
            self.thesis = synced
        self._refresh_summary()
        self.saved.emit(self.thesis.id)

    def _build_plagiarism_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        # Shoda %
        perc_row = QHBoxLayout()
        perc_row.addWidget(QLabel(tr("Procento shody:")))
        self.ed_plag_pct = QLineEdit()
        self.ed_plag_pct.setPlaceholderText(tr("např. 12.3"))
        validator = QDoubleValidator(0.0, 100.0, 2, self)
        validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        # akceptuj tečku i čárku jako desetinnou
        validator.setLocale(QLocale(QLocale.Language.English))
        self.ed_plag_pct.setValidator(validator)
        self.ed_plag_pct.setFixedWidth(120)
        # Změna % obnoví auto-předvyplněný komentář (je-li verdikt zvolen).
        self.ed_plag_pct.textChanged.connect(self._maybe_autofill_plag_comment)
        perc_row.addWidget(self.ed_plag_pct)
        perc_row.addWidget(QLabel("%"))
        perc_row.addStretch()
        layout.addLayout(perc_row)

        # Verdikt — 3 radio buttony + barevný badge
        verdict_row = QHBoxLayout()
        verdict_row.addWidget(QLabel(tr("Verdikt:")))
        self.rb_verdict_na = QRadioButton(PlagiarismVerdict.NOT_ASSESSED.label)
        self.rb_verdict_pl = QRadioButton(PlagiarismVerdict.PLAGIARISM.label)
        self.rb_verdict_np = QRadioButton(PlagiarismVerdict.NOT_PLAGIARISM.label)
        self._verdict_group = QButtonGroup(self)
        self._verdict_group.addButton(self.rb_verdict_na, 0)
        self._verdict_group.addButton(self.rb_verdict_pl, 1)
        self._verdict_group.addButton(self.rb_verdict_np, 2)
        self.rb_verdict_na.setChecked(True)
        verdict_row.addWidget(self.rb_verdict_na)
        verdict_row.addWidget(self.rb_verdict_pl)
        verdict_row.addWidget(self.rb_verdict_np)
        verdict_row.addStretch()
        layout.addLayout(verdict_row)

        # Velký barevný badge ukazující aktuální verdikt
        self.lbl_verdict_badge = QLabel("")
        self.lbl_verdict_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._update_verdict_badge_style(PlagiarismVerdict.NOT_ASSESSED)
        layout.addWidget(self.lbl_verdict_badge)

        # napojení změny radio → update badge
        self._verdict_group.buttonClicked.connect(self._on_verdict_changed)

        # Komentář — label + tlačítko doporučeného komentáře
        comment_hdr = QHBoxLayout()
        lbl_c = QLabel(tr("Komentář k výsledku plagiátorství:"))
        lbl_c.setContentsMargins(0, 8, 0, 0)
        comment_hdr.addWidget(lbl_c)
        comment_hdr.addStretch()

        self.btn_plag_suggest = QToolButton()
        self.btn_plag_suggest.setText(tr("💡 Doporučený komentář"))
        self.btn_plag_suggest.setToolTip(
            tr("Vloží doporučené znění podle verdiktu a procenta shody. "
            "Lze libovolně upravit. Rozbalovací šipka nabízí konkrétní varianty.")
        )
        self.btn_plag_suggest.setPopupMode(
            QToolButton.ToolButtonPopupMode.MenuButtonPopup
        )
        # Hlavní klik = smart default dle aktuálního verdiktu + %
        self.btn_plag_suggest.clicked.connect(self._insert_suggested_plag_comment)
        # Menu s konkrétními variantami — rebuilduje se podle aktuálního %
        self._plag_suggest_menu = QMenu(self.btn_plag_suggest)
        self._plag_suggest_menu.aboutToShow.connect(self._rebuild_plag_suggest_menu)
        self.btn_plag_suggest.setMenu(self._plag_suggest_menu)
        comment_hdr.addWidget(self.btn_plag_suggest)
        layout.addLayout(comment_hdr)

        self.ed_plag_comment = QPlainTextEdit()
        self.ed_plag_comment.setPlaceholderText(
            tr("Např. „Drobné shody v citacích a standardních formulacích, žádné podezření.\"")
        )
        self.ed_plag_comment.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        layout.addWidget(self.ed_plag_comment, stretch=1)

        # PDF protokol
        pdf_lbl = QLabel(tr("PDF protokol o plagiátorství:"))
        pdf_lbl.setContentsMargins(0, 8, 0, 0)
        layout.addWidget(pdf_lbl)

        pdf_row = QHBoxLayout()
        self.lbl_plag_pdf = QLabel(tr("(žádný soubor)"))
        self.lbl_plag_pdf.setStyleSheet("color: #888;")
        pdf_row.addWidget(self.lbl_plag_pdf, stretch=1)

        self.btn_plag_upload = QPushButton(tr("📎 Vybrat PDF…"))
        self.btn_plag_upload.clicked.connect(self._plag_upload)
        pdf_row.addWidget(self.btn_plag_upload)

        self.btn_plag_open = QPushButton(tr("📂 Otevřít"))
        self.btn_plag_open.clicked.connect(self._plag_open)
        pdf_row.addWidget(self.btn_plag_open)

        self.btn_plag_remove = QPushButton(tr("🗑 Odebrat"))
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
        # Bez explicitní font-family — zdědí systémové písmo aplikace
        # (specifikování „-apple-system" Qt nezná → varování + zdržení).
        self.summary_view.setStyleSheet("QTextBrowser { padding: 12px; }")
        layout.addWidget(self.summary_view, stretch=1)
        return w

    # --- načítání / zobrazení -------------------------------------------------

    def _show_empty(self) -> None:
        self.placeholder.setVisible(True)
        self.container.setVisible(False)
        self.btn_generate_review.setEnabled(False)
        self.btn_delete.setEnabled(False)

    def _show_form(self) -> None:
        self.placeholder.setVisible(False)
        self.container.setVisible(True)
        # Posudek je relevantní jen pro aktivní (V řešení) práce.
        # Pro Budoucí (vypsané/zájemce) ani Historie (obhájeno/nedokončeno)
        # nemá smysl psát posudek — výjimky řeší přechod stavu.
        self.btn_generate_review.setEnabled(
            self.thesis is not None
            and self.thesis.status == ThesisStatus.IN_PROGRESS
        )
        self._update_review_button_tooltip()
        self.btn_delete.setEnabled(True)

    def _update_review_button_tooltip(self) -> None:
        if self.thesis is None:
            return
        if self.thesis.status == ThesisStatus.IN_PROGRESS:
            self.btn_generate_review.setToolTip(
                tr("Otevře editor posudku (auto-filtr šablon dle typu a oboru), "
                "vyplní body hodnocení a vygeneruje XLSX + PDF jako přílohu.")
            )
        else:
            self.btn_generate_review.setToolTip(
                tr('Posudek lze psát jen pro práci ve stavu „V řešení".')
                + " " + tr("Aktuálně:") + " " + self.thesis.status.label
            )

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

            # Obor (dropdown evidovaných oborů; text se zachová)
            obor_text = self.cb_thesis_obor.currentText()
            self.cb_thesis_obor.clear()
            self.cb_thesis_obor.addItem("")
            for o in self.service.list_obor_objects():
                self.cb_thesis_obor.addItem(o.name)
            self.cb_thesis_obor.setCurrentText(obor_text)
        finally:
            self._loading = was_loading

    def _sync_thesis_obor_combo(self) -> None:
        """Nastaví obor combobox podle oboru aktuálně vybraného studenta."""
        student_id = self._resolve_combo_id(self.cb_student)
        student = self.service.get_student(student_id) if student_id else None
        was_loading = self._loading
        self._loading = True
        try:
            self.cb_thesis_obor.setCurrentText((student.obor if student else "") or "")
        finally:
            self._loading = was_loading

    def _on_student_changed(self) -> None:
        """Po RUČNÍ změně studenta sjednoť obor combobox s jeho oborem."""
        if not self._loading:
            self._sync_thesis_obor_combo()

    def set_thesis(self, thesis: Thesis | None) -> None:
        # Před přepnutím flushni rozpracované změny aktuální práce
        if self._dirty and self.thesis is not None:
            self._autosave()

        self.thesis = thesis
        if thesis is None:
            self._show_empty()
            self._update_save_state_label(idle=True)
            self.content_changed.emit("")
            return
        # Doplň chybějící známky i zpětně (z in-app posudku / nahraného PDF) —
        # užitečné u historických prací s posudkem jen jako PDF.
        synced = self.service.sync_thesis_grades(thesis.id)
        if synced is not None:
            self.thesis = thesis = synced
        self._show_form()
        self.content_changed.emit(thesis.id)

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
            self._sync_thesis_obor_combo()
            self.ed_stag_url.setText(thesis.stag_url or "")

            self.ed_title_cs.setText(thesis.title_cs)
            self.ed_annotation.setPlainText(thesis.annotation)
            self.ed_annotation_en.setPlainText(thesis.annotation_en or "")
            self.ed_title_en.setText(thesis.title_en)
            self.ed_objectives.setPlainText(thesis.objectives or "")
            self.ed_references.setPlainText(thesis.references or "")
            self.ed_notes.setPlainText(thesis.notes)

            # Plagiátorství
            if thesis.plagiarism_similarity_pct is None:
                self.ed_plag_pct.clear()
            else:
                # zobrazujeme s odstraněním nul (např. 15.0 → "15", 15.3 → "15.3")
                pct = thesis.plagiarism_similarity_pct
                self.ed_plag_pct.setText(
                    f"{pct:g}".replace(",", ".")
                )
            self.ed_plag_comment.setPlainText(thesis.plagiarism_comment or "")
            # Uložený komentář ber jako uživatelův text → auto-fill ho nepřepíše,
            # dokud uživatel nezvolí verdikt nad prázdným polem.
            self._auto_plag_comment = ""
            self._set_verdict_radio(thesis.plagiarism_verdict)
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
        # Panel přechodů má smysl jen u rozpracovaných prací (aktuální/budoucí).
        # U historických (obhájeno/neobhájeno/nedokončeno) ho skryjeme — i v
        # záložce „Vše". Tab Historie ho navíc vypíná natvrdo (_show_transitions).
        visible = self._show_transitions and self.thesis.status not in STATUSES_HISTORY
        self._transition_box.setVisible(visible)
        allowed = ALLOWED_TRANSITIONS.get(self.thesis.status, set())
        for status, btn in self.transition_buttons.items():
            btn.setEnabled(status in allowed and status != self.thesis.status)

    # --- autosave ------------------------------------------------------------

    def _connect_dirty_signals(self) -> None:
        """Napojí změny všech polí na ``_mark_dirty``."""
        self.rb_bp.toggled.connect(self._mark_dirty)
        self.rb_dp.toggled.connect(self._mark_dirty)
        self.cb_year.currentTextChanged.connect(self._mark_dirty)
        self.ed_stag_url.textChanged.connect(self._mark_dirty)
        self.ed_plag_pct.textChanged.connect(self._mark_dirty)
        self.ed_plag_comment.textChanged.connect(self._mark_dirty)
        self.rb_verdict_na.toggled.connect(self._mark_dirty)
        self.rb_verdict_pl.toggled.connect(self._mark_dirty)
        self.rb_verdict_np.toggled.connect(self._mark_dirty)
        self.cb_student.currentIndexChanged.connect(self._mark_dirty)
        self.cb_student.currentIndexChanged.connect(self._on_student_changed)
        self.cb_opponent.currentIndexChanged.connect(self._mark_dirty)
        self.cb_thesis_obor.currentTextChanged.connect(self._mark_dirty)
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
            self.lbl_save_state.setText(tr("⚠ Chyba ukládání:") + f" {error}")
            self.lbl_save_state.setStyleSheet("color: #c62828; font-size: 11px;")
            return
        if pending:
            self.lbl_save_state.setText(tr("● Ukládám…"))
            self.lbl_save_state.setStyleSheet("color: #ef6c00; font-size: 11px;")
            return
        # po úspěšném autosavu
        ts = self._last_save_at.strftime("%H:%M:%S") if self._last_save_at else ""
        self.lbl_save_state.setText(tr("✓ Uloženo") + f" {ts}")
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
                + tr("Vyberte práci v seznamu nahoře, nebo přidejte novou.")
                + "</p>"
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
        stag_url = (thesis.stag_url or "").strip()
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
                f'<h3 style="{section_header_style}">{tr("Anotace (EN)")}:'
                f"{cp('annotation_en', 'Zkopírovat anotaci EN')}</h3>"
                f"{anot_en_html}"
            )

        # ── Plagiátorství (jen pokud něco vyplněno) ────────────────────────
        plag_section = ""
        has_plag_pct = thesis.plagiarism_similarity_pct is not None
        has_plag_comment = bool((thesis.plagiarism_comment or "").strip())
        has_plag_pdf = bool(thesis.plagiarism_pdf_filename)
        has_plag_verdict = thesis.plagiarism_verdict != PlagiarismVerdict.NOT_ASSESSED
        if has_plag_pct or has_plag_comment or has_plag_pdf or has_plag_verdict:
            verdict = thesis.plagiarism_verdict
            verdict_badge = (
                f'<span style="background-color:{verdict.color};color:white;'
                f"padding:3px 10px;border-radius:5px;font-weight:bold;"
                f'letter-spacing:0.5px;">{e(verdict.label.upper())}</span>'
            )
            pct_str = (
                f"{thesis.plagiarism_similarity_pct:g} %"
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
                f'<h3 style="{section_header_style}">{tr("🔍 Plagiátorství")}:</h3>'
                f"<p><b>Verdikt:</b> {verdict_badge}</p>"
                f"<p><b>Shoda:</b> {pct_str}"
                f"{cp('plag_pct', 'Zkopírovat procento shody') if has_plag_pct else ''}</p>"
                f"<p><b>Komentář:</b> {comment_html}"
                f"{cp('plag_comment', 'Zkopírovat komentář k plagiátorství') if has_plag_comment else ''}</p>"
                f"<p><b>PDF protokol:</b> {pdf_html}</p>"
            )

        # ── Známky + Posudky (strukturovaná data) ──────────────────────────
        grades_section = self._build_grades_summary_html(thesis, e, section_header_style)
        reviews_section = self._build_reviews_summary_html(thesis, e, section_header_style)
        sent_section = self._build_sent_summary_html(thesis, e, section_header_style)
        documents_section = self._build_documents_summary_html(
            thesis, e, section_header_style
        )

        # ── STAG link ──────────────────────────────────────────────────────
        stag_html = ""
        if stag_url:
            stag_html = (
                f'<p style="margin:6px 0 12px 0;color:#666;">'
                f'<b>🔗 STAG:</b> '
                f'<a href="{e(stag_url)}" style="color:#1976d2;">{e(stag_url)}</a>'
                f"{cp('stag_url', 'Zkopírovat STAG URL')}"
                f"</p>"
            )

        # Repetent — vazba na druhý pokus.
        retake_html = ""
        if thesis.related_thesis_id:
            other = self.service.get_thesis(thesis.related_thesis_id)
            if other is not None:
                other_title = e(other.display_title)
                other_status = e(other.status.label)
                retake_html = (
                    "<p style='background:#fff3e0;color:#5d4037;padding:6px 10px;"
                    "border-radius:4px;border:1px solid #ffb74d;'>"
                    f"🔁 <b>Repetent:</b> souvisí s prací „{other_title}“ "
                    f"({other_status}) — řádný + opravný pokus.</p>"
                )

        return (
            "<html><body>"
            f"{status_bar}"
            f"{readiness_html}"
            f"{retake_html}"
            f"{header_line}"
            f"{en_line}"
            f"{stag_html}"
            f'<h3 style="{section_header_style}">{tr("Anotace")}:'
            f"{cp('annotation', 'Zkopírovat anotaci')}</h3>"
            f"{anot_html}"
            f"{anot_en_section}"
            f'<h3 style="{section_header_style}">{tr("Body zadání")}:'
            f"{cp('objectives', 'Zkopírovat body zadání')}</h3>"
            f"{obj_html}"
            f'<h3 style="{section_header_style}">{tr("Literární zdroje")}:'
            f"{cp('references', 'Zkopírovat literární zdroje')}</h3>"
            f"{ref_html}"
            f"{plag_section}"
            f"{grades_section}"
            f"{reviews_section}"
            f"{sent_section}"
            f"{documents_section}"
            "</body></html>"
        )

    _GRADE_COLORS = {
        "A": "#2e7d32", "B": "#43a047", "C": "#fb8c00",
        "D": "#f57c00", "E": "#e65100", "F": "#c62828", "FX": "#c62828",
    }

    @classmethod
    def _grade_badge_cell(cls, label: str, value: str, e) -> str:
        """Vycentrovaná buňka se známkou (label nad barevným badge)."""
        color = cls._GRADE_COLORS.get((value or "").upper(), "#9e9e9e")
        disp = e(value) if value else "—"
        return (
            '<td style="padding:0 24px;text-align:center;vertical-align:top;">'
            f'<div style="color:#666;font-size:10pt;text-align:center;">{e(label)}</div>'
            f'<div style="background-color:{color};color:white;font-weight:bold;'
            'font-size:18pt;padding:6px 16px;border-radius:6px;'
            f'display:inline-block;text-align:center;min-width:28px;">{disp}</div>'
            "</td>"
        )

    def _build_sent_summary_html(self, thesis, e, section_header_style: str) -> str:
        """Indikace, zda byl posudek vedoucího odeslán sekretářce.

        U **historických** prací (obhájeno / nedokončeno) je odeslání posudku
        sekretářce už irelevantní — sekci proto vůbec neukazujeme, i kdyby
        práce dřív byla „V řešení".
        """
        if thesis.status in STATUSES_HISTORY:
            return ""
        has_review = any(
            a.kind == AttachmentKind.SUPERVISOR_REVIEW for a in thesis.attachments
        ) or any(r.role == "supervisor" for r in thesis.reviews)
        sent = thesis.supervisor_review_sent_at
        if not has_review and not sent:
            return ""
        if sent:
            body = (
                '<span style="color:#2e7d32;">✓ odesláno '
                f'{e(sent.strftime("%d.%m.%Y"))}</span>'
            )
        else:
            body = '<span style="color:#c62828;">✗ neodesláno</span>'
        return (
            f'<h3 style="{section_header_style}">Odeslání posudku</h3>'
            f"<p>📨 Posudek vedoucího sekretářce: {body}</p>"
        )

    def _build_documents_summary_html(self, thesis, e, section_header_style: str) -> str:
        """Souhrn souborů (aktuální přílohy) — u aktuálních i historických prací."""
        atts = [a for a in thesis.attachments if a.is_current]
        if not atts:
            return ""
        rows = ""
        for att in sorted(atts, key=lambda a: a.kind.label):
            icon = "📄 " if att.is_file else "🔗 "
            rows += (
                "<tr>"
                f"<td style='padding:3px 14px 3px 0;'><b>{e(att.kind.label)}</b></td>"
                f"<td style='padding:3px 0;'>{icon}{e(att.label)}</td>"
                "</tr>"
            )
        return (
            f'<h3 style="{section_header_style}">Soubory:</h3>'
            f"<table>{rows}</table>"
        )

    def _build_grades_summary_html(self, thesis, e, section_header_style: str) -> str:
        """Známky (navržené z posudků) — vedoucí + oponent, nad sekcí Posudky.

        Přednost má in-app posudek (``Review.suggested_grade``); pokud chybí,
        použije se známka vyčtená z nahraného PDF (``thesis.grade_*``, plní
        ``sync_thesis_grades``) — typicky u historických prací.
        """
        reviews = [r for r in thesis.reviews if r.is_current]
        sup = next((r for r in reviews if r.role == "supervisor"), None)
        opp = next((r for r in reviews if r.role == "opponent"), None)
        sup_grade = sup.suggested_grade if sup else (thesis.grade_supervisor or "")
        opp_grade = opp.suggested_grade if opp else (thesis.grade_opponent or "")
        if not sup_grade and not opp_grade:
            return ""
        table = (
            "<table style='margin:12px auto;'><tr>"
            + self._grade_badge_cell("Vedoucí:", sup_grade, e)
            + self._grade_badge_cell(tr("Oponent:"), opp_grade, e)
            + "</tr></table>"
        )
        return f'<h3 style="{section_header_style}">Známky</h3>{table}'

    def _build_reviews_summary_html(self, thesis, e, section_header_style: str) -> str:
        """Náhled uložených posudků (current verze) pro Souhrn tab."""
        reviews = [r for r in thesis.reviews if r.is_current]
        if not reviews:
            return ""
        # Vedoucí první, pak oponent
        reviews.sort(key=lambda r: 0 if r.role == "supervisor" else 1)

        blocks: list[str] = []
        for r in reviews:
            role_label = "🎓 Posudek vedoucího" if r.role == "supervisor" else "🧐 Posudek oponenta"
            grade = r.suggested_grade
            grade_color = {
                "A": "#2e7d32", "B": "#43a047", "C": "#fb8c00",
                "D": "#f57c00", "E": "#e65100", "F": "#c62828", "FX": "#c62828",
            }.get(grade, "#666")
            grade_badge = (
                f'<span style="background-color:{grade_color};color:white;'
                f'padding:2px 10px;border-radius:8px;font-weight:bold;">{e(grade)}</span>'
            )
            # Kritéria — kompaktní seznam
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
                f"známka {grade_badge}</p>"
                f"{crit_table}"
                f"<p style='margin:4px 0 0 0;'><b>Hodnocení:</b> {comment_html}</p>"
                f"<p style='margin:2px 0 0 0;color:#888;font-size:11px;'>"
                f"{files_str} &nbsp;·&nbsp; {e(r.place_date)}</p>"
                f"</div>"
            )

        return (
            f'<h3 style="{section_header_style}">📝 Posudky:</h3>'
            + "".join(blocks)
        )

    def _on_summary_anchor_clicked(self, url: QUrl) -> None:
        """Click v Souhrnu — buď 'copy:<field>' (clipboard), nebo http(s) URL (otevřít)."""
        s = url.toString()
        if s.startswith("copy:"):
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
            return

        # http/https/file/mailto → otevřít systémovým prohlížečem
        if url.scheme() in ("http", "https", "file", "mailto"):
            from PySide6.QtGui import QDesktopServices
            QDesktopServices.openUrl(url)

    def _summary_field_value(self, field: str) -> tuple[str | None, str]:
        """Vrátí (text-do-schránky, popisek-pro-tooltip) pro daný field."""
        t = self.thesis
        if t is None:
            return None, ""
        if field == "title_cs":
            return t.title_cs or "", "název (CZ)"
        if field == "title_en":
            return t.title_en or "", "název (EN)"
        if field == "stag_url":
            return t.stag_url or "", "STAG URL"
        if field == "annotation":
            return t.annotation or "", "anotace"
        if field == "annotation_en":
            return t.annotation_en or "", "anotace (EN)"
        if field == "objectives":
            return _format_numbered(t.objectives), "body zadání"
        if field == "references":
            return _format_numbered(t.references), "literární zdroje"
        if field == "plag_pct":
            if t.plagiarism_similarity_pct is None:
                return "", "shoda plagiátorství"
            return f"{t.plagiarism_similarity_pct:g} %", "shoda plagiátorství"
        if field == "plag_comment":
            return t.plagiarism_comment or "", "komentář k plagiátorství"
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
        self.thesis.stag_url = self.ed_stag_url.text().strip()
        self.thesis.student_id = self._resolve_combo_id(self.cb_student)
        self.thesis.opponent_id = self._resolve_combo_id(self.cb_opponent)

        # Obor patří studentovi — ulož ho k aktuálně vybranému studentovi.
        if self.thesis.student_id:
            obor_text = self.cb_thesis_obor.currentText().strip()
            student = self.service.get_student(self.thesis.student_id)
            if student is not None and (student.obor or "") != obor_text:
                student.obor = obor_text
                self.service.upsert_student(student)
        self.thesis.title_cs = self.ed_title_cs.text().strip()
        self.thesis.annotation = self.ed_annotation.toPlainText().strip()
        self.thesis.annotation_en = self.ed_annotation_en.toPlainText().strip()
        self.thesis.title_en = self.ed_title_en.text().strip()
        self.thesis.objectives = self.ed_objectives.toPlainText()
        self.thesis.references = self.ed_references.toPlainText()
        self.thesis.notes = self.ed_notes.toPlainText().strip()

        # Plagiátorství — text z QLineEdit s validatorem
        raw = self.ed_plag_pct.text().strip().replace(",", ".").replace("%", "").strip()
        if not raw:
            self.thesis.plagiarism_similarity_pct = None
        else:
            try:
                self.thesis.plagiarism_similarity_pct = float(raw)
            except ValueError:
                self.thesis.plagiarism_similarity_pct = None
        self.thesis.plagiarism_comment = self.ed_plag_comment.toPlainText().strip()
        self.thesis.plagiarism_verdict = self._current_verdict()
        # attachments spravuje DocumentsWidget okamžitě skrz service,
        # zde je proto nepřepisujeme — jen znovu načteme aktuální stav.
        fresh = self.service.get_thesis(self.thesis.id)
        if fresh is not None:
            self.thesis.attachments = fresh.attachments

    # --- plagiátorství akce -------------------------------------------------

    def _current_verdict(self) -> PlagiarismVerdict:
        if self.rb_verdict_pl.isChecked():
            return PlagiarismVerdict.PLAGIARISM
        if self.rb_verdict_np.isChecked():
            return PlagiarismVerdict.NOT_PLAGIARISM
        return PlagiarismVerdict.NOT_ASSESSED

    def _set_verdict_radio(self, verdict: PlagiarismVerdict) -> None:
        if verdict == PlagiarismVerdict.PLAGIARISM:
            self.rb_verdict_pl.setChecked(True)
        elif verdict == PlagiarismVerdict.NOT_PLAGIARISM:
            self.rb_verdict_np.setChecked(True)
        else:
            self.rb_verdict_na.setChecked(True)
        self._update_verdict_badge_style(verdict)

    def _update_verdict_badge_style(self, verdict: PlagiarismVerdict) -> None:
        self.lbl_verdict_badge.setText(verdict.label.upper())
        self.lbl_verdict_badge.setStyleSheet(
            f"QLabel {{ background-color: {verdict.color}; color: white; "
            f"font-weight: bold; padding: 8px 14px; border-radius: 6px; "
            f"font-size: 13pt; letter-spacing: 0.5px; }}"
        )

    def _on_verdict_changed(self, *_args) -> None:
        self._update_verdict_badge_style(self._current_verdict())
        # Po ručním kliknutí na verdikt rovnou předvyplň komentář.
        self._maybe_autofill_plag_comment()

    def _maybe_autofill_plag_comment(self) -> None:
        """Automaticky předvyplní komentář dle verdiktu + %.

        Spustí se po zvolení verdiktu i po změně procenta shody. Přepíše jen
        **prázdné** pole nebo **dříve auto-vygenerovaný** text — ruční úpravy
        uživatele zůstanou zachované.
        """
        if self._loading:
            return
        verdict = self._current_verdict()
        if verdict == PlagiarismVerdict.NOT_ASSESSED:
            return
        from ..services.plagiarism_comments import suggest_comment

        text = suggest_comment(verdict, self._plag_pct_value())
        if not text:
            return
        current = self.ed_plag_comment.toPlainText().strip()
        if current and current != self._auto_plag_comment.strip():
            return  # uživatel si komentář upravil → nepřepisuj
        self._auto_plag_comment = text
        self.ed_plag_comment.setPlainText(text)

    def _plag_pct_value(self) -> float | None:
        """Aktuální procento shody z pole (None pokud prázdné/neplatné)."""
        txt = self.ed_plag_pct.text().strip().replace(",", ".")
        if not txt:
            return None
        try:
            return float(txt)
        except ValueError:
            return None

    def _insert_suggested_plag_comment(self) -> None:
        """Smart default — vloží doporučený komentář dle verdiktu + %."""
        from ..services.plagiarism_comments import suggest_comment

        verdict = self._current_verdict()
        if verdict == PlagiarismVerdict.NOT_ASSESSED:
            QMessageBox.information(
                self,
                tr("Doporučený komentář"),
                tr("Nejdřív zvol verdikt (Posouzen — je / není plagiát). "
                "Pro „Neposouzen\" se komentář negeneruje."),
            )
            return
        text = suggest_comment(verdict, self._plag_pct_value())
        self._apply_plag_comment(text)

    def _rebuild_plag_suggest_menu(self) -> None:
        """Naplní menu konkrétními variantami komentáře (s aktuálním %)."""
        from ..services.plagiarism_comments import comment_variants

        self._plag_suggest_menu.clear()
        for label, text in comment_variants(self._plag_pct_value()):
            act = self._plag_suggest_menu.addAction(label)
            act.triggered.connect(
                lambda _checked=False, t=text: self._apply_plag_comment(t)
            )

    def _apply_plag_comment(self, text: str) -> None:
        """Vloží text do komentáře. Pokud už něco je, zeptá se na přepis."""
        current = self.ed_plag_comment.toPlainText().strip()
        if current and current != text:
            confirm = QMessageBox.question(
                self,
                tr("Přepsat komentář"),
                tr("Komentář už obsahuje text. Přepsat doporučeným zněním?"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if confirm != QMessageBox.StandardButton.Yes:
                return
        self._auto_plag_comment = text  # ber jako auto-text (verdikt/% ho smí obnovit)
        self.ed_plag_comment.setPlainText(text)

    def _update_plagiarism_pdf_display(self) -> None:
        """Aktualizuje label a stav tlačítek podle stavu PDF."""
        has_pdf = bool(
            self.thesis and self.thesis.plagiarism_pdf_filename
        )
        if has_pdf:
            self.lbl_plag_pdf.setText(f"📄 {self.thesis.plagiarism_pdf_filename}")
            self.lbl_plag_pdf.setStyleSheet("")
        else:
            self.lbl_plag_pdf.setText(tr("(žádný soubor)"))
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
                self, tr("Chyba"), f"Nepodařilo se uložit PDF:\n{exc}"
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
                self, tr("Otevřít PDF"), tr("Žádné PDF není nahrané.")
            )
            return
        self._open_path_in_os(path)

    def _plag_remove(self) -> None:
        if self.thesis is None or not self.thesis.plagiarism_pdf_filename:
            return
        confirm = QMessageBox.question(
            self,
            tr("Odebrat PDF"),
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
            tr("Smazat práci"),
            f"Opravdu smazat „{self.thesis.display_title}“?\nTuto akci nelze vrátit.",
        )
        if confirm == QMessageBox.StandardButton.Yes:
            tid = self.thesis.id
            self.service.delete_thesis(tid)
            self.set_thesis(None)
            self.deleted.emit(tid)

    def _generate_review(self) -> None:
        """Klik na „📝 Napsat posudek…" → emit signal, MainWindow otevře dialog."""
        if self.thesis is None:
            return
        # Flushni pending změny (autosave debounce), aby šablona dostala
        # aktuální data (např. čerstvě zadaný titul EN).
        self.flush()
        self.generate_review_requested.emit(self.thesis.id)

    def _transition(self, target: ThesisStatus) -> None:
        if self.thesis is None:
            return
        self._collect_into_thesis()
        self.service.upsert_thesis(self.thesis)
        try:
            self.service.transition(self.thesis.id, target)
        except TransitionError as exc:
            QMessageBox.warning(self, tr("Přechod stavu"), str(exc))
            return
        self.set_thesis(self.service.get_thesis(self.thesis.id))
        self.saved.emit(self.thesis.id)
