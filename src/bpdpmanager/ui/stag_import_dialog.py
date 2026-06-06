"""STAG import dialog — načtení CSV, náhled, mapování oborů, provedení importu.

Workflow:
1) File picker + tvoje jméno → detekuje per-řádek roli
2) Náhled tabulky — sloupce Role / Student / Téma / Obor / Stav / Akce
3) Per-řádek volby (role override, obor mapping, status, akce)
4) Před spuštěním automatická záloha
5) Provedení importu — vytvoří/aktualizuje práce, studenty, vedoucí, oponenty
"""

from __future__ import annotations

import re
import tempfile
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QBrush, QColor, QFont
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from ..models import (
    Obor,
    Opponent,
    OpposingThesis,
    Student,
    Supervisor,
    Thesis,
)
from ..models.enums import AttachmentKind, OpponentKind, ThesisStatus, ThesisType
from ..services import BackupManager, ProfileManager, ThesisService, stag_api
from ..services.stag_csv_importer import (
    ImportFile,
    ImportRole,
    ParsedRecord,
    load_stag_csv,
)
from .obor_dialog import OborDialog

# Per-row akce
ACTION_CREATE = "create"
ACTION_UPDATE = "update"
ACTION_SKIP = "skip"

# Mapování STAG sekce (viz stag_api.StagFile.section) → typ přílohy v DB.
_SECTION_TO_KIND: dict[str, AttachmentKind] = {
    "text": AttachmentKind.THESIS_TEXT,
    "appendix": AttachmentKind.THESIS_APPENDIX,
    "supervisor_review": AttachmentKind.SUPERVISOR_REVIEW,
    "opponent_review": AttachmentKind.OPPONENT_REVIEW,
    "other": AttachmentKind.OTHER,
}

# Typy příloh nabízené v náhledu stažených souborů (v pořadí rozbalovače).
_FILE_KIND_CHOICES: list[AttachmentKind] = [
    AttachmentKind.THESIS_TEXT,
    AttachmentKind.THESIS_APPENDIX,
    AttachmentKind.SUPERVISOR_REVIEW,
    AttachmentKind.OPPONENT_REVIEW,
    AttachmentKind.OTHER,
]


@dataclass
class _DownloadedStagFile:
    """Soubor stažený ze STAG do dočasného úložiště — čeká na import do práce."""

    path: Path                 # dočasná lokální cesta
    filename: str              # původní název ze STAG
    kind: AttachmentKind       # typ přílohy (předvyplněn ze sekce, lze přepsat)
    section: str = "other"     # původní STAG sekce
    size: int = 0              # velikost v bajtech
    selected: bool = True      # zda importovat (náhled umožní odznačit)


def _fold(s: str) -> str:
    """Lowercase + bez diakritiky (pro porovnání jmen napříč diakritikou)."""
    s = unicodedata.normalize("NFKD", s or "")
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def _name_matches(person_field: str, full_name: str) -> bool:
    """True, pokud ``person_field`` (jméno z STAG) odpovídá celému jménu uživatele.

    Filtruje „past" se jmenovci — ze samotného příjmení může být víc vedoucích
    (Petr vs Pavel Žáček). Vyžaduje výskyt **křestního i příjmení**. Pokud nemáme
    celé jméno (jen jeden token), nefiltruje (vrací True).
    """
    tokens = [t.strip(".,") for t in (full_name or "").replace(",", " ").split() if t.strip(".,")]
    if len(tokens) < 2:
        return True
    field = _fold(person_field)
    return _fold(tokens[0]) in field and _fold(tokens[-1]) in field


def _fmt_size(n: int) -> str:
    """Lidsky čitelná velikost souboru."""
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n / 1024:.0f} KB"
    return f"{n / (1024 * 1024):.1f} MB"


# Práh pro varování u velkých příloh (desítky MB) — nad ním se uživatel
# před stažením dotáže, jestli je chce stáhnout.
_LARGE_FILE_BYTES = 25 * 1024 * 1024  # 25 MB

# STAG kódy stavu práce (sloupec ``stavPrace``) → náš ``ThesisStatus``.
# Zdroj: konzultace s uživatelem (FAI UTB STAG export).
#
#   R     - Rozpracovaná                              → V řešení
#   DBPOO - Dokončená bez pokusu o obhajobu           → V řešení
#   DUO   - Dokončená s úspěšnou obhajobou            → Obhájeno
#   DBUO  - Dokončená s neúspěšnou obhajobou          → Nedokončeno
#   ND    - Nedokončená práce                         → Nedokončeno
#
# Pozn.: DBUO a ND mají v našem schématu společný stav (CANCELLED =
# „Nedokončeno"). Nuance „failed defense" vs „abandoned work" lze
# dohledat v poli ``stag_state_code`` u Thesis (zachovává se z importu).
STAG_STATE_TO_STATUS: dict[str, ThesisStatus] = {
    "R": ThesisStatus.IN_PROGRESS,
    "DBPOO": ThesisStatus.IN_PROGRESS,
    "DUO": ThesisStatus.DEFENDED,
    "DBUO": ThesisStatus.CANCELLED,
    "OPUNO": ThesisStatus.CANCELLED,  # odevzdaná, ukončená po neúspěšné obhajobě
    "ND": ThesisStatus.CANCELLED,
}

# Lidsky čitelná jména STAG kódů pro tooltip.
STAG_STATE_LABELS: dict[str, str] = {
    "R": "Rozpracovaná",
    "DBPOO": "Dokončená bez pokusu o obhajobu",
    "DUO": "Dokončená s úspěšnou obhajobou",
    "DBUO": "Dokončená, neúspěšná obhajoba",
    "OPUNO": "Odevzdaná, ukončená po neúspěšné obhajobě",
    "ND": "Nedokončená práce",
}


class _ImportHadErrors(Exception):
    """Vnitřní sentinel pro vyhození batche když nastaly per-řádkové chyby.

    Důvod: rozhodnutí o rollback/keep dělá uživatel po batchi, ale
    batch už mezitím musí být zrušen (data ještě nepersistována).
    """

    def __init__(self, errors: list[str]) -> None:
        super().__init__(f"{len(errors)} chyb při importu")
        self.errors = errors


class StagImportDialog(QDialog):
    def __init__(
        self,
        service: ThesisService,
        profile_manager: ProfileManager | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.service = service
        self.profile_manager = profile_manager
        self.import_file: ImportFile | None = None
        # Metadata z přímého stažení ze STAG (jméno studenta apod.) — veřejný
        # CSV export STAG totiž jméno studenta NEOBSAHUJE (jen osobní číslo),
        # doplníme ho proto z výsledku vyhledávání. Spotřebuje ho _load_preview.
        self._pending_stag_meta: stag_api.StagThesisResult | None = None
        # Studenti zkontrolovaní/doplnění uživatelem před importem (klíč =
        # osobní číslo). Použije je _ensure_student místo holého auto-založení.
        self._reviewed_students: dict[str, Student] = {}
        self.row_widgets: list[dict] = []  # každý řádek má { role, obor, status, action }
        # Po úspěšném importu MainWindow přečte tyto atributy a přepne se na
        # příslušnou práci v UI (Aktuální / Budoucí / Historie nebo Oponentury).
        self.imported_thesis_ids: list[str] = []
        self.imported_opposing_ids: list[str] = []
        self.focus_thesis_id: str | None = None      # poslední vytvořená/aktualizovaná vedená
        self.focus_opposing_id: str | None = None    # poslední vytvořený/aktualizovaný posudek
        # Záchranná brzda — záloha před importem (umožní celý import vrátit).
        self._preimport_backup_file: str | None = None
        self._preimport_data_dir: Path | None = None
        self.reverted = False  # MainWindow přečte: pokud True, import byl vrácen
        # Soubory stažené ze STAG spolu s prací (klíč = adipIdno). Importér je
        # po založení práce připojí k té správné (přes adipIdno).
        self._stag_downloaded_files: dict[str, list[_DownloadedStagFile]] = {}

        self.setWindowTitle("Import dat ze STAG CSV")
        self.setMinimumSize(1240, 820)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 14, 14, 14)
        outer.setSpacing(10)

        # ── Hlavička ────────────────────────────────────────────────────────
        title = QLabel("📥 Import dat ze STAG CSV")
        title.setStyleSheet("font-size:16px;font-weight:bold;")
        outer.addWidget(title)

        # ── Formulář s parametry ────────────────────────────────────────────
        form = QFormLayout()
        self.ed_path = QLineEdit()
        self.ed_path.setPlaceholderText("vyber CSV soubor exportovaný ze STAG")
        btn_browse = QPushButton("Procházet…")
        btn_browse.clicked.connect(self._browse)
        btn_stag_dl = QPushButton("🌐 Stáhnout ze STAG")
        btn_stag_dl.setToolTip(
            "Najdi a stáhni CSV s prací přímo ze STAG podle příjmení "
            "studenta a vedoucího/oponenta (bez přihlášení)."
        )
        btn_stag_dl.clicked.connect(self._open_stag_download)
        btn_csv_help = QPushButton("❓ Odkud stáhnout")
        btn_csv_help.setToolTip("Jak získat CSV s prací ze STAG")
        btn_csv_help.clicked.connect(self._show_csv_download_help)
        row_path = QHBoxLayout()
        row_path.addWidget(self.ed_path, stretch=1)
        row_path.addWidget(btn_browse)
        row_path.addWidget(btn_stag_dl)
        row_path.addWidget(btn_csv_help)
        form.addRow("CSV soubor", row_path)

        # Hromadné stažení všech mých prací ze STAG (napříč roky).
        btn_my_led = QPushButton("🎓 Moje vedené práce…")
        btn_my_led.setToolTip(
            "Najde ve STAG všechny práce, kde jsi vedoucí (historické, aktuální "
            "i vypsané) — podle tvého jména z profilu. Vybereš, co naimportovat."
        )
        btn_my_led.clicked.connect(lambda: self._open_stag_download(auto_role="supervisor"))
        btn_my_opp = QPushButton("🧐 Moje oponentury…")
        btn_my_opp.setToolTip(
            "Najde ve STAG všechny práce, kde jsi oponent — podle tvého jména "
            "z profilu. Vybereš, co naimportovat."
        )
        btn_my_opp.clicked.connect(lambda: self._open_stag_download(auto_role="opponent"))
        row_bulk = QHBoxLayout()
        row_bulk.addWidget(btn_my_led)
        row_bulk.addWidget(btn_my_opp)
        row_bulk.addStretch()
        form.addRow("Hromadně ze STAG", row_bulk)

        # Tvoje jméno (pro detekci role)
        default_user_name = ""
        if profile_manager and profile_manager.active:
            default_user_name = profile_manager.active.user_name or ""
        self.ed_user_name = QLineEdit(default_user_name)
        self.ed_user_name.setPlaceholderText("např. Petr Žáček")
        form.addRow("Tvoje jméno", self.ed_user_name)
        help_lbl = QLabel(
            "<small><i>Použije se k auto-detekci role: pokud se najde "
            "v `vedouciJmeno` → ‚Vedu‘, v `oponentJmeno` → ‚Oponuji‘. "
            "Per řádek lze přepsat v náhledu.</i></small>"
        )
        help_lbl.setStyleSheet("color:#888;")
        help_lbl.setTextFormat(Qt.TextFormat.RichText)
        form.addRow("", help_lbl)

        # Fallback stav (použije se jen když CSV nemá žádné z datumů
        # zadání/odevzdání/obhajoby — typicky čerstvý zájem). Skutečný
        # stav per řádek určí heuristika z dat CSV (datumObhajoby →
        # Obhájeno, datumOdevzdani → V řešení, datumZadani → Schválené),
        # ale uživatel ho samozřejmě může v náhledu přepsat.
        self.cb_default_status = QComboBox()
        for st in ThesisStatus:
            self.cb_default_status.addItem(st.label, st.value)
        idx = self.cb_default_status.findData(ThesisStatus.IN_PROGRESS.value)
        if idx >= 0:
            self.cb_default_status.setCurrentIndex(idx)
        form.addRow("Fallback stav (vedené práce)", self.cb_default_status)
        status_help = QLabel(
            "<small><i>Použije se jen pro řádky, kde CSV neobsahuje "
            "<code>datumZadani</code>/<code>datumOdevzdani</code>/"
            "<code>datumObhajoby</code>. Reálný stav per řádek určí "
            "heuristika nad dat z CSV (lze ručně přepsat v náhledu).</i></small>"
        )
        status_help.setStyleSheet("color:#888;")
        status_help.setTextFormat(Qt.TextFormat.RichText)
        status_help.setWordWrap(True)
        form.addRow("", status_help)

        # Po úspěchu importu smazat originální CSV (default: ON — typicky
        # nechce na disku zůstat nepořádek se stáhnutým CSV ze STAG)
        self.chk_delete_csv = QCheckBox(
            "🗑 Po dokončení importu smazat originální CSV"
        )
        self.chk_delete_csv.setChecked(True)
        self.chk_delete_csv.setToolTip(
            "Po úspěšném importu (rollback se nepočítá) původní CSV soubor "
            "odstraní z disku. Kopie zůstává jako příloha typu *STAG export* "
            "u každé importované práce."
        )
        form.addRow("", self.chk_delete_csv)

        # Před založením nových studentů otevřít jejich kartu k revizi/doplnění
        # (e-mail, telefon, obor…). Veřejný STAG CSV nese jen osobní číslo a
        # jméno (jméno doplňujeme z vyhledávání), zbytek je vhodné doplnit ručně.
        self.chk_review_students = QCheckBox(
            "✎ Před založením zkontrolovat / doplnit nové studenty"
        )
        self.chk_review_students.setChecked(False)
        self.chk_review_students.setToolTip(
            "Pro každého nového studenta (u vedených prací) otevře kartu "
            "studenta předvyplněnou daty ze STAG — můžeš doplnit e-mail, "
            "telefon, obor apod. Záznam se uloží až v rámci importu."
        )
        form.addRow("", self.chk_review_students)

        btn_load = QPushButton("🔍 Načíst náhled")
        btn_load.clicked.connect(self._load_preview)
        form.addRow("", btn_load)

        outer.addLayout(form)

        # ── Náhled tabulky + detail panel ──────────────────────────────────
        self.lbl_info = QLabel("Načti CSV soubor pro náhled.")
        self.lbl_info.setStyleSheet("color:#888;")
        outer.addWidget(self.lbl_info)

        # Splitter: nahoře tabulka řádků, dole detail vybraného řádku
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setChildrenCollapsible(False)

        self.table = QTableWidget(0, 10)
        self.table.setHorizontalHeaderLabels(
            [
                "Role",
                "Student",
                "Typ",
                "Rok",
                "Téma",
                "Vedoucí",
                "Oponent",
                "Obor (STAG → cíl)",
                "Stav",
                "Akce",
            ]
        )
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setMinimumHeight(180)
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(8, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(9, QHeaderView.ResizeMode.ResizeToContents)
        # Při změně výběru řádku obnov detail panel
        self.table.itemSelectionChanged.connect(self._on_row_selected)
        splitter.addWidget(self.table)

        # Detail panel — HTML zobrazení všech parsovaných polí
        detail_box = QWidget()
        detail_layout = QVBoxLayout(detail_box)
        detail_layout.setContentsMargins(0, 6, 0, 0)
        detail_layout.setSpacing(4)
        detail_header = QLabel("🔎 Detail vybraného řádku")
        detail_header.setStyleSheet("font-weight:bold;")
        detail_layout.addWidget(detail_header)
        self.detail_view = QTextBrowser()
        self.detail_view.setOpenExternalLinks(True)
        self.detail_view.setMinimumHeight(220)
        self.detail_view.setHtml(
            "<p style='color:#888;'>Po načtení náhledu vyber v tabulce řádek "
            "— ukáže se kompletní obsah parsovaného STAG záznamu.</p>"
        )
        detail_layout.addWidget(self.detail_view, stretch=1)
        splitter.addWidget(detail_box)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([360, 280])
        outer.addWidget(splitter, stretch=1)

        # ── Tlačítka ────────────────────────────────────────────────────────
        row = QHBoxLayout()
        self.btn_import = QPushButton("📥 Provést import")
        self.btn_import.setEnabled(False)
        self.btn_import.clicked.connect(self._execute_import)
        f = self.btn_import.font()
        f.setBold(True)
        self.btn_import.setFont(f)
        btn_cancel = QPushButton("Zavřít")
        btn_cancel.clicked.connect(self.reject)
        row.addStretch()
        row.addWidget(btn_cancel)
        row.addWidget(self.btn_import)
        outer.addLayout(row)

    # --- akce ----------------------------------------------------------------

    def _show_csv_download_help(self) -> None:
        """Návod, odkud a jak stáhnout CSV s prací ze STAG."""
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setWindowTitle("Odkud stáhnout CSV ze STAG")
        msg.setTextFormat(Qt.TextFormat.RichText)
        msg.setText(
            "<b>Nejrychleji:</b> použij tlačítko "
            "<b>🌐 Stáhnout ze STAG</b> — práci najde a CSV stáhne přímo "
            "(stačí příjmení studenta + vedoucího/oponenta).<hr>"
            "<b>Nebo ručně z webu STAG:</b>"
            "<ol>"
            "<li>Otevři <a href='https://stag.utb.cz'>stag.utb.cz</a></li>"
            "<li>Sekce <b>Prohlížení</b> → <b>Kvalifikační práce</b></li>"
            "<li>Vyhledej práci podle <b>jména studenta</b></li>"
            "<li>U nalezené práce zvol <b>stažení CSV</b></li>"
            "</ol>"
            "<p>Stažený soubor (<code>getKvalifikacniPrace*.csv</code>) pak "
            "vyber tlačítkem <i>Procházet…</i>.</p>"
            "<p style='color:#888;font-size:11px;'>Záznam kvalifikační práce "
            "je veřejný, takže ke stažení obvykle není potřeba přihlášení.</p>"
        )
        # Umožni klik na odkaz
        lbl = msg.findChild(QLabel, "qt_msgbox_label")
        if lbl is not None:
            lbl.setOpenExternalLinks(True)
        msg.exec()

    def _browse(self) -> None:
        # Začni v poslední použité složce (nebo v adresáři aktuálně vybraného
        # souboru, pokud uživatel už něco vyplnil ručně).
        start_dir = ""
        current = self.ed_path.text().strip()
        if current:
            p = Path(current).expanduser()
            if p.is_dir():
                start_dir = str(p)
            elif p.parent.exists():
                start_dir = str(p.parent)
        if not start_dir and self.profile_manager is not None:
            remembered = self.profile_manager.last_stag_import_dir
            if remembered and Path(remembered).exists():
                start_dir = remembered
        if not start_dir:
            start_dir = str(Path.home())

        path_str, _ = QFileDialog.getOpenFileName(
            self,
            "Vyber STAG CSV soubor",
            start_dir,
            "CSV soubory (*.csv);;Všechny soubory (*.*)",
        )
        if path_str:
            self.ed_path.setText(path_str)
            # Zapamatuj si složku pro příště
            if self.profile_manager is not None:
                try:
                    self.profile_manager.set_last_stag_import_dir(
                        str(Path(path_str).parent)
                    )
                except Exception:
                    pass

    def _open_stag_download(self, auto_role: str | None = None) -> None:
        """Otevře dialog pro přímé vyhledání + stažení CSV ze STAG.

        ``auto_role`` ("supervisor"/"opponent") = hromadné stažení všech mých
        prací dané role (předvyplní a rovnou hledá podle jména z profilu).
        Po úspěšném stažení nastaví cestu k dočasnému CSV a rovnou načte náhled.
        """
        user_name = ""
        if self.profile_manager and self.profile_manager.active:
            user_name = self.profile_manager.active.user_name or ""
        tokens = [
            t.strip(".,")
            for t in user_name.replace(",", " ").split()
            if t.strip(".,")
        ]
        default_surname = tokens[-1] if tokens else ""  # příjmení = poslední token

        if auto_role and not default_surname:
            QMessageBox.information(
                self, "Chybí jméno",
                "Pro hromadné stažení doplň své jméno v profilu "
                "(👤 → Tvoje jméno).",
            )
            return

        dlg = StagDownloadDialog(
            default_person_surname=default_surname, parent=self, service=self.service,
            auto_role=auto_role, user_full_name=user_name,
        )
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        if dlg.files_only_done:
            # Soubory byly připojeny rovnou k existující práci v DB — žádný CSV
            # import. Naviguj na práci a zavři dialog, MainWindow refreshne.
            self.focus_thesis_id = dlg.focus_thesis_id
            self.focus_opposing_id = dlg.focus_opposing_id
            self.accept()
            return
        if dlg.result_items:
            # Zapamatuj si stažené soubory — připojí se po importu práce.
            self._stag_downloaded_files = dict(dlg.downloaded_files)
            # Po stažení (i více prací najednou) rovnou načti náhled.
            self._load_preview_from_stag(dlg.result_items)

    def _load_preview_from_stag(
        self, items: list[tuple[Path, "stag_api.StagThesisResult"]]
    ) -> None:
        """Načte do náhledu jednu nebo více stažených STAG prací (každá = CSV).

        Záznamy ze všech CSV se sloučí; ke každému se doplní jméno studenta
        z výsledku vyhledávání (veřejné CSV ho nemá) a uloží se jeho zdrojové
        CSV (``source_csv``), aby se k práci připojilo to správné.
        """
        user_name = self.ed_user_name.text().strip()
        all_records: list[ParsedRecord] = []
        skipped = 0
        encoding: str | None = None
        for path, meta in items:
            try:
                imp = load_stag_csv(Path(path), user_name=user_name)
            except Exception as exc:  # noqa: BLE001
                QMessageBox.warning(
                    self, "Chyba načítání", f"CSV {Path(path).name} nelze přečíst:\n{exc}"
                )
                continue
            encoding = encoding or imp.encoding
            skipped += imp.skipped
            for rec in imp.records:
                if not rec.student_last and meta.surname:
                    rec.student_last = meta.surname
                if not rec.student_first and meta.name:
                    rec.student_first = meta.name
                rec.source_csv = str(path)
            all_records.extend(imp.records)

        if not all_records:
            QMessageBox.warning(self, "STAG", "Stažené CSV neobsahuje žádná data.")
            return

        self.import_file = ImportFile(
            path=Path(items[0][0]),  # reprezentativní cesta (sloučeno z více CSV)
            encoding=encoding or "utf-8",
            records=all_records,
            skipped=skipped,
        )
        self.ed_path.setText(str(items[0][0]))  # první cesta jen pro zobrazení
        self._persist_user_name(user_name)
        self._populate_preview()

    def _persist_user_name(self, user_name: str) -> None:
        """Uloží user_name do aktivního profilu (pro příští předvyplnění)."""
        if (
            self.profile_manager is not None
            and self.profile_manager.active is not None
            and user_name
            and self.profile_manager.active.user_name != user_name
        ):
            try:
                self.profile_manager.set_user_name(
                    self.profile_manager.active.id, user_name
                )
            except Exception:  # noqa: BLE001
                pass

    def _load_preview(self) -> None:
        path_str = self.ed_path.text().strip()
        if not path_str:
            QMessageBox.warning(self, "Chybí soubor", "Vyber nejdřív CSV soubor.")
            return
        user_name = self.ed_user_name.text().strip()
        try:
            self.import_file = load_stag_csv(Path(path_str), user_name=user_name)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Chyba načítání", f"Soubor nelze přečíst:\n{exc}")
            return

        # Doplň jméno studenta z výsledku vyhledávání ve STAG — veřejný CSV
        # export jméno (jmeno/prijmeni.student) NEOBSAHUJE, jen osobní číslo.
        self._apply_stag_meta_to_records()

        # Ulož user_name do aktivního profilu, aby se příště předvyplnil
        if (
            self.profile_manager is not None
            and self.profile_manager.active is not None
            and user_name
            and self.profile_manager.active.user_name != user_name
        ):
            try:
                self.profile_manager.set_user_name(
                    self.profile_manager.active.id, user_name
                )
            except Exception:
                pass

        self._populate_preview()

    def _apply_stag_meta_to_records(self) -> None:
        """Doplní jméno studenta z výsledku vyhledávání STAG do načtených
        záznamů (veřejný CSV jméno neobsahuje). Spotřebuje ``_pending_stag_meta``.
        """
        meta = self._pending_stag_meta
        self._pending_stag_meta = None
        if meta is None or self.import_file is None:
            return
        for rec in self.import_file.records:
            # Páruj přes adipidno; u jednořádkového exportu doplň vždy.
            matches = (
                rec.adipidno and meta.adipidno and rec.adipidno == meta.adipidno
            ) or len(self.import_file.records) == 1
            if not matches:
                continue
            if not rec.student_last and meta.surname:
                rec.student_last = meta.surname
            if not rec.student_first and meta.name:
                rec.student_first = meta.name

    def _populate_preview(self) -> None:
        if self.import_file is None:
            return

        # Reset
        self.row_widgets = []
        self.table.setRowCount(0)
        if not self.import_file.records:
            self.lbl_info.setText(
                f"⚠ Soubor neobsahuje data ({self.import_file.skipped} přeskočeno)."
            )
            self.btn_import.setEnabled(False)
            return

        # Akademické obory v naší DB — pro mapování
        all_obory = self.service.list_obor_objects()
        obory_by_stag = {o.stag_code: o for o in all_obory if o.stag_code}
        all_obor_names = [o.name for o in all_obory]

        default_status = ThesisStatus(self.cb_default_status.currentData())

        existing_theses = self.service.list_theses()
        existing_opposing = self.service.list_opposing_theses()

        # Styl pro combo s neutrálním pozadím — sjednotí read na světlém i tmavém
        # tématu OS (default QComboBox je transparentní → na alternujícím
        # pozadí splývá s řádkem, špatně čitelné).
        combo_neutral_qss = (
            "QComboBox { background-color: palette(base); color: palette(text); "
            "border: 1px solid palette(mid); border-radius: 3px; padding: 2px 4px; }"
            "QComboBox QAbstractItemView { background-color: palette(base); "
            "color: palette(text); }"
        )

        for record in self.import_file.records:
            row_idx = self.table.rowCount()
            self.table.insertRow(row_idx)

            # === Role combobox ===
            cb_role = QComboBox()
            cb_role.addItem("🎓 Vedu já", ImportRole.SUPERVISOR.value)
            cb_role.addItem("🧐 Oponuji", ImportRole.OPPONENT.value)
            initial = (
                ImportRole.SUPERVISOR.value
                if record.role != ImportRole.OPPONENT
                else ImportRole.OPPONENT.value
            )
            cb_role.setCurrentIndex(0 if initial == ImportRole.SUPERVISOR.value else 1)
            if record.role == ImportRole.UNKNOWN:
                # Neutrální QSS pro čitelnost + jednoznačné jantarové varování
                cb_role.setStyleSheet(
                    "QComboBox { background-color: #fff3e0; color: #5d4037; "
                    "border: 1px solid #ffb74d; border-radius: 3px; padding: 2px 4px; "
                    "font-weight: bold; }"
                    "QComboBox QAbstractItemView { background-color: #fffaf2; "
                    "color: #5d4037; }"
                )
                cb_role.setToolTip(
                    "⚠ Roli se nepodařilo auto-detekovat — překontroluj ji."
                )
            else:
                cb_role.setStyleSheet(combo_neutral_qss)
            # Po změně role aktualizuj detail panel
            cb_role.currentIndexChanged.connect(
                lambda _, r=row_idx: self._refresh_detail_if_current(r)
            )
            self.table.setCellWidget(row_idx, 0, cb_role)

            # === Student ===
            student_label = f"{record.student_last}, {record.student_first}"
            if record.student_uni_id:
                student_label += f"  [{record.student_uni_id}]"
            student_item = QTableWidgetItem(student_label)
            self.table.setItem(row_idx, 1, student_item)

            # === Typ ===
            type_item = QTableWidgetItem(record.type_code)
            type_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row_idx, 2, type_item)

            # === Rok ===
            year_item = QTableWidgetItem(record.academic_year or "—")
            year_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row_idx, 3, year_item)

            # === Téma ===
            theme_item = QTableWidgetItem(record.title_cs or "(bez názvu)")
            theme_item.setToolTip(record.title_cs or "")
            self.table.setItem(row_idx, 4, theme_item)

            # === Vedoucí ===
            sup_item = QTableWidgetItem(record.supervisor_name or "—")
            sup_item.setToolTip(record.supervisor_name or "")
            self.table.setItem(row_idx, 5, sup_item)

            # === Oponent ===
            opp_item = QTableWidgetItem(record.opponent_name or "—")
            opp_item.setToolTip(record.opponent_name or "")
            self.table.setItem(row_idx, 6, opp_item)

            # === Obor mapping ===
            cb_obor = QComboBox()
            cb_obor.setEditable(False)
            # Volby:
            #  - mapping na existující obor (auto-detekce přes stag_code)
            #  - "(zachovat STAG kód jako jméno)"
            #  - "+ Nový obor…"
            cb_obor.addItem(f"⚠ Nemapováno — uložit jako '{record.student_obor_stag}'", "__keep__")
            for obor_name in all_obor_names:
                cb_obor.addItem(obor_name, obor_name)
            cb_obor.addItem("➕ Nový obor…", "__new__")

            # Auto-mapping přes stag_code
            mapped = obory_by_stag.get(record.student_obor_stag)
            if mapped:
                idx = cb_obor.findData(mapped.name)
                if idx >= 0:
                    cb_obor.setCurrentIndex(idx)
            # Capture row pro on-change
            cb_obor.currentIndexChanged.connect(
                lambda _, r=row_idx: self._on_obor_combo_changed(r)
            )
            stag_label = QLabel(record.student_obor_stag or "—")
            stag_label.setStyleSheet("color:#888;font-size:11px;")
            obor_widget = QWidget()
            obor_layout = QHBoxLayout(obor_widget)
            obor_layout.setContentsMargins(2, 0, 2, 0)
            obor_layout.setSpacing(4)
            obor_layout.addWidget(stag_label)
            obor_layout.addWidget(cb_obor, stretch=1)
            self.table.setCellWidget(row_idx, 7, obor_widget)
            # Jantarové zvýraznění, pokud STAG obor nemá lokální mapování.
            self._style_obor_combo(cb_obor)
            cb_obor.currentIndexChanged.connect(
                lambda _, cb=cb_obor: self._style_obor_combo(cb)
            )

            # === Stav (jen pro Vedené práce) ===
            cb_status = QComboBox()
            cb_status.setStyleSheet(combo_neutral_qss)
            for st in ThesisStatus:
                cb_status.addItem(st.label, st.value)
            # Smart per-row default:
            #  - datumObhajoby vyplněno → Obhájeno
            #  - datumOdevzdani vyplněno (ale ne obhajoba) → V řešení
            #  - datumZadani vyplněno (ale ne odevzdání) → V řešení
            #  - jinak → globální default z formuláře
            #
            # Pokud uživatel globální default v hlavičce explicitně přepsal
            # (ne defaultní DEFENDED), jeho volba má přednost nad heuristikou.
            row_default = self._smart_status_for_record(record, default_status)
            idx = cb_status.findData(row_default.value)
            if idx >= 0:
                cb_status.setCurrentIndex(idx)
            cb_status.currentIndexChanged.connect(
                lambda _, r=row_idx: self._refresh_detail_if_current(r)
            )
            # Tooltip vysvětluje proč jsme zvolili daný default
            cb_status.setToolTip(
                self._status_heuristic_explanation(record, row_default)
            )
            self.table.setCellWidget(row_idx, 8, cb_status)

            # === Akce ===
            existing_label = self._find_existing_label(
                record, existing_theses, existing_opposing,
                role=ImportRole(initial),
            )
            cb_action = QComboBox()
            cb_action.setStyleSheet(combo_neutral_qss)
            if existing_label:
                cb_action.addItem(f"🔄 Aktualizovat ({existing_label})", ACTION_UPDATE)
                cb_action.addItem("✗ Přeskočit", ACTION_SKIP)
            else:
                cb_action.addItem("✓ Vytvořit novou", ACTION_CREATE)
                cb_action.addItem("✗ Přeskočit", ACTION_SKIP)
            self.table.setCellWidget(row_idx, 9, cb_action)

            self.row_widgets.append({
                "record": record,
                "cb_role": cb_role,
                "cb_obor": cb_obor,
                "cb_status": cb_status,
                "cb_action": cb_action,
            })

        # Předvyber první řádek a ukaž detail
        if self.row_widgets:
            self.table.selectRow(0)
            self._render_record_detail(0)

        # Spočti, kolik řádků má nenamapovaný obor (default „Nemapováno").
        unmapped = sum(
            1 for w in self.row_widgets
            if w["cb_obor"].currentData() == "__keep__"
        )
        info = (
            f"📊 Řádků: {len(self.import_file.records)} "
            f"(přeskočeno při parsingu: {self.import_file.skipped})  ·  "
            f"Encoding: {self.import_file.encoding}"
        )
        if unmapped:
            info += (
                f"  ·  <span style='color:#e65100;font-weight:bold;'>"
                f"⚠ {unmapped}× nenamapovaný obor</span> — "
                f"doplň ve sloupci „Obor (STAG → cíl)\""
            )
        self.lbl_info.setTextFormat(Qt.TextFormat.RichText)
        self.lbl_info.setText(info)
        self.btn_import.setEnabled(True)

    # --- detail panel --------------------------------------------------------

    def _on_row_selected(self) -> None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        row_idx = rows[0].row()
        self._render_record_detail(row_idx)

    def _refresh_detail_if_current(self, row_idx: int) -> None:
        """Aktualizuje detail panel, pokud uživatel právě má vybraný tento řádek."""
        rows = self.table.selectionModel().selectedRows()
        if rows and rows[0].row() == row_idx:
            self._render_record_detail(row_idx)

    def _render_record_detail(self, row_idx: int) -> None:
        if row_idx < 0 or row_idx >= len(self.row_widgets):
            return
        ws = self.row_widgets[row_idx]
        record: ParsedRecord = ws["record"]
        cb_role: QComboBox = ws["cb_role"]
        cb_obor: QComboBox = ws["cb_obor"]
        cb_status: QComboBox = ws["cb_status"]
        cb_action: QComboBox = ws["cb_action"]

        role_value = cb_role.currentData()
        role_label = (
            "🎓 Vedu (Thesis)"
            if role_value == ImportRole.SUPERVISOR.value
            else "🧐 Oponuji (OpposingThesis)"
        )
        status_label = cb_status.currentText()
        action_label = cb_action.currentText()
        obor_data = cb_obor.currentData()
        if obor_data == "__keep__":
            obor_target = (
                f"⚠ Nemapováno (uložit jako '{record.student_obor_stag}')"
            )
        elif obor_data == "__new__":
            obor_target = "➕ Nový obor (zatím nevytvořen)"
        else:
            obor_target = obor_data or "—"

        def esc(value: str | None) -> str:
            from html import escape

            if not value:
                return "<span style='color:#aaa;'>—</span>"
            return escape(str(value))

        def multiline(value: str | None) -> str:
            from html import escape

            if not value:
                return "<span style='color:#aaa;'>—</span>"
            lines = [escape(ln) for ln in str(value).splitlines() if ln.strip()]
            if not lines:
                return "<span style='color:#aaa;'>—</span>"
            items = "".join(f"<li>{ln}</li>" for ln in lines)
            return f"<ol style='margin:0 0 0 18px;padding:0;'>{items}</ol>"

        def fmt_date(d) -> str:
            if d is None:
                return "<span style='color:#aaa;'>—</span>"
            return d.strftime("%d.%m.%Y")

        student_line = (
            f"{esc(record.student_title_pre)} "
            f"<b>{esc(record.student_first)} {esc(record.student_last)}</b> "
            f"{esc(record.student_title_post)}"
        ).strip()
        uni = f" <code>[{esc(record.student_uni_id)}]</code>" if record.student_uni_id else ""

        html = f"""
        <style>
          h3 {{ margin: 8px 0 4px 0; font-size: 13px; color: #444; }}
          table.kv {{ border-collapse: collapse; }}
          table.kv td {{ padding: 2px 8px 2px 0; vertical-align: top; }}
          table.kv td.k {{ color: #666; white-space: nowrap; }}
          .badge {{ background-color: #e8f0fe; color: #1565c0; padding: 1px 6px;
                    border-radius: 6px; font-weight: bold; }}
          .small {{ color: #888; font-size: 11px; }}
        </style>
        <table class='kv'>
          <tr><td class='k'>Role</td><td><span class='badge'>{esc(role_label)}</span></td></tr>
          <tr><td class='k'>Akce</td><td>{esc(action_label)}</td></tr>
          <tr><td class='k'>Student</td><td>{student_line}{uni}</td></tr>
          <tr><td class='k'>Obor (STAG)</td><td>{esc(record.student_obor_stag)} →
              <b>{esc(obor_target)}</b></td></tr>
          <tr><td class='k'>Typ / Rok</td><td>{esc(record.type_code)} ·
              {esc(record.academic_year)}</td></tr>
          <tr><td class='k'>STAG ID práce</td>
              <td><code>{esc(record.adipidno)}</code></td></tr>
          <tr><td class='k'>Stav (zvolený)</td><td>{esc(status_label)}</td></tr>
          <tr><td class='k'>Stav (STAG kód)</td>
              <td><code>{esc(record.stag_state_code)}</code>
              {" — <i>" + esc(STAG_STATE_LABELS.get((record.stag_state_code or '').strip().upper(), 'neznámý kód')) + "</i>" if record.stag_state_code else ""}
              </td></tr>
          <tr><td class='k'>Vedoucí</td><td>{esc(record.supervisor_name)}</td></tr>
          <tr><td class='k'>Oponent</td><td>{esc(record.opponent_name)}</td></tr>
          <tr><td class='k'>Známky</td>
              <td>vedoucí: <b>{esc(record.grade_supervisor)}</b> ·
                  oponent: <b>{esc(record.grade_opponent)}</b></td></tr>
          <tr><td class='k'>Datumy</td>
              <td>zadáno: {fmt_date(record.date_assigned)} ·
                  odevzdáno: {fmt_date(record.date_submitted)} ·
                  obhajoba: {fmt_date(record.date_defended)}</td></tr>
        </table>

        <h3>Název CZ</h3>
        <div>{esc(record.title_cs)}</div>
        <h3>Název EN</h3>
        <div>{esc(record.title_en)}</div>

        <h3>Anotace CZ</h3>
        <div style='white-space:pre-wrap;'>{esc(record.annotation_cs)}</div>
        <h3>Anotace EN</h3>
        <div style='white-space:pre-wrap;'>{esc(record.annotation_en)}</div>

        <h3>Zásady pro vypracování (body zadání)</h3>
        {multiline(record.objectives_text)}

        <h3>Seznam doporučené literatury</h3>
        {multiline(record.references_text)}
        """
        self.detail_view.setHtml(html)

    # --- obor mapping --------------------------------------------------------

    @staticmethod
    def _style_obor_combo(cb_obor: QComboBox) -> None:
        """Obarví obor combo — jantarově když je „Nemapováno", jinak neutrálně.

        Vizuálně upozorní, že STAG obor nemá lokální mapování (uživatel by
        ho měl namapovat na existující obor nebo založit nový).
        """
        neutral = (
            "QComboBox { background-color: palette(base); color: palette(text); "
            "border: 1px solid palette(mid); border-radius: 3px; padding: 2px 4px; }"
            "QComboBox QAbstractItemView { background-color: palette(base); "
            "color: palette(text); }"
        )
        amber = (
            "QComboBox { background-color: #fff3e0; color: #5d4037; "
            "border: 1px solid #ffb74d; border-radius: 3px; padding: 2px 4px; "
            "font-weight: bold; }"
            "QComboBox QAbstractItemView { background-color: #fffaf2; "
            "color: #5d4037; }"
        )
        if cb_obor.currentData() == "__keep__":
            cb_obor.setStyleSheet(amber)
            cb_obor.setToolTip(
                "⚠ STAG obor není namapovaný na žádný evidovaný obor. "
                'Vyber existující obor, nebo zvol „Nový obor…" — předvyplní se '
                "STAG kód, takže příště se namapuje automaticky."
            )
        else:
            cb_obor.setStyleSheet(neutral)
            cb_obor.setToolTip("")

    def _on_obor_combo_changed(self, row_idx: int) -> None:
        if row_idx >= len(self.row_widgets):
            return
        cb_obor: QComboBox = self.row_widgets[row_idx]["cb_obor"]
        data = cb_obor.currentData()
        if data != "__new__":
            # každopádně aktualizuj detail (zobrazený cíl mapování se mění)
            self._refresh_detail_if_current(row_idx)
            return
        # Otevři nový obor dialog
        record: ParsedRecord = self.row_widgets[row_idx]["record"]
        # Pre-fill: STAG kód = student_obor_stag
        new_obor = Obor(name="", stag_code=record.student_obor_stag or None)
        dlg = OborDialog(self.service, new_obor, parent=self)
        if dlg.exec():
            # Reload obory v combu (a vyber nově vytvořený)
            self._reload_obor_options(cb_obor, prefer_name=new_obor.name)
        else:
            # Cancel — vrať zpět na první volbu (Nemapováno)
            cb_obor.setCurrentIndex(0)
        self._refresh_detail_if_current(row_idx)

    def _reload_obor_options(self, cb_obor: QComboBox, prefer_name: str = "") -> None:
        all_obory = self.service.list_obor_objects()
        record = None
        for w in self.row_widgets:
            if w["cb_obor"] is cb_obor:
                record = w["record"]
                break
        stag = record.student_obor_stag if record else ""
        cb_obor.blockSignals(True)
        try:
            cb_obor.clear()
            cb_obor.addItem(f"⚠ Nemapováno — uložit jako '{stag}'", "__keep__")
            for o in all_obory:
                cb_obor.addItem(o.name, o.name)
            cb_obor.addItem("➕ Nový obor…", "__new__")
            if prefer_name:
                idx = cb_obor.findData(prefer_name)
                if idx >= 0:
                    cb_obor.setCurrentIndex(idx)
        finally:
            cb_obor.blockSignals(False)

    def _find_existing_label(
        self,
        record: ParsedRecord,
        existing_theses: list[Thesis],
        existing_opposing: list[OpposingThesis],
        role: ImportRole,
    ) -> str:
        """Vrátí krátký popis existující práce/posudku ke stejnému studentovi+roku.

        Pokud nenajde, vrátí prázdný string.
        """
        type_value = record.type_code
        year = record.academic_year
        uni_id = record.student_uni_id.strip()
        adip = record.adipidno.strip()

        if role == ImportRole.SUPERVISOR:
            # 1) přesně přes adipidno
            if adip:
                for t in existing_theses:
                    if t.adipidno and t.adipidno == adip:
                        return f"existuje: {t.display_title[:40]}"
            # 2) fallback: student_id (přes university_id) + year + type
            students_by_uni_id = {
                s.university_id: s for s in self.service.list_students()
                if s.university_id
            }
            student = students_by_uni_id.get(uni_id)
            if student is None:
                return ""
            for t in existing_theses:
                if (
                    t.student_id == student.id
                    and t.academic_year == year
                    and t.type.value == type_value
                ):
                    return f"existuje: {t.display_title[:40]}"
            return ""
        else:
            if adip:
                for o in existing_opposing:
                    if o.adipidno and o.adipidno == adip:
                        return f"existuje: {o.display_title[:40]}"
            # OPPOSING — match podle student_uni_id (inline) + year + type
            for o in existing_opposing:
                if (
                    o.student_university_id == uni_id
                    and o.academic_year == year
                    and o.type.value == type_value
                ):
                    return f"existuje: {o.display_title[:40]}"
            return ""

    # --- vlastní import (transakční) ----------------------------------------

    def _collect_active_rows(self) -> list[dict]:
        """Vrátí řádky, které se mají importovat (akce není „Přeskočit")."""
        active = []
        for ws in self.row_widgets:
            if ws["cb_action"].currentData() != ACTION_SKIP:
                active.append(ws)
        return active

    def _scan_missing_entities(self, active_rows: list[dict]) -> dict[str, list]:
        """Pre-flight scan — zjistí, které entity zatím v registrech nejsou.

        Vrací slovník:
          ``students``: [(label, uni_id, obor_name), …]
          ``opponents``: [name, …]    (deduplikováno)
          ``supervisors``: [name, …]   (deduplikováno)
          ``obory``: [stag_code, …]    (řádky s mapováním „Nemapováno",
                     kde lokální obor neexistuje pod tímtéž jménem)
        """
        existing_students_by_uni = {
            s.university_id: s for s in self.service.list_students() if s.university_id
        }
        existing_opponent_names = {o.name for o in self.service.list_opponents()}
        existing_supervisor_names = {s.name for s in self.service.list_supervisors()}
        existing_obor_names = {o.name for o in self.service.list_obor_objects()}

        new_students: list[tuple[str, str, str]] = []
        new_opponents: set[str] = set()
        new_supervisors: set[str] = set()
        new_obory: set[str] = set()
        seen_uni: set[str] = set()

        for ws in active_rows:
            record: ParsedRecord = ws["record"]
            role = ImportRole(ws["cb_role"].currentData())
            obor_choice = ws["cb_obor"].currentData()
            obor_name = (
                obor_choice
                if obor_choice not in ("__keep__", "__new__")
                else (record.student_obor_stag or "")
            )

            # Student je relevantní jen pro SUPERVISOR role
            # (pro OPPOSING ukládáme inline jméno, ne entitu Student).
            if role == ImportRole.SUPERVISOR:
                uni_id = record.student_uni_id.strip()
                if uni_id and uni_id not in existing_students_by_uni and uni_id not in seen_uni:
                    seen_uni.add(uni_id)
                    label = f"{record.student_last}, {record.student_first}"
                    new_students.append((label, uni_id, obor_name))

            # Vedoucí — registr (jen pro OPPOSING role je relevantní cizí vedoucí)
            if role == ImportRole.OPPONENT and record.supervisor_name:
                if record.supervisor_name not in existing_supervisor_names:
                    new_supervisors.add(record.supervisor_name)

            # Oponent — registr (jen pro SUPERVISOR role je relevantní cizí oponent)
            if role == ImportRole.SUPERVISOR and record.opponent_name:
                if record.opponent_name not in existing_opponent_names:
                    new_opponents.add(record.opponent_name)

            # Obor — jen pokud uživatel zvolil „Nemapováno" a ten název ještě neexistuje
            if obor_choice == "__keep__" and obor_name and obor_name not in existing_obor_names:
                new_obory.add(obor_name)

        return {
            "students": new_students,
            "opponents": sorted(new_opponents),
            "supervisors": sorted(new_supervisors),
            "obory": sorted(new_obory),
        }

    def _show_preflight_dialog(self, missing: dict[str, list], total_rows: int) -> bool:
        """Pre-flight potvrzení — ukáže, co se bude vytvářet. Vrací True pro pokračování."""
        from html import escape as _esc

        any_new = any(missing.values())
        rows_count = total_rows

        body_parts: list[str] = [
            f"<p>Připraveno k importu: <b>{rows_count}</b> "
            f"{self._cs_plural(rows_count, 'řádek', 'řádky', 'řádků')}.</p>",
        ]

        if any_new:
            body_parts.append(
                "<p><b>Tyto entity zatím nejsou v registru a budou "
                "automaticky založeny:</b></p>"
            )

            if missing["students"]:
                items = "".join(
                    f"<li>{_esc(label)} <code>[{_esc(uni)}]</code>"
                    + (f" · {_esc(obor)}" if obor else "")
                    + "</li>"
                    for label, uni, obor in missing["students"]
                )
                body_parts.append(
                    f"<p>👨‍🎓 <b>Studenti</b> ({len(missing['students'])}):</p>"
                    f"<ul style='margin-top:0;'>{items}</ul>"
                )

            if missing["opponents"]:
                items = "".join(f"<li>{_esc(name)}</li>" for name in missing["opponents"])
                body_parts.append(
                    f"<p>🧐 <b>Oponenti</b> ({len(missing['opponents'])}):"
                    f" <span style='color:#888;font-size:11px;'>"
                    f"založí se jako <i>interní</i> — kind a kontakt lze upravit dodatečně"
                    f"</span></p>"
                    f"<ul style='margin-top:0;'>{items}</ul>"
                )

            if missing["supervisors"]:
                items = "".join(f"<li>{_esc(name)}</li>" for name in missing["supervisors"])
                body_parts.append(
                    f"<p>🎓 <b>Vedoucí</b> ({len(missing['supervisors'])}):"
                    f" <span style='color:#888;font-size:11px;'>"
                    f"do registru vedoucích (pro oponentské posudky)"
                    f"</span></p>"
                    f"<ul style='margin-top:0;'>{items}</ul>"
                )

            if missing["obory"]:
                items = "".join(f"<li><code>{_esc(name)}</code></li>" for name in missing["obory"])
                body_parts.append(
                    "<p style='background:#fff3e0;color:#5d4037;padding:8px;"
                    "border-radius:4px;border:1px solid #ffb74d;'>"
                    f"⚠ <b>Nenamapované obory</b> ({len(missing['obory'])}) — "
                    "STAG kód oboru nemá protějšek v evidovaných oborech, "
                    "uloží se jako prostý název (a <b>příště se znovu "
                    "nenamapuje automaticky</b>).<br>"
                    "<small>Doporučení: zavři tento dialog a u dotčených řádků "
                    "vyber ve sloupci <i>Obor</i> existující obor, nebo "
                    'zvol „➕ Nový obor…" (předvyplní STAG kód → příští import '
                    "se namapuje sám).</small>"
                    f"<ul style='margin:6px 0 0 0;'>{items}</ul>"
                    "</p>"
                )
        else:
            body_parts.append(
                "<p style='color:#2e7d32;'>✓ Všechny související entity již "
                "v registru existují — nic nového se zakládat nebude.</p>"
            )

        body_parts.append(
            "<hr>"
            "<p style='color:#666;font-size:11px;'>"
            "Změny se zapíšou na disk až po úspěšném dokončení importu. "
            "Před zápisem se navíc vytvoří záloha <code>before-stag-import</code>. "
            "Pokud kdykoli dojde k chybě, vše se rolluje zpět a aktuální data "
            "zůstanou nedotčená.</p>"
        )

        # Vlastní dialog s rich textem (QMessageBox omezuje formatting)
        dlg = QDialog(self)
        dlg.setWindowTitle("Souhrn před importem")
        dlg.setMinimumSize(640, 480)
        outer = QVBoxLayout(dlg)
        header = QLabel("📋 Souhrn před importem")
        header.setStyleSheet("font-weight:bold;font-size:14px;")
        outer.addWidget(header)
        body = QTextBrowser()
        body.setOpenExternalLinks(False)
        body.setHtml("".join(body_parts))
        outer.addWidget(body, stretch=1)

        btn_row = QHBoxLayout()
        btn_cancel = QPushButton("Zrušit")
        btn_cancel.clicked.connect(dlg.reject)
        btn_go = QPushButton("✓ Provést import")
        f = btn_go.font()
        f.setBold(True)
        btn_go.setFont(f)
        btn_go.setDefault(True)
        btn_go.clicked.connect(dlg.accept)
        btn_row.addStretch()
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_go)
        outer.addLayout(btn_row)

        return dlg.exec() == QDialog.DialogCode.Accepted

    @staticmethod
    def _cs_plural(n: int, one: str, few: str, many: str) -> str:
        if n == 1:
            return one
        if 2 <= n <= 4:
            return few
        return many

    @staticmethod
    def _smart_status_for_record(
        record: ParsedRecord, fallback: ThesisStatus
    ) -> ThesisStatus:
        """Per-řádkový default stav.

        Priorita:
        1. **STAG kód `stavPrace`** (R / DBPOO / DUO / DBUO / ND) — pokud je
           v CSV, je autoritativní (přímo říká stav práce).
        2. **Datumové heuristiky** — fallback pro CSV bez ``stavPrace``:
           - ``datumObhajoby`` vyplněno → ``DEFENDED``
           - ``datumOdevzdani`` vyplněno (ale ne obhajoba) → ``IN_PROGRESS``
           - ``datumZadani`` vyplněno (ale ne odevzdání) → ``IN_PROGRESS``
        3. **Fallback** z hlavičkového combo boxu pro úplně prázdné řádky.

        Mapování STAG kódů → náš ``ThesisStatus``: viz konstanta
        ``STAG_STATE_TO_STATUS`` na vrcholu modulu.
        """
        code = (record.stag_state_code or "").strip().upper()
        if code in STAG_STATE_TO_STATUS:
            return STAG_STATE_TO_STATUS[code]
        # Fallback na datumovou heuristiku
        if record.date_defended is not None:
            return ThesisStatus.DEFENDED
        if record.date_submitted is not None:
            return ThesisStatus.IN_PROGRESS
        if record.date_assigned is not None:
            return ThesisStatus.IN_PROGRESS
        return fallback

    @staticmethod
    def _status_heuristic_explanation(
        record: ParsedRecord, chosen: ThesisStatus
    ) -> str:
        code = (record.stag_state_code or "").strip().upper()
        # 1) Známý STAG kód má přednost
        if code in STAG_STATE_TO_STATUS:
            human = STAG_STATE_LABELS.get(code, "")
            return (
                f"Auto-default: {chosen.label}\n"
                f"  → STAG stavPrace = {code} ({human})\n"
                f"\n"
                f"Mapování STAG → BPDPManager:\n"
                f"  R     → V řešení (Rozpracovaná)\n"
                f"  DBPOO → V řešení (Dokončená bez pokusu o obhajobu)\n"
                f"  DUO   → Obhájeno (úspěšná obhajoba)\n"
                f"  DBUO  → Nedokončeno (neúspěšná obhajoba)\n"
                f"  ND    → Nedokončeno (nedokončená)\n"
                f"\n"
                f"Pokud je to chyba, zvol jiný stav."
            )
        # 2) STAG kód neznámý / prázdný → datumové fallback
        if code:
            prefix = (
                f"STAG stavPrace = {code} — neznámý kód, použita "
                "datumová heuristika:\n"
            )
        else:
            prefix = (
                "STAG stavPrace prázdné, použita datumová heuristika:\n"
            )
        if record.date_defended is not None:
            return prefix + (
                f"  → Obhájeno (CSV má datumObhajoby = "
                f"{record.date_defended.strftime('%d.%m.%Y')})."
            )
        if record.date_submitted is not None:
            return prefix + (
                f"  → V řešení (CSV má datumOdevzdani = "
                f"{record.date_submitted.strftime('%d.%m.%Y')} "
                "ale ne datumObhajoby)."
            )
        if record.date_assigned is not None:
            return prefix + (
                f"  → V řešení (CSV má datumZadani = "
                f"{record.date_assigned.strftime('%d.%m.%Y')} "
                "ale ne odevzdání)."
            )
        return f"Default z hlavičky: {chosen.label}"

    def _execute_import(self) -> None:
        if not self.row_widgets:
            return

        active_rows = self._collect_active_rows()
        if not active_rows:
            QMessageBox.information(
                self,
                "Nic k importu",
                'Všechny řádky mají akci „Přeskočit". Nastav alespoň jeden řádek '
                "na *Vytvořit* nebo *Aktualizovat*.",
            )
            return

        # 1) Pre-flight scan — co je nutné založit
        missing = self._scan_missing_entities(active_rows)
        if not self._show_preflight_dialog(missing, len(active_rows)):
            return  # uživatel zrušil

        # 1b) Volitelná revize/doplnění nových studentů (před zápisem)
        self._reviewed_students = {}
        if self.chk_review_students.isChecked():
            reviewed = self._review_new_students(active_rows)
            if reviewed is None:
                return  # uživatel revizi zrušil → celý import zruš
            self._reviewed_students = reviewed

        # 2) Backup před importem (záchranná brzda — umožní celý import vrátit)
        self._preimport_backup_file = None
        self._preimport_data_dir = None
        if self.profile_manager and self.profile_manager.active:
            data_dir = self.profile_manager.active_data_dir()
            try:
                info = BackupManager(data_dir).create_backup(
                    data_dir / "db.json",
                    suffix="before-stag-import",
                    dedupe=False,
                )
                if info is not None:
                    self._preimport_backup_file = info.path.name
                    self._preimport_data_dir = data_dir
            except Exception:
                pass

        # 3) Transakční blok — všechno se zapíše jednou na konci, nebo nic
        stats = {
            "created_thesis": 0, "updated_thesis": 0,
            "created_opposing": 0, "updated_opposing": 0,
            "created_student": 0, "created_opponent": 0,
            "created_supervisor": 0, "skipped": 0,
            "attached_csv": 0, "attached_files": 0,
        }
        errors: list[str] = []
        affected_thesis_ids: list[str] = []
        affected_opposing_ids: list[str] = []
        # Per-práce zdrojové CSV (u vícesouborového stažení se ke každé práci
        # připojí to její). Fallback je společný ``csv_source``.
        thesis_csv: dict[str, str] = {}
        opposing_csv: dict[str, str] = {}
        # adipIdno → id práce/posudku (pro připojení stažených STAG souborů).
        thesis_by_adip: dict[str, str] = {}
        opposing_by_adip: dict[str, str] = {}
        last_thesis_id: str | None = None
        last_opposing_id: str | None = None

        csv_source = Path(self.ed_path.text().strip()) if self.ed_path.text().strip() else None

        try:
            with self.service.batch():
                # 3a) Per-row apply
                for widget_set in active_rows:
                    record: ParsedRecord = widget_set["record"]
                    cb_role: QComboBox = widget_set["cb_role"]
                    cb_obor: QComboBox = widget_set["cb_obor"]
                    cb_status: QComboBox = widget_set["cb_status"]

                    role = ImportRole(cb_role.currentData())
                    obor_choice = cb_obor.currentData()
                    obor_name = (
                        obor_choice
                        if obor_choice not in ("__keep__", "__new__")
                        else (record.student_obor_stag or "")
                    )
                    status = ThesisStatus(cb_status.currentData())

                    try:
                        if role == ImportRole.SUPERVISOR:
                            thesis_id, _is_new = self._apply_supervisor_role(
                                record, obor_name, status, stats
                            )
                            affected_thesis_ids.append(thesis_id)
                            if record.source_csv:
                                thesis_csv[thesis_id] = record.source_csv
                            if record.adipidno:
                                thesis_by_adip[record.adipidno] = thesis_id
                            last_thesis_id = thesis_id
                        else:
                            op_id, _is_new = self._apply_opponent_role(
                                record, obor_name, stats
                            )
                            affected_opposing_ids.append(op_id)
                            if record.source_csv:
                                opposing_csv[op_id] = record.source_csv
                            if record.adipidno:
                                opposing_by_adip[record.adipidno] = op_id
                            last_opposing_id = op_id
                    except Exception as exc:  # noqa: BLE001
                        errors.append(
                            f"{record.student_last} {record.student_first}: {exc}"
                        )

                # 3b) Připoj CSV jako STAG_EXPORT k dotčeným pracem (každé to její)
                for tid in affected_thesis_ids:
                    src = Path(thesis_csv[tid]) if tid in thesis_csv else csv_source
                    if not (src and src.exists()):
                        continue
                    try:
                        self.service.attach_document(
                            tid, src, kind=AttachmentKind.STAG_EXPORT
                        )
                        stats["attached_csv"] += 1
                    except Exception as exc:  # noqa: BLE001
                        errors.append(f"Přiložení CSV k práci {tid[:8]}: {exc}")
                for oid in affected_opposing_ids:
                    src = Path(opposing_csv[oid]) if oid in opposing_csv else csv_source
                    if not (src and src.exists()):
                        continue
                    try:
                        self.service.opposing_attach_document(
                            oid, src, kind=AttachmentKind.STAG_EXPORT
                        )
                        stats["attached_csv"] += 1
                    except Exception as exc:  # noqa: BLE001
                        errors.append(f"Přiložení CSV k posudku {oid[:8]}: {exc}")

                # 3b2) Připoj soubory stažené ze STAG (text/přílohy/posudky)
                self._attach_downloaded_files(
                    thesis_by_adip, opposing_by_adip, stats, errors
                )

                # 3c) Pokud se cokoli nepovedlo a uživatel je dotazuje, dej mu
                #     šanci rollback udělat výjimkou z bloku.
                if errors:
                    raise _ImportHadErrors(errors)
        except _ImportHadErrors as bundle:
            # Nabídni rollback při chybě
            choice = self._ask_continue_with_errors(bundle.errors, stats)
            if choice == "rollback":
                # Restartuj batch BEZ chyb — vše už bylo zahozeno, jen dej vědět uživateli
                QMessageBox.warning(
                    self,
                    "Import zrušen",
                    "Žádné změny nebyly uloženy. Pokud chceš, můžeš upravit data "
                    "v náhledu a zkusit znovu, nebo zavřít dialog.",
                )
                # Reset focus + counters
                self.imported_thesis_ids = []
                self.imported_opposing_ids = []
                self.focus_thesis_id = None
                self.focus_opposing_id = None
                return
            else:
                # Uživatel chce přesto uložit → zopakuj v dalším batch BEZ raise
                # POZOR: po předchozím raise je _db reloadnutý z disku, takže
                # musíme všechno provést znova. Pro jednoduchost: 2× run.
                self._execute_import_retry_silent(
                    active_rows, csv_source, stats, errors
                )
        except Exception as exc:  # noqa: BLE001
            # Jakákoli jiná neočekávaná chyba — rollback už proběhl
            QMessageBox.critical(
                self,
                "Import selhal",
                f"Při importu došlo k neočekávané chybě, žádné změny nebyly "
                f"uloženy:\n\n{exc}",
            )
            return

        # 4) Úspěch — zapamatuj focus, mazání originálu, sumář
        self.imported_thesis_ids = affected_thesis_ids
        self.imported_opposing_ids = affected_opposing_ids
        self.focus_thesis_id = last_thesis_id
        self.focus_opposing_id = last_opposing_id
        try:
            self.service.auto_link_retakes()  # propoj řádný + opravný pokus
        except Exception:  # noqa: BLE001
            pass
        self._maybe_delete_source_csv(csv_source, stats)
        self._show_summary_dialog(stats, errors)

    def _maybe_delete_source_csv(self, csv_source: Path | None, stats: dict) -> None:
        """Po úspěšném importu smaže originální CSV soubor, je-li zaškrtnuto.

        Důvod proč až tady (a ne uvnitř ``attach_document(delete_source=True)``):
        CSV se připojí ke každé importované práci — pokud bychom smazali
        po prvním attach, druhý attach by selhal s ``FileNotFoundError``.
        Mazáme tedy jednorázově po dokončení všech přiloh.
        """
        stats.setdefault("source_csv_deleted", 0)
        if not self.chk_delete_csv.isChecked():
            return
        if csv_source is None or not csv_source.is_file():
            return
        try:
            csv_source.unlink()
            stats["source_csv_deleted"] = 1
        except OSError:
            stats["source_csv_deleted"] = 0

    def _attach_downloaded_files(
        self,
        thesis_by_adip: dict[str, str],
        opposing_by_adip: dict[str, str],
        stats: dict,
        errors: list[str],
    ) -> None:
        """Připojí soubory stažené ze STAG k odpovídající práci (přes adipIdno).

        U oponentských posudků navíc dosynchronizuje známky (z PDF posudku
        vedoucího se vyčte navržená známka).
        """
        if not self._stag_downloaded_files:
            return
        for adip, files in self._stag_downloaded_files.items():
            tid = thesis_by_adip.get(adip)
            oid = opposing_by_adip.get(adip)
            if not tid and not oid:
                continue
            for f in files:
                if not (f.path and f.path.exists()):
                    continue
                try:
                    if tid:
                        self.service.attach_document(tid, f.path, kind=f.kind)
                    else:
                        self.service.opposing_attach_document(oid, f.path, kind=f.kind)
                    stats["attached_files"] += 1
                except Exception as exc:  # noqa: BLE001
                    errors.append(f"Přiložení souboru {f.filename}: {exc}")
            if oid:
                try:
                    self.service.sync_opposing_grades(oid)
                except Exception:  # noqa: BLE001
                    pass
            if tid:
                try:
                    self.service.sync_thesis_grades(tid)
                except Exception:  # noqa: BLE001
                    pass

    # --- pomocné helpers k importu --------------------------------------

    def _ask_continue_with_errors(
        self, errors: list[str], stats: dict
    ) -> str:
        """Při chybách v batch — uživatel se rozhodne mezi rollback a continue.

        Vrací: ``"rollback"`` nebo ``"keep"``.
        """
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle("Při importu nastaly chyby")
        msg.setText(
            f"Při importu nastalo {len(errors)} "
            f"{self._cs_plural(len(errors), 'chyba', 'chyby', 'chyb')}."
        )
        details = "\n".join(f"• {e}" for e in errors[:30])
        if len(errors) > 30:
            details += f"\n… a {len(errors) - 30} dalších"
        msg.setDetailedText(details)
        msg.setInformativeText(
            "Žádná data zatím nebyla uložena. Co chceš udělat?"
        )
        btn_rollback = msg.addButton(
            "↩ Zrušit import (rollback)", QMessageBox.ButtonRole.RejectRole
        )
        btn_keep = msg.addButton(
            "✓ Uložit i tak (jen úspěšné řádky)", QMessageBox.ButtonRole.AcceptRole
        )
        msg.setDefaultButton(btn_rollback)
        msg.exec()
        return "rollback" if msg.clickedButton() == btn_rollback else "keep"

    def _execute_import_retry_silent(
        self,
        active_rows: list[dict],
        csv_source: Path | None,
        stats: dict,
        prev_errors: list[str],
    ) -> None:
        """Zopakuje import po rollbacku — pro variantu „Uložit i tak"."""
        # Reset stats — předchozí pokus je zahozený
        for k in stats:
            stats[k] = 0
        errors: list[str] = []
        affected_thesis_ids: list[str] = []
        affected_opposing_ids: list[str] = []
        thesis_csv: dict[str, str] = {}
        opposing_csv: dict[str, str] = {}
        thesis_by_adip: dict[str, str] = {}
        opposing_by_adip: dict[str, str] = {}
        last_thesis_id: str | None = None
        last_opposing_id: str | None = None

        with self.service.batch():
            for widget_set in active_rows:
                record: ParsedRecord = widget_set["record"]
                role = ImportRole(widget_set["cb_role"].currentData())
                obor_choice = widget_set["cb_obor"].currentData()
                obor_name = (
                    obor_choice
                    if obor_choice not in ("__keep__", "__new__")
                    else (record.student_obor_stag or "")
                )
                status = ThesisStatus(widget_set["cb_status"].currentData())
                try:
                    if role == ImportRole.SUPERVISOR:
                        tid, _ = self._apply_supervisor_role(
                            record, obor_name, status, stats
                        )
                        affected_thesis_ids.append(tid)
                        if record.source_csv:
                            thesis_csv[tid] = record.source_csv
                        if record.adipidno:
                            thesis_by_adip[record.adipidno] = tid
                        last_thesis_id = tid
                    else:
                        oid, _ = self._apply_opponent_role(record, obor_name, stats)
                        affected_opposing_ids.append(oid)
                        if record.source_csv:
                            opposing_csv[oid] = record.source_csv
                        if record.adipidno:
                            opposing_by_adip[record.adipidno] = oid
                        last_opposing_id = oid
                except Exception as exc:  # noqa: BLE001
                    errors.append(
                        f"{record.student_last} {record.student_first}: {exc}"
                    )
            for tid in affected_thesis_ids:
                src = Path(thesis_csv[tid]) if tid in thesis_csv else csv_source
                if not (src and src.exists()):
                    continue
                try:
                    self.service.attach_document(
                        tid, src, kind=AttachmentKind.STAG_EXPORT
                    )
                    stats["attached_csv"] += 1
                except Exception:
                    pass
            for oid in affected_opposing_ids:
                src = Path(opposing_csv[oid]) if oid in opposing_csv else csv_source
                if not (src and src.exists()):
                    continue
                try:
                    self.service.opposing_attach_document(
                        oid, src, kind=AttachmentKind.STAG_EXPORT
                    )
                    stats["attached_csv"] += 1
                except Exception:
                    pass

            # Soubory stažené ze STAG (text/přílohy/posudky)
            self._attach_downloaded_files(
                thesis_by_adip, opposing_by_adip, stats, errors
            )

        self.imported_thesis_ids = affected_thesis_ids
        self.imported_opposing_ids = affected_opposing_ids
        self.focus_thesis_id = last_thesis_id
        self.focus_opposing_id = last_opposing_id
        try:
            self.service.auto_link_retakes()  # propoj řádný + opravný pokus
        except Exception:  # noqa: BLE001
            pass
        self._maybe_delete_source_csv(csv_source, stats)
        self._show_summary_dialog(stats, errors)

    def _show_summary_dialog(self, stats: dict, errors: list[str]) -> None:
        """Závěrečný sumář s tlačítky pro přepnutí na práci."""
        from html import escape as _esc

        rows: list[str] = []
        rows.append(
            f"<tr><td>📚 <b>Vedené práce</b></td>"
            f"<td>{stats['created_thesis']} vytvořeno</td>"
            f"<td>{stats['updated_thesis']} aktualizováno</td></tr>"
        )
        rows.append(
            f"<tr><td>🧐 <b>Oponentské posudky</b></td>"
            f"<td>{stats['created_opposing']} vytvořeno</td>"
            f"<td>{stats['updated_opposing']} aktualizováno</td></tr>"
        )
        rows.append(
            f"<tr><td>👨‍🎓 Noví studenti</td>"
            f"<td colspan='2'>{stats['created_student']}</td></tr>"
        )
        rows.append(
            f"<tr><td>🧐 Noví oponenti</td>"
            f"<td colspan='2'>{stats['created_opponent']}</td></tr>"
        )
        rows.append(
            f"<tr><td>🎓 Noví vedoucí</td>"
            f"<td colspan='2'>{stats['created_supervisor']}</td></tr>"
        )
        rows.append(
            f"<tr><td>📎 CSV přiloženo k pracem</td>"
            f"<td colspan='2'>{stats['attached_csv']}</td></tr>"
        )
        rows.append(
            f"<tr><td>📄 Soubory ze STAG přiloženy</td>"
            f"<td colspan='2'>{stats.get('attached_files', 0)}</td></tr>"
        )
        if stats.get("source_csv_deleted"):
            rows.append(
                "<tr><td>🗑 Originální CSV smazán</td>"
                "<td colspan='2'>✓</td></tr>"
            )
        rows.append(
            f"<tr><td>✗ Přeskočeno</td>"
            f"<td colspan='2'>{stats['skipped']}</td></tr>"
        )

        html = (
            "<style>"
            "table.summary { border-collapse: collapse; }"
            "table.summary td { padding: 4px 12px 4px 0; }"
            "</style>"
            "<p style='color:#2e7d32;'>✓ Import dokončen.</p>"
            f"<table class='summary'>{''.join(rows)}</table>"
        )
        if errors:
            err_items = "".join(f"<li>{_esc(e)}</li>" for e in errors[:15])
            extra = f"<p style='color:#888;'>… a {len(errors) - 15} dalších</p>" if len(errors) > 15 else ""
            html += (
                f"<hr><p><b>⚠ Chyby ({len(errors)}):</b></p>"
                f"<ul>{err_items}</ul>{extra}"
            )

        dlg = QDialog(self)
        dlg.setWindowTitle("Import dokončen")
        dlg.setMinimumSize(560, 420)
        outer = QVBoxLayout(dlg)
        header = QLabel("📥 Import ze STAG dokončen")
        header.setStyleSheet("font-weight:bold;font-size:14px;")
        outer.addWidget(header)
        body = QTextBrowser()
        body.setHtml(html)
        outer.addWidget(body, stretch=1)

        btn_row = QHBoxLayout()
        btn_close = QPushButton("Zavřít")
        btn_close.clicked.connect(dlg.accept)

        # Pokud byl importován pouze jeden záznam, nabídni „Přepnout na práci".
        # Pokud více, ukaž tlačítko jen pokud je k tomu jediný thesis_id / opposing_id.
        has_focus = bool(self.focus_thesis_id or self.focus_opposing_id)

        # Záchranná brzda — vrátit celý import ze zálohy před importem.
        if self._preimport_backup_file and self._preimport_data_dir:
            btn_revert = QPushButton("↩ Vrátit celý import zpět")
            btn_revert.setToolTip(
                "Obnoví stav databáze ze zálohy pořízené TĚSNĚ PŘED tímto "
                "importem — odstraní vše, co tento import přidal/změnil."
            )
            btn_revert.clicked.connect(lambda: self._revert_import(dlg))
            btn_row.addWidget(btn_revert)

        btn_row.addStretch()
        btn_row.addWidget(btn_close)
        if has_focus:
            btn_focus = QPushButton("👁 Zobrazit práci")
            btn_focus.setDefault(True)
            f = btn_focus.font()
            f.setBold(True)
            btn_focus.setFont(f)
            # Klik = zavře dialog s navigací; MainWindow přečte focus_*_id atributy.
            btn_focus.clicked.connect(dlg.accept)
            btn_row.addWidget(btn_focus)
        else:
            # Bez focusu — zruš auto-navigaci
            self.focus_thesis_id = None
            self.focus_opposing_id = None

        outer.addLayout(btn_row)
        dlg.exec()
        # Dialog (StagImportDialog) potvrď — MainWindow přečte focus_*_id
        self.accept()

    def _revert_import(self, summary_dlg: QDialog) -> None:
        """Vrátí celý import — obnoví db.json ze zálohy před importem."""
        if not (self._preimport_backup_file and self._preimport_data_dir):
            return
        confirm = QMessageBox.question(
            self,
            "Vrátit celý import?",
            "Obnoví se stav databáze ze zálohy pořízené těsně před tímto "
            "importem. <b>Vše, co tento import přidal nebo změnil, zmizí.</b>"
            "<br><br>Aktuální (importovaný) stav se předtím ještě zazálohuje "
            "(<code>before-restore</code>), takže krok jde i vrátit.<br><br>"
            "<small>Pozn.: soubory zkopírované do složky dokumentů zůstanou na "
            "disku jako osiřelé (bez vazby v DB) — neškodí.</small>",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        try:
            BackupManager(self._preimport_data_dir).restore_backup(
                self._preimport_backup_file, self._preimport_data_dir / "db.json"
            )
            self.service.reload()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(
                self, "Vrácení selhalo",
                f"Obnovu ze zálohy se nepodařilo provést:\n{exc}",
            )
            return
        # Zruš navigaci na (už neexistující) importované práce.
        self.focus_thesis_id = None
        self.focus_opposing_id = None
        self.imported_thesis_ids = []
        self.imported_opposing_ids = []
        self.reverted = True
        QMessageBox.information(
            self, "Import vrácen",
            "Stav databáze byl obnoven do podoby před importem.",
        )
        summary_dlg.accept()

    # --- per-role logic ------------------------------------------------------

    def _apply_supervisor_role(
        self,
        record: ParsedRecord,
        obor_name: str,
        status: ThesisStatus,
        stats: dict,
    ) -> tuple[str, bool]:
        """Vytvoří/aktualizuje vedenou Thesis.

        Vrací ``(thesis_id, is_new)``.
        """
        # 1) Student
        student = self._ensure_student(record, obor_name, stats)

        # 2) Opponent (z registry)
        opponent = self._ensure_opponent(record.opponent_name, stats) \
            if record.opponent_name else None

        # 3) Najdi existující práci (univ_id + year + type)
        existing = self._find_existing_thesis(student.id, record)
        is_new = existing is None
        thesis = existing or Thesis(
            type=ThesisType(record.type_code),
            status=status,
            academic_year=record.academic_year,
        )

        # 4) Naplň pole — preferujeme nové údaje (STAG má autoritativní data)
        thesis.student_id = student.id
        thesis.opponent_id = opponent.id if opponent else thesis.opponent_id
        thesis.type = ThesisType(record.type_code)
        thesis.academic_year = record.academic_year
        if is_new:
            thesis.status = status  # u nových volíme z dialogu; existující neměníme
        thesis.title_cs = record.title_cs or thesis.title_cs
        thesis.title_en = record.title_en or thesis.title_en
        thesis.annotation = record.annotation_cs or thesis.annotation
        thesis.annotation_en = record.annotation_en or thesis.annotation_en
        thesis.objectives = record.objectives_text or thesis.objectives
        thesis.references = record.references_text or thesis.references
        if record.adipidno:
            thesis.adipidno = record.adipidno

        self.service.upsert_thesis(thesis)
        if is_new:
            stats["created_thesis"] += 1
        else:
            stats["updated_thesis"] += 1
        return thesis.id, is_new

    def _apply_opponent_role(
        self,
        record: ParsedRecord,
        obor_name: str,
        stats: dict,
    ) -> tuple[str, bool]:
        """Vytvoří/aktualizuje OpposingThesis.

        Vrací ``(opposing_id, is_new)``.
        """
        # Vedoucí v registru
        supervisor = self._ensure_supervisor(record.supervisor_name, stats) \
            if record.supervisor_name else None

        # Najdi existující posudek
        existing = self._find_existing_opposing(record)
        is_new = existing is None
        op = existing or OpposingThesis(
            type=ThesisType(record.type_code),
            academic_year=record.academic_year,
        )

        op.type = ThesisType(record.type_code)
        op.academic_year = record.academic_year
        op.student_first_name = record.student_first or op.student_first_name
        op.student_last_name = record.student_last or op.student_last_name
        op.student_obor = obor_name or op.student_obor
        op.student_university_id = record.student_uni_id or op.student_university_id
        op.supervisor_name = record.supervisor_name or op.supervisor_name
        op.supervisor_email = (
            (supervisor.email if supervisor else "")
            or op.supervisor_email
        )
        op.title_cs = record.title_cs or op.title_cs
        op.objectives = record.objectives_text or op.objectives
        op.grade_supervisor = record.grade_supervisor or op.grade_supervisor
        op.grade_opponent = record.grade_opponent or op.grade_opponent
        if record.adipidno:
            op.adipidno = record.adipidno

        self.service.upsert_opposing_thesis(op)
        if is_new:
            stats["created_opposing"] += 1
        else:
            stats["updated_opposing"] += 1
        return op.id, is_new

    # --- entity ensure helpers -----------------------------------------------

    def _ensure_student(
        self, record: ParsedRecord, obor_name: str, stats: dict
    ) -> Student:
        """Najdi (podle uni_id) nebo vytvoř studenta."""
        uni_id = record.student_uni_id.strip()
        if uni_id:
            for s in self.service.list_students():
                if s.university_id == uni_id:
                    # Aktualizuj jméno/obor, pokud se liší
                    changed = False
                    if record.student_first and s.first_name != record.student_first:
                        s.first_name = record.student_first
                        changed = True
                    if record.student_last and s.last_name != record.student_last:
                        s.last_name = record.student_last
                        changed = True
                    if obor_name and s.obor != obor_name:
                        s.obor = obor_name
                        changed = True
                    if changed:
                        self.service.upsert_student(s)
                    return s
        # Vytvoř nového — pokud uživatel studenta předem zrevidoval/doplnil,
        # použij jeho objekt (jen dorovnej prázdná pole z dat STAG).
        reviewed = self._reviewed_students.get(uni_id) if uni_id else None
        if reviewed is not None:
            s = reviewed
            s.first_name = s.first_name or record.student_first
            s.last_name = s.last_name or record.student_last
            if not s.obor:
                s.obor = obor_name
            if not s.university_id:
                s.university_id = uni_id or None
            if s.obor:
                self.service.add_obor(s.obor)
        else:
            s = Student(
                first_name=record.student_first,
                last_name=record.student_last,
                obor=obor_name,
                university_id=uni_id or None,
            )
        self.service.upsert_student(s)
        stats["created_student"] += 1
        return s

    def _review_new_students(
        self, active_rows: list[dict]
    ) -> dict[str, Student] | None:
        """Otevře kartu studenta pro každého *nového* studenta vedené práce.

        Vrací slovník ``{osobní_číslo: Student}`` s doplněnými daty (zápis se
        provede až v dávce importu), nebo ``None`` pokud uživatel revizi zrušil
        a chce celý import přerušit.
        """
        from .student_dialog import StudentDialog

        existing_by_uni = {
            s.university_id: s
            for s in self.service.list_students()
            if s.university_id
        }
        reviewed: dict[str, Student] = {}
        seen: set[str] = set()

        for ws in active_rows:
            record: ParsedRecord = ws["record"]
            if ImportRole(ws["cb_role"].currentData()) != ImportRole.SUPERVISOR:
                continue
            uni_id = record.student_uni_id.strip()
            if not uni_id or uni_id in existing_by_uni or uni_id in seen:
                continue
            seen.add(uni_id)

            obor_choice = ws["cb_obor"].currentData()
            obor_name = (
                obor_choice
                if obor_choice not in ("__keep__", "__new__")
                else (record.student_obor_stag or "")
            )
            prefilled = Student(
                first_name=record.student_first,
                last_name=record.student_last,
                obor=obor_name,
                university_id=uni_id,
            )
            dlg = StudentDialog(
                self.service, prefilled, parent=self, persist=False
            )
            label = f"{record.student_last} {record.student_first}".strip()
            dlg.setWindowTitle(f"Doplnit studenta — {label}" if label else "Doplnit studenta")
            if dlg.exec() == QDialog.DialogCode.Accepted:
                reviewed[uni_id] = dlg.student
            else:
                choice = QMessageBox.question(
                    self,
                    "Přeskočit revizi?",
                    "Revize tohoto studenta byla zrušena.\n\n"
                    "Pokračovat v importu s automaticky vyplněnými údaji "
                    "(jméno, obor, osobní číslo)?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                    QMessageBox.StandardButton.Yes,
                )
                if choice == QMessageBox.StandardButton.Cancel:
                    return None
                reviewed[uni_id] = prefilled
        return reviewed

    def _ensure_opponent(self, name: str, stats: dict) -> Opponent | None:
        """Najdi (podle jména) nebo vytvoř oponenta v registru."""
        name = (name or "").strip()
        if not name:
            return None
        for o in self.service.list_opponents():
            if o.name == name:
                return o
        # Vytvoř — default jako interní (lze přepsat)
        opp = Opponent(kind=OpponentKind.INTERNAL, name=name)
        self.service.upsert_opponent(opp)
        stats["created_opponent"] += 1
        return opp

    def _ensure_supervisor(self, name: str, stats: dict) -> Supervisor | None:
        """Najdi (podle jména) nebo vytvoř vedoucího v registru."""
        name = (name or "").strip()
        if not name:
            return None
        for sup in self.service.list_supervisors():
            if sup.name == name:
                return sup
        sup = Supervisor(name=name)
        self.service.upsert_supervisor(sup)
        stats["created_supervisor"] += 1
        return sup

    def _find_existing_thesis(self, student_id: str, record: ParsedRecord) -> Thesis | None:
        # 1) Přesná shoda přes STAG ID práce (adipidno) — nejspolehlivější.
        if record.adipidno:
            for t in self.service.list_theses():
                if t.adipidno and t.adipidno == record.adipidno:
                    return t
        # 2) Fallback: student + rok + typ (BP≠DP → samostatné záznamy).
        #    POZOR: práci, která má JINÉ adipidno, nikdy nepřepiš — jde
        #    o jinou práci (typicky repetent: řádný + opravný pokus téhož
        #    studenta ve stejném roce, ale jiné STAG ID).
        for t in self.service.list_theses():
            if t.adipidno and record.adipidno and t.adipidno != record.adipidno:
                continue
            if (
                t.student_id == student_id
                and t.academic_year == record.academic_year
                and t.type.value == record.type_code
            ):
                return t
        return None

    def _find_existing_opposing(self, record: ParsedRecord) -> OpposingThesis | None:
        if record.adipidno:
            for o in self.service.list_opposing_theses():
                if o.adipidno and o.adipidno == record.adipidno:
                    return o
        uni_id = record.student_uni_id.strip()
        for o in self.service.list_opposing_theses():
            if o.adipidno and record.adipidno and o.adipidno != record.adipidno:
                continue
            if (
                o.student_university_id == uni_id
                and o.academic_year == record.academic_year
                and o.type.value == record.type_code
            ):
                return o
        return None


class StagFilesPreviewDialog(QDialog):
    """Náhled souborů stažených ze STAG — výběr, co importovat, a typ přílohy.

    Soubory přijdou předzaškrtnuté (lze odznačit) a s typem přílohy odhadnutým
    z původní STAG sekce. Typ lze ručně přepsat (fallback při chybě detekce).
    Dialog mutuje předané ``_DownloadedStagFile`` objekty (``selected`` + ``kind``).
    """

    def __init__(
        self,
        groups: list[tuple[str, list[_DownloadedStagFile]]],
        parent=None,
        *,
        intro: str = "",
    ) -> None:
        super().__init__(parent)
        self._rows: list[tuple[_DownloadedStagFile, QComboBox, int]] = []

        self.setWindowTitle("Soubory ke stažení ze STAG")
        self.setMinimumSize(720, 460)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 14, 14, 14)
        outer.setSpacing(10)

        title = QLabel("📎 Soubory práce ze STAG")
        title.setStyleSheet("font-size:16px;font-weight:bold;")
        outer.addWidget(title)

        lead = QLabel(
            intro
            or "Vyber, které soubory importovat. Typ přílohy je odhadnutý "
            "ze STAG — pokud nesedí, přepiš ho v posledním sloupci."
        )
        lead.setWordWrap(True)
        lead.setStyleSheet("color:#888;")
        outer.addWidget(lead)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["", "Práce", "Soubor", "Velikost", "Typ přílohy"]
        )
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)

        combo_qss = (
            "QComboBox { background-color: palette(base); color: palette(text); "
            "border: 1px solid palette(mid); border-radius: 3px; padding: 2px 4px; }"
            "QComboBox QAbstractItemView { background-color: palette(base); "
            "color: palette(text); }"
        )

        for header, files in groups:
            for f in files:
                row = self.table.rowCount()
                self.table.insertRow(row)

                chk = QTableWidgetItem()
                chk.setFlags(
                    Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled
                )
                chk.setCheckState(
                    Qt.CheckState.Checked if f.selected else Qt.CheckState.Unchecked
                )
                self.table.setItem(row, 0, chk)

                self.table.setItem(row, 1, QTableWidgetItem(header))
                name_item = QTableWidgetItem(f.filename)
                name_item.setToolTip(f.filename)
                self.table.setItem(row, 2, name_item)
                size_item = QTableWidgetItem(_fmt_size(f.size))
                size_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(row, 3, size_item)

                cb_kind = QComboBox()
                cb_kind.setStyleSheet(combo_qss)
                for kind in _FILE_KIND_CHOICES:
                    cb_kind.addItem(kind.label, kind.value)
                idx = cb_kind.findData(f.kind.value)
                if idx >= 0:
                    cb_kind.setCurrentIndex(idx)
                self.table.setCellWidget(row, 4, cb_kind)

                self._rows.append((f, cb_kind, row))

        outer.addWidget(self.table, stretch=1)

        # ── Tlačítka (zaškrtnout/odznačit vše + potvrzení) ──────────────────
        row = QHBoxLayout()
        btn_all = QPushButton("☑ Vše")
        btn_all.clicked.connect(lambda: self._set_all(True))
        btn_none = QPushButton("☐ Nic")
        btn_none.clicked.connect(lambda: self._set_all(False))
        row.addWidget(btn_all)
        row.addWidget(btn_none)
        row.addStretch()
        btn_skip = QPushButton("Přeskočit soubory")
        btn_skip.clicked.connect(self.reject)
        btn_ok = QPushButton("✓ Importovat vybrané")
        bf = btn_ok.font()
        bf.setBold(True)
        btn_ok.setFont(bf)
        btn_ok.setDefault(True)
        btn_ok.clicked.connect(self._accept)
        row.addWidget(btn_skip)
        row.addWidget(btn_ok)
        outer.addLayout(row)

    def _set_all(self, checked: bool) -> None:
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        for _f, _cb, r in self._rows:
            item = self.table.item(r, 0)
            if item is not None:
                item.setCheckState(state)

    def _accept(self) -> None:
        for f, cb, r in self._rows:
            item = self.table.item(r, 0)
            f.selected = bool(item) and item.checkState() == Qt.CheckState.Checked
            f.kind = AttachmentKind(cb.currentData())
        self.accept()


class StagDownloadDialog(QDialog):
    """Vyhledání a stažení CSV s prací přímo ze STAG (stag.utb.cz).

    Replikuje veřejné *Prohlížení → Kvalifikační práce*: hledá podle příjmení
    studenta a (volitelně) příjmení vedoucího/oponenta, zobrazí seznam shod a
    stáhne CSV vybrané práce do dočasného souboru. Síťovou vrstvu řeší
    :mod:`bpdpmanager.services.stag_api` (UI nesahá na HTTP přímo).
    """

    def __init__(
        self, default_person_surname: str = "", parent=None, *, service=None,
        auto_role: str | None = None, user_full_name: str = "",
    ) -> None:
        super().__init__(parent)
        # Vícevýběr: ``result_items`` = stažené práce (cesta k CSV + STAG meta).
        self.result_items: list[tuple[Path, stag_api.StagThesisResult]] = []
        # Zpětná kompatibilita (první stažená) — některý starší kód to čte.
        self.result_path: Path | None = None
        self.result_meta: stag_api.StagThesisResult | None = None
        self._results: list[stag_api.StagThesisResult] = []
        self._service = service
        # Hromadný režim (moje vedené / oponentury) — filtrace dle celého jména.
        self._auto_role = auto_role
        self._user_full_name = user_full_name
        # Soubory stažené spolu s prací (klíč = adipIdno) — importér je připojí
        # k odpovídající práci po jejím založení.
        self.downloaded_files: dict[str, list[_DownloadedStagFile]] = {}
        # Režim „jen soubory" — soubory připojeny rovnou k existující práci v DB,
        # CSV import se neprovádí. MainWindow pak jen refreshne + naviguje.
        self.files_only_done = False
        self.focus_thesis_id: str | None = None
        self.focus_opposing_id: str | None = None

        self.setWindowTitle("Stáhnout práci ze STAG")
        self.setMinimumSize(740, 560)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 14, 14, 14)
        outer.setSpacing(10)

        title = QLabel("🌐 Stáhnout práci ze STAG")
        title.setStyleSheet("font-size:16px;font-weight:bold;")
        outer.addWidget(title)

        intro = QLabel(
            "Vyhledá veřejné záznamy kvalifikačních prací na "
            "<a href='https://stag.utb.cz'>stag.utb.cz</a> a stáhne jejich CSV. "
            "Hledat můžeš podle <b>příjmení studenta</b> (+ upřesnění vedoucím/"
            "oponentem), nebo <b>jen podle vedoucího/oponenta</b> — pak najde "
            "<b>všechny jeho práce</b> (historické i aktuální) a můžeš jich "
            "naimportovat víc najednou."
        )
        intro.setTextFormat(Qt.TextFormat.RichText)
        intro.setOpenExternalLinks(True)
        intro.setWordWrap(True)
        intro.setStyleSheet("color:#888;")
        outer.addWidget(intro)

        # ── Vyhledávací formulář ────────────────────────────────────────────
        form = QFormLayout()

        self.ed_student = QLineEdit()
        self.ed_student.setPlaceholderText("např. Pohanka (nepovinné při hledání dle vedoucího)")
        self.ed_student.returnPressed.connect(self._do_search)
        form.addRow("Příjmení studenta", self.ed_student)

        self.ed_person = QLineEdit(default_person_surname)
        self.ed_person.setPlaceholderText("např. Žáček (tvoje příjmení) — bez studenta najde VŠE")
        self.ed_person.returnPressed.connect(self._do_search)

        self.rb_supervisor = QRadioButton("Vedoucí")
        self.rb_opponent = QRadioButton("Oponent")
        self.rb_supervisor.setChecked(True)
        role_group = QButtonGroup(self)
        role_group.addButton(self.rb_supervisor)
        role_group.addButton(self.rb_opponent)
        person_row = QHBoxLayout()
        person_row.setContentsMargins(0, 0, 0, 0)
        person_row.addWidget(self.ed_person, stretch=1)
        self._role_label = QLabel("role:")
        person_row.addWidget(self._role_label)
        person_row.addWidget(self.rb_supervisor)
        person_row.addWidget(self.rb_opponent)
        person_widget = QWidget()
        person_widget.setLayout(person_row)
        self._person_form_label = QLabel("Příjmení vedoucího/oponenta")
        form.addRow(self._person_form_label, person_widget)

        outer.addLayout(form)

        self.btn_search = QPushButton("🔍 Vyhledat ve STAG")
        self.btn_search.clicked.connect(self._do_search)
        bf = self.btn_search.font()
        bf.setBold(True)
        self.btn_search.setFont(bf)
        outer.addWidget(self.btn_search)

        # ── Výsledky ────────────────────────────────────────────────────────
        self.lbl_status = QLabel("Zadej příjmení a klikni na „Vyhledat ve STAG\".")
        self.lbl_status.setStyleSheet("color:#888;")
        self.lbl_status.setWordWrap(True)
        outer.addWidget(self.lbl_status)

        self.list_results = QListWidget()
        self.list_results.itemChanged.connect(lambda _i: self._update_download_btn())
        outer.addWidget(self.list_results, stretch=1)

        # Filtr „jen moje práce" (dle celého jména) — past s více jmenovci.
        self.chk_only_mine = QCheckBox("Jen moje práce (filtrovat dle celého jména)")
        self.chk_only_mine.setChecked(bool(auto_role))
        self.chk_only_mine.setToolTip(
            "Příjmení nemusí být jednoznačné (víc vedoucích stejného příjmení). "
            "Zaškrtnuté = ponechá jen práce, kde je tvé celé jméno z profilu."
        )
        self.chk_only_mine.setVisible(bool(auto_role))
        self.chk_only_mine.stateChanged.connect(lambda _s: self._render_results())
        outer.addWidget(self.chk_only_mine)

        # ── Tlačítka ────────────────────────────────────────────────────────
        row = QHBoxLayout()
        btn_cancel = QPushButton("Zrušit")
        btn_cancel.clicked.connect(self.reject)
        self.btn_files_only = QPushButton("📎 Stáhnout jen soubory")
        self.btn_files_only.setEnabled(False)
        self.btn_files_only.setToolTip(
            "Stáhne jen soubory (text, přílohy, posudky) a připojí je k "
            "odpovídající práci, kterou už máš v databázi (CSV se neimportuje). "
            "Pokud práce v databázi není, upozorní."
        )
        self.btn_files_only.clicked.connect(self._download_files_only)
        self.btn_download = QPushButton("⬇ Stáhnout vybrané")
        self.btn_download.setEnabled(False)
        self.btn_download.setDefault(True)
        df = self.btn_download.font()
        df.setBold(True)
        self.btn_download.setFont(df)
        self.btn_download.setToolTip(
            "Stáhne CSV s prací i její soubory — v dalším kroku zvolíš, "
            "co naimportovat."
        )
        self.btn_download.clicked.connect(self._download_selected)
        row.addStretch()
        row.addWidget(btn_cancel)
        row.addWidget(self.btn_files_only)
        row.addWidget(self.btn_download)
        outer.addLayout(row)

        # Hromadný režim — uzamkni roli (žádné přepínání), vypni studenta
        # a rovnou hledej.
        if auto_role:
            what = "vedené práce" if auto_role == "supervisor" else "oponentury"
            role_word = "vedoucího" if auto_role == "supervisor" else "oponenta"
            self.setWindowTitle(f"Stáhnout moje {what} ze STAG")
            title.setText(f"🌐 Moje {what} ze STAG")
            self.ed_student.clear()
            self.ed_student.setEnabled(False)
            self.ed_student.setVisible(False)
            student_lbl = form.labelForField(self.ed_student)
            if student_lbl is not None:
                student_lbl.setVisible(False)
            if auto_role == "supervisor":
                self.rb_supervisor.setChecked(True)
            else:
                self.rb_opponent.setChecked(True)
            # Skryj přepínač role — dialog je zamčený na jednu roli.
            self._role_label.setVisible(False)
            self.rb_supervisor.setVisible(False)
            self.rb_opponent.setVisible(False)
            self._person_form_label.setText(f"Příjmení {role_word} (= tvoje)")
            self.ed_person.setPlaceholderText("tvé příjmení z profilu")
            QTimer.singleShot(0, self._do_search)

    # --- akce ----------------------------------------------------------------

    def _do_search(self) -> None:
        student = self.ed_student.text().strip()
        person = self.ed_person.text().strip()
        if not student and not person:
            QMessageBox.warning(
                self, "Chybí příjmení",
                "Zadej příjmení studenta, nebo příjmení vedoucího/oponenta "
                "(hromadné vyhledání všech jeho prací).",
            )
            self.ed_student.setFocus()
            return
        role = (
            stag_api.ROLE_SUPERVISOR
            if self.rb_supervisor.isChecked()
            else stag_api.ROLE_OPPONENT
        )

        self.list_results.clear()
        self._results = []
        self.btn_download.setEnabled(False)
        self.lbl_status.setText("⏳ Hledám ve STAG…")
        self.btn_search.setEnabled(False)
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        QApplication.processEvents()
        try:
            results = stag_api.search_theses(student, person, role)
        except stag_api.StagError as exc:
            QApplication.restoreOverrideCursor()
            self.btn_search.setEnabled(True)
            self.lbl_status.setText("⚠ Vyhledávání se nezdařilo.")
            QMessageBox.warning(self, "STAG", str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            QApplication.restoreOverrideCursor()
            self.btn_search.setEnabled(True)
            self.lbl_status.setText("⚠ Neočekávaná chyba.")
            QMessageBox.critical(
                self, "STAG", f"Neočekávaná chyba při vyhledávání:\n{exc}"
            )
            return
        finally:
            QApplication.restoreOverrideCursor()
            self.btn_search.setEnabled(True)

        self._results = results
        self._render_results()

    def _render_results(self) -> None:
        """Naplní seznam výsledků (s filtrem „jen moje" a řazením dle roku)."""
        raw = self._results
        self.list_results.blockSignals(True)
        self.list_results.clear()
        self.list_results.blockSignals(False)
        if not raw:
            self.lbl_status.setText(
                "Nenalezena žádná práce. Zkontroluj příjmení (i diakritiku)."
            )
            self._update_download_btn()
            return

        hidden = 0
        results = raw
        if (
            self._auto_role
            and self.chk_only_mine.isChecked()
            and self._user_full_name.strip()
        ):
            def _person(r):
                return r.supervisor if self._auto_role == "supervisor" else r.reviewer
            kept = [r for r in raw if _name_matches(_person(r), self._user_full_name)]
            hidden = len(raw) - len(kept)
            results = kept

        # Řazení dle akademického roku (nejnovější první).
        results = sorted(results, key=lambda r: (r.year or ""), reverse=True)

        existing_adip, existing_name_type = self._existing_keys()
        new_count = 0
        self.list_results.blockSignals(True)
        for r in results:
            is_existing = self._is_existing(r, existing_adip, existing_name_type)
            if not is_existing:
                new_count += 1
            badge = "✓ už máš" if is_existing else "🆕 nové"
            item = QListWidgetItem(f"{badge}   {r.display_label}")
            item.setData(Qt.ItemDataRole.UserRole, r.adipidno)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(
                Qt.CheckState.Unchecked if is_existing else Qt.CheckState.Checked
            )
            if is_existing:
                item.setForeground(QBrush(QColor("#888")))
            tooltip = [f"STAG ID práce: {r.adipidno}"]
            if r.supervisor:
                tooltip.append(f"Vedoucí: {r.supervisor}")
            if r.reviewer:
                tooltip.append(f"Oponent: {r.reviewer}")
            if is_existing:
                tooltip.append("Tuto práci už máš v databázi.")
            item.setToolTip("\n".join(tooltip))
            self.list_results.addItem(item)
        self.list_results.blockSignals(False)

        status = (
            f"✓ Zobrazeno: {len(results)} "
            f"{StagImportDialog._cs_plural(len(results), 'práce', 'práce', 'prací')}"
            f" ({new_count} nových)."
        )
        if hidden:
            status += (
                f"  ·  Skryto {hidden} prací jmenovců — zruš filtr „Jen moje "
                "práce“ pro zobrazení všech."
            )
        elif self._auto_role and not self.chk_only_mine.isChecked():
            status += "  ·  Bez filtru: zobrazeny i práce stejného příjmení jiných osob."
        self.lbl_status.setText(status)
        self._update_download_btn()

    # --- vícevýběr / odznaky -------------------------------------------------

    @staticmethod
    def _result_type_code(r: stag_api.StagThesisResult) -> str:
        lbl = (r.type_label or "").lower()
        if "diplom" in lbl:
            return "DP"
        if "bakal" in lbl:
            return "BP"
        return ""

    @staticmethod
    def _result_name_key(r: stag_api.StagThesisResult) -> tuple[str, str]:
        full = f"{r.name} {r.surname}".strip().lower()
        return (full, StagDownloadDialog._result_type_code(r))

    def _existing_keys(self) -> tuple[set[str], set[tuple[str, str]]]:
        """Vrátí (množina adipidno v DB, množina (jméno, typ) v DB)."""
        adip: set[str] = set()
        name_type: set[tuple[str, str]] = set()
        svc = self._service
        if svc is None:
            return adip, name_type
        try:
            for t in svc.list_theses():
                if t.adipidno:
                    adip.add(t.adipidno)
                student = svc.get_student(t.student_id) if t.student_id else None
                if student:
                    name_type.add((student.full_name.strip().lower(), t.type.value))
            for o in svc.list_opposing_theses():
                if o.adipidno:
                    adip.add(o.adipidno)
                name_type.add((o.student_full_name.strip().lower(), o.type.value))
        except Exception:  # noqa: BLE001
            pass
        return adip, name_type

    def _is_existing(
        self,
        r: stag_api.StagThesisResult,
        existing_adip: set[str],
        existing_name_type: set[tuple[str, str]],
    ) -> bool:
        if r.adipidno and r.adipidno in existing_adip:
            return True
        key = self._result_name_key(r)
        return key[1] != "" and key in existing_name_type

    def _checked_results(self) -> list[stag_api.StagThesisResult]:
        out: list[stag_api.StagThesisResult] = []
        for i in range(self.list_results.count()):
            item = self.list_results.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                adip = item.data(Qt.ItemDataRole.UserRole)
                r = next((x for x in self._results if x.adipidno == adip), None)
                if r is not None:
                    out.append(r)
        return out

    def _update_download_btn(self) -> None:
        n = len(self._checked_results())
        self.btn_download.setEnabled(n > 0)
        self.btn_download.setText(
            "⬇ Stáhnout vybrané" if n == 0 else f"⬇ Stáhnout vybrané ({n})"
        )
        # „Jen soubory" má smysl jen když máme službu (k dohledání práce v DB).
        self.btn_files_only.setEnabled(n > 0 and self._service is not None)

    def _download_selected(self) -> None:
        results = self._checked_results()
        if not results:
            return

        self.btn_download.setEnabled(False)
        self.btn_files_only.setEnabled(False)
        items: list[tuple[Path, stag_api.StagThesisResult]] = []
        errors: list[str] = []
        files_by_adip: dict[str, list[_DownloadedStagFile]] = {}
        listings: dict[str, list[stag_api.StagFile]] = {}
        # Jeden klient (session) na celé stažení — odkaz na soubor je vázán
        # na session, kterou založí dotaz na detail práce.
        client = stag_api.StagClient()

        # Fáze 1: stáhni CSV a vypiš soubory (bez stahování jejich obsahu).
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        QApplication.processEvents()
        try:
            for result in results:
                try:
                    data = client.download_csv(result.adipidno)
                except Exception as exc:  # noqa: BLE001
                    errors.append(f"{result.student_full}: {exc}")
                    continue
                surname = result.surname or "prace"
                safe = re.sub(r"[^0-9A-Za-zÀ-ž_-]+", "_", surname).strip("_") or "prace"
                target = (
                    Path(tempfile.gettempdir())
                    / f"stag_{safe}_{result.adipidno}.csv"
                )
                try:
                    target.write_bytes(data)
                except OSError as exc:
                    errors.append(f"{result.student_full}: zápis CSV: {exc}")
                    continue
                items.append((target, result))
                listings[result.adipidno] = self._list_files_for(client, result)
        finally:
            QApplication.restoreOverrideCursor()

        if not items:
            self.btn_download.setEnabled(True)
            self._update_download_btn()
            QMessageBox.warning(
                self, "STAG",
                "Nepodařilo se stáhnout žádnou práci.\n\n" + "\n".join(errors),
            )
            return
        if errors:
            QMessageBox.warning(
                self, "STAG",
                "Některé práce se nepodařilo stáhnout:\n\n" + "\n".join(errors),
            )

        # Fáze 2: varování u velkých příloh (mimo čekací kurzor — ptá se uživatele).
        skip_ids = self._confirm_oversized(
            {r.adipidno: listings.get(r.adipidno, []) for (_, r) in items}
        )

        # Fáze 3: stáhni soubory (text, přílohy, posudky), velké přeskoč dle volby.
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        QApplication.processEvents()
        try:
            for _, result in items:
                dl = self._download_listed(
                    client, result, listings.get(result.adipidno, []), skip_ids
                )
                if dl:
                    files_by_adip[result.adipidno] = dl
        finally:
            QApplication.restoreOverrideCursor()

        # Náhled stažených souborů — výběr, co naimportovat (default vše).
        self.downloaded_files = self._preview_and_pick(
            [(self._group_label(r), files_by_adip[r.adipidno])
             for (_, r) in items if r.adipidno in files_by_adip],
            files_by_adip,
        )

        self.result_items = items
        self.result_path = items[0][0]   # zpětná kompatibilita
        self.result_meta = items[0][1]
        self.accept()

    def _download_files_only(self) -> None:
        """Stáhne jen soubory a připojí je k odpovídající práci v DB."""
        results = self._checked_results()
        if not results or self._service is None:
            return

        self.btn_download.setEnabled(False)
        self.btn_files_only.setEnabled(False)
        files_by_adip: dict[str, list[_DownloadedStagFile]] = {}
        # (result, thesis_id|None, opposing_id|None, vypsané soubory)
        matched: list[
            tuple[stag_api.StagThesisResult, str | None, str | None, list[stag_api.StagFile]]
        ] = []
        unmatched: list[stag_api.StagThesisResult] = []
        no_files: list[stag_api.StagThesisResult] = []
        client = stag_api.StagClient()

        # Fáze 1: vypiš soubory + dohledej práci v DB (bez stahování obsahu).
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        QApplication.processEvents()
        try:
            for result in results:
                stag_files = self._list_files_for(client, result)
                if not stag_files:
                    no_files.append(result)
                    continue
                thesis_id, op_id = self._find_db_target(result)
                if not thesis_id and not op_id:
                    unmatched.append(result)
                    continue
                matched.append((result, thesis_id, op_id, stag_files))
        finally:
            QApplication.restoreOverrideCursor()

        # Fáze 2: varování u velkých příloh.
        skip_ids = self._confirm_oversized(
            {r.adipidno: sf for r, _, _, sf in matched}
        )

        # Fáze 3: stáhni soubory dohledaných prací (velké přeskoč dle volby).
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        QApplication.processEvents()
        try:
            for result, _tid, _oid, stag_files in matched:
                dl = self._download_listed(client, result, stag_files, skip_ids)
                if dl:
                    files_by_adip[result.adipidno] = dl
        finally:
            QApplication.restoreOverrideCursor()

        if not matched:
            self._update_download_btn()
            msg = "Soubory nebylo k čemu připojit."
            if unmatched:
                names = ", ".join(r.student_full for r in unmatched)
                msg += (
                    "\n\nTyto práce zatím nemáš v databázi (nejdřív je naimportuj "
                    f"přes „Stáhnout vybrané\"):\n{names}"
                )
            if no_files:
                names = ", ".join(r.student_full for r in no_files)
                msg += f"\n\nU těchto prací STAG nenabízí žádné soubory:\n{names}"
            QMessageBox.warning(self, "STAG — jen soubory", msg)
            return

        # Náhled výběru souborů (jen práce, kde se nějaké soubory stáhly)
        picked = self._preview_and_pick(
            [
                (self._group_label(r), files_by_adip[r.adipidno])
                for r, _, _, _ in matched
                if r.adipidno in files_by_adip
            ],
            files_by_adip,
            intro="Vyber soubory k připojení k odpovídající práci v databázi.",
        )

        attached = 0
        attach_errors: list[str] = []
        last_thesis_id: str | None = None
        last_opposing_id: str | None = None
        for result, thesis_id, op_id, _stag_files in matched:
            for f in picked.get(result.adipidno, []):
                try:
                    if thesis_id:
                        self._service.attach_document(thesis_id, f.path, kind=f.kind)
                    else:
                        self._service.opposing_attach_document(op_id, f.path, kind=f.kind)
                    attached += 1
                except Exception as exc:  # noqa: BLE001
                    attach_errors.append(f"{result.student_full} / {f.filename}: {exc}")
            if op_id:
                try:
                    self._service.sync_opposing_grades(op_id)
                except Exception:  # noqa: BLE001
                    pass
                last_opposing_id = op_id
            if thesis_id:
                try:
                    self._service.sync_thesis_grades(thesis_id)
                except Exception:  # noqa: BLE001
                    pass
                last_thesis_id = thesis_id

        if attached == 0 and not attach_errors:
            self._update_download_btn()
            QMessageBox.information(
                self, "STAG — jen soubory",
                "Žádné soubory nebyly vybrány k importu.",
            )
            return

        summary = [f"✓ Připojeno souborů: {attached}"]
        if unmatched:
            summary.append(
                "⚠ Bez odpovídající práce v DB: "
                + ", ".join(r.student_full for r in unmatched)
            )
        if no_files:
            summary.append(
                "• Bez souborů ve STAG: " + ", ".join(r.student_full for r in no_files)
            )
        if attach_errors:
            summary.append("⚠ Chyby:\n" + "\n".join(attach_errors))
        QMessageBox.information(self, "STAG — jen soubory", "\n\n".join(summary))

        self.files_only_done = True
        self.focus_thesis_id = last_thesis_id
        self.focus_opposing_id = last_opposing_id if not last_thesis_id else None
        self.accept()

    # --- stahování souborů ---------------------------------------------------

    def _list_files_for(
        self, client: stag_api.StagClient, result: stag_api.StagThesisResult
    ) -> list[stag_api.StagFile]:
        """Vypíše veřejné soubory práce (bez stahování obsahu)."""
        try:
            return client.list_thesis_files(result.adipidno)
        except Exception:  # noqa: BLE001
            return []

    def _confirm_oversized(
        self, listings: dict[str, list[stag_api.StagFile]]
    ) -> set[str]:
        """Pokud jsou ve výpisu velké přílohy, dá varování a vrátí ``soubidno``
        těch, které má uživatel přeskočit (zvolil „Přeskočit velké").
        """
        big = [
            sf
            for files in listings.values()
            for sf in files
            if sf.size_hint >= _LARGE_FILE_BYTES
        ]
        if not big:
            return set()
        lines = "\n".join(
            f"• {sf.filename} — {_fmt_size(sf.size_hint)}" for sf in big
        )
        total = sum(sf.size_hint for sf in big)
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle("Velké přílohy ze STAG")
        msg.setText(
            f"{len(big)} {self._cs_plural(len(big), 'příloha je velká', 'přílohy jsou velké', 'příloh je velkých')} "
            f"(celkem ~{_fmt_size(total)}):"
        )
        msg.setInformativeText(lines + "\n\nStáhnout je i tak?")
        btn_dl = msg.addButton("⬇ Stáhnout i tak", QMessageBox.ButtonRole.AcceptRole)
        btn_skip = msg.addButton(
            "Přeskočit velké", QMessageBox.ButtonRole.RejectRole
        )
        msg.setDefaultButton(btn_dl)
        msg.exec()
        if msg.clickedButton() == btn_skip:
            return {sf.soubidno for sf in big}
        return set()

    def _download_listed(
        self,
        client: stag_api.StagClient,
        result: stag_api.StagThesisResult,
        stag_files: list[stag_api.StagFile],
        skip_soubidno: set[str],
    ) -> list[_DownloadedStagFile]:
        """Stáhne dané (už vypsané) soubory do dočasného úložiště.

        Soubory ze ``skip_soubidno`` (uživatel je odmítl kvůli velikosti)
        přeskočí.
        """
        out: list[_DownloadedStagFile] = []
        for sf in stag_files:
            if sf.soubidno in skip_soubidno:
                continue
            try:
                data = client.download_file(sf.download_path)
            except Exception:  # noqa: BLE001
                continue
            safe = re.sub(r"[^0-9A-Za-zÀ-ž._-]+", "_", sf.filename).strip("_")
            if not safe:
                safe = f"soubor_{sf.soubidno}"
            target = (
                Path(tempfile.gettempdir())
                / f"stag_{result.adipidno}_{sf.soubidno}_{safe}"
            )
            try:
                target.write_bytes(data)
            except OSError:
                continue
            out.append(
                _DownloadedStagFile(
                    path=target,
                    filename=sf.filename,
                    kind=_SECTION_TO_KIND.get(sf.section, AttachmentKind.OTHER),
                    section=sf.section,
                    size=len(data),
                )
            )
        return out

    def _preview_and_pick(
        self,
        groups: list[tuple[str, list[_DownloadedStagFile]]],
        files_by_adip: dict[str, list[_DownloadedStagFile]],
        intro: str = "",
    ) -> dict[str, list[_DownloadedStagFile]]:
        """Zobrazí náhled souborů a vrátí jen vybrané (klíč = adipIdno).

        Když uživatel náhled přeskočí, vrátí prázdný výběr.
        """
        if not groups:
            return {}
        dlg = StagFilesPreviewDialog(groups, parent=self, intro=intro)
        accepted = dlg.exec() == QDialog.DialogCode.Accepted
        picked: dict[str, list[_DownloadedStagFile]] = {}
        for adip, files in files_by_adip.items():
            chosen = [f for f in files if accepted and f.selected]
            if chosen:
                picked[adip] = chosen
        return picked

    @staticmethod
    def _group_label(result: stag_api.StagThesisResult) -> str:
        bits = [result.student_full]
        meta = [m for m in (result.type_label, result.year) if m]
        if meta:
            bits.append("(" + ", ".join(meta) + ")")
        return " ".join(bits)

    def _find_db_target(
        self, result: stag_api.StagThesisResult
    ) -> tuple[str | None, str | None]:
        """Najde v DB práci/posudek odpovídající STAG výsledku.

        Vrací ``(thesis_id, opposing_id)`` — vždy nanejvýš jeden je vyplněn.
        Páruje primárně přes ``adipIdno``, jinak přes jméno + typ práce.
        """
        svc = self._service
        if svc is None:
            return None, None
        adip = (result.adipidno or "").strip()
        type_code = self._result_type_code(result)
        name_key = f"{result.name} {result.surname}".strip().lower()

        if adip:
            for t in svc.list_theses():
                if t.adipidno and t.adipidno == adip:
                    return t.id, None
            for o in svc.list_opposing_theses():
                if o.adipidno and o.adipidno == adip:
                    return None, o.id
        # Fallback: jméno + typ
        for t in svc.list_theses():
            student = svc.get_student(t.student_id) if t.student_id else None
            if (
                student
                and student.full_name.strip().lower() == name_key
                and (not type_code or t.type.value == type_code)
            ):
                return t.id, None
        for o in svc.list_opposing_theses():
            if (
                o.student_full_name.strip().lower() == name_key
                and (not type_code or o.type.value == type_code)
            ):
                return None, o.id
        return None, None
