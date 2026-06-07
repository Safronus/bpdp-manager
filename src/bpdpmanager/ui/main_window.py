from __future__ import annotations

import re
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QAction, QCloseEvent, QColor
from PySide6.QtWidgets import (
    QComboBox,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ..models import Thesis
from ..models.enums import (
    GRADES_ORDER,
    REVIEW_STATE_STRONG,
    STATUS_LABELS,
    STATUSES_CURRENT,
    STATUSES_FUTURE,
    STATUSES_HISTORY,
    ThesisStatus,
    ThesisType,
)
from ..services import (
    BackupManager,
    LockStatus,
    ProfileError,
    ProfileManager,
    ThesisService,
)
from ..storage import JsonRepository
from .backup_dialog import BackupBrowserDialog
from .harmonogram_tab import HarmonogramTab
from .stats_tab import StatsTab
from .import_into_current_dialog import ImportIntoCurrentDialog
from .manage_dialogs import (
    OboryManageDialog,
    OpponentsManageDialog,
    StudentsManageDialog,
    SupervisorsManageDialog,
)
from .new_profile_dialog import NewProfileDialog
from .opposing_tab import OpposingTab
from .proposals_tab import ProposalsTab
from .help_dialog import HelpDialog
from .profile_export_dialog import ExportProfileDialog, ImportProfileDialog
from .profile_manage_dialog import ProfileManageDialog
from .review_templates_dialog import GenerateReviewDialog, ReviewTemplatesDialog
from .rollback_dialog import RollbackOpposingDialog, RollbackThesisDialog
from .stag_consistency_dialog import StagConsistencyDialog
from .stag_import_dialog import StagImportDialog
from .theses_tree import ThesesTreeWidget
from .thesis_detail import (
    YEAR_MODE_ALL,
    YEAR_MODE_CURRENT,
    YEAR_MODE_FUTURE,
    YEAR_MODE_HISTORY,
    ThesisDetail,
)

# Orientační kapacita budoucích prací (na další akademický rok). Počet
# v titulku záložky se barví: pod limit zeleně, na limitu žlutě, nad červeně.
_FUTURE_CAPACITY = 15


# Barvy do titulků záložek — světlejší odstíny, ať jsou čitelné i v dark theme.
_TAB_GREEN = "#66bb6a"
_TAB_AMBER = "#f9a825"
_TAB_RED = "#ef5350"


def _future_count_color(n: int) -> str:
    """Barva počtu budoucích prací podle kapacity (< 15 zelená, = 15 žlutá, > 15 červená)."""
    if n < _FUTURE_CAPACITY:
        return _TAB_GREEN
    if n == _FUTURE_CAPACITY:
        return _TAB_AMBER
    return _TAB_RED


def _reviews_complete_color(complete_flags: list[bool]) -> str | None:
    """Barva titulku dle dokončenosti posudků: vše hotové+odeslané → zelená,
    něco chybí → oranžová, žádné práce → bez barvy (``None``)."""
    if not complete_flags:
        return None
    return _TAB_GREEN if all(complete_flags) else _TAB_AMBER


class _ThesesTab(QWidget):
    """Jedna záložka = strom prací (grupování rok → BP/DP) nahoře + detail dole."""

    # Emitne se, když se mohla změnit data ovlivňující souhrn (posudek, uložení).
    data_changed = Signal()

    def __init__(
        self,
        service: ThesisService,
        filter_predicate,
        year_mode: str = YEAR_MODE_ALL,
        parent=None,
        *,
        profile_manager=None,
        status_filter_choices: list[ThesisStatus] | None = None,
        status_filter_pref_key: str = "",
        enable_extra_filters: bool = False,
        hidden_columns: list[int] | None = None,
        show_transitions: bool = True,
    ) -> None:
        super().__init__(parent)
        self.service = service
        self._profile_manager = profile_manager
        self._base_predicate = filter_predicate
        self._status_filter_choices = list(status_filter_choices or [])
        self._status_filter_pref_key = status_filter_pref_key
        self._enable_extra_filters = enable_extra_filters
        self._status_checks: dict[ThesisStatus, QCheckBox] = {}
        self._cb_opponent: QComboBox | None = None
        self._cb_grade: QComboBox | None = None
        self._populating_filters = False

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setChildrenCollapsible(False)
        self.tree = ThesesTreeWidget(service)
        self.tree.setMinimumHeight(160)
        for col in (hidden_columns or []):
            self.tree.setColumnHidden(col, True)
        self.detail = ThesisDetail(
            service, year_mode=year_mode, profile_manager=profile_manager,
            show_transitions=show_transitions,
        )
        self.detail.setMinimumHeight(520)

        splitter.addWidget(self.tree)
        splitter.addWidget(self.detail)
        # Výchozí proporce: detail má dvojnásobek místa proti seznamu,
        # aby se formulářová pole vlezla bez vnitřního skrolování.
        splitter.setSizes([260, 640])
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        if self._status_filter_choices or self._enable_extra_filters:
            layout.addLayout(self._build_filter_row())
        layout.addWidget(splitter)

        # Filtr stromu = základní predikát + (volitelně) zaškrtnuté stavy /
        # vybraný oponent / vybraná známka.
        self._apply_tree_filter()

        self.tree.thesis_selected.connect(self._on_thesis_selected)
        self.tree.rollback_requested.connect(self._on_rollback_requested)
        self.tree.generate_review_requested.connect(self._on_generate_review_requested)
        self.tree.export_thesis_requested.connect(self._on_export_thesis)
        self.tree.mark_review_sent_requested.connect(self._on_mark_review_sent)
        # Detail panel má vlastní tlačítko „📝 Napsat posudek…" — pošle
        # stejný signal a my ho zpracujeme jednou handlerem.
        self.detail.generate_review_requested.connect(self._on_generate_review_requested)
        self.detail.saved.connect(lambda _: (self.tree.refresh(), self.data_changed.emit()))
        self.detail.deleted.connect(lambda _: (self.tree.refresh(), self.data_changed.emit()))

    def _build_filter_row(self) -> QHBoxLayout:
        """Řádek filtrů: checkboxy stavů (perzistentní) + comba oponent/známka."""
        row = QHBoxLayout()
        row.setContentsMargins(4, 2, 4, 0)
        row.setSpacing(8)

        if self._status_filter_choices:
            saved = None
            if self._profile_manager and self._status_filter_pref_key:
                saved = self._profile_manager.get_ui_pref(self._status_filter_pref_key)
            saved_set = set(saved) if isinstance(saved, list) else None
            row.addWidget(QLabel("Zobrazit:"))
            for status in self._status_filter_choices:
                cb = QCheckBox(STATUS_LABELS.get(status, status.value))
                # Bez uloženého nastavení je vše zaškrtnuté; jinak dle uložené volby.
                cb.setChecked(saved_set is None or status.value in saved_set)
                cb.toggled.connect(self._on_status_filter_changed)
                self._status_checks[status] = cb
                row.addWidget(cb)

        if self._enable_extra_filters:
            row.addSpacing(16)
            row.addWidget(QLabel("Oponent:"))
            self._cb_opponent = QComboBox()
            self._cb_opponent.setMinimumWidth(180)
            self._cb_opponent.currentIndexChanged.connect(self._on_extra_filter_changed)
            row.addWidget(self._cb_opponent)
            row.addSpacing(8)
            row.addWidget(QLabel("Známka:"))
            self._cb_grade = QComboBox()
            self._cb_grade.addItem("Všechny známky", userData=None)
            for g in GRADES_ORDER:
                self._cb_grade.addItem(g, userData=g)
            self._cb_grade.currentIndexChanged.connect(self._on_extra_filter_changed)
            row.addWidget(self._cb_grade)
            self._populate_opponent_combo()

        row.addStretch(1)
        return row

    def _populate_opponent_combo(self) -> None:
        """Naplní combo oponentů těmi, kdo se vyskytují v této záložce.

        Zachová aktuální výběr (podle ID). Volá se i při ``refresh`` — data se
        mohla změnit (import, smazání). Signály po dobu plnění blokujeme.
        """
        if self._cb_opponent is None:
            return
        prev_id = self._cb_opponent.currentData()
        # Posbírej oponenty z prací patřících do této záložky (základní predikát).
        seen: dict[str, str] = {}
        for t in self.service.list_theses():
            if not self._base_predicate(t) or not t.opponent_id:
                continue
            if t.opponent_id not in seen:
                opp = self.service.get_opponent(t.opponent_id)
                if opp is not None:
                    seen[t.opponent_id] = opp.display_name
        ordered = sorted(seen.items(), key=lambda kv: kv[1].casefold())

        self._populating_filters = True
        try:
            self._cb_opponent.clear()
            self._cb_opponent.addItem("Všichni oponenti", userData=None)
            for oid, name in ordered:
                self._cb_opponent.addItem(name, userData=oid)
            # Obnov předchozí výběr, pokud tam pořád je.
            if prev_id:
                idx = self._cb_opponent.findData(prev_id)
                self._cb_opponent.setCurrentIndex(idx if idx >= 0 else 0)
        finally:
            self._populating_filters = False

    def _checked_statuses(self) -> set[ThesisStatus]:
        return {s for s, cb in self._status_checks.items() if cb.isChecked()}

    def _apply_tree_filter(self) -> None:
        base = self._base_predicate
        allowed = self._checked_statuses() if self._status_checks else None
        opp_id = self._cb_opponent.currentData() if self._cb_opponent else None
        grade = self._cb_grade.currentData() if self._cb_grade else None

        def predicate(t) -> bool:
            if not base(t):
                return False
            if allowed is not None and t.status not in allowed:
                return False
            if opp_id and t.opponent_id != opp_id:
                return False
            if grade:
                gs = (t.grade_supervisor or "").upper().strip()
                go = (t.grade_opponent or "").upper().strip()
                if grade not in (gs, go):
                    return False
            return True

        self.tree.set_filter(predicate)

    def _on_status_filter_changed(self, _checked: bool) -> None:
        self._apply_tree_filter()
        self.tree.refresh()
        if self._profile_manager and self._status_filter_pref_key:
            self._profile_manager.set_ui_pref(
                self._status_filter_pref_key,
                [s.value for s in self._checked_statuses()],
            )

    def _on_extra_filter_changed(self, _index: int) -> None:
        if self._populating_filters:
            return
        self._apply_tree_filter()
        self.tree.refresh()

    def _on_thesis_selected(self, thesis_id: str) -> None:
        thesis = self.service.get_thesis(thesis_id)
        self.detail.set_thesis(thesis)

    def _on_generate_review_requested(self, thesis_id: str) -> None:
        """Otevře dialog pro výběr šablony + generování posudku."""
        # Flushni rozpracované změny, aby data byla aktuální
        try:
            self.detail.flush()
        except Exception:
            pass
        thesis = self.service.get_thesis(thesis_id)
        if thesis is None:
            return
        dlg = GenerateReviewDialog(self.service, thesis, self)
        if dlg.exec():
            # Po potvrzení dialogu znovu načti práci — posudek mohl přidat
            # přílohy (XLSX/PDF) a archivovat starší. ``set_thesis`` přes
            # ``DocumentsWidget.set_thesis_id`` rovnou obnoví i seznam dokumentů.
            self.detail.set_thesis(self.service.get_thesis(thesis_id))
            self.tree.refresh()
            self.data_changed.emit()

    def _on_mark_review_sent(self, thesis_id: str, sent: bool) -> None:
        """Ručně přepne příznak odeslání posudku vedoucího sekretářce."""
        self.service.set_supervisor_review_sent(thesis_id, sent)
        self.tree.refresh()
        if self.detail.thesis and self.detail.thesis.id == thesis_id:
            self.detail.set_thesis(self.service.get_thesis(thesis_id))
        self.data_changed.emit()

    def _on_export_thesis(self, thesis_id: str) -> None:
        """Exportuje práci do ZIP balíku."""
        from ..services.thesis_export import ThesisExportError, export_thesis_to_zip

        try:
            self.detail.flush()
        except Exception:
            pass
        thesis = self.service.get_thesis(thesis_id)
        if thesis is None:
            return
        surname = ""
        if thesis.student_id:
            student = self.service.get_student(thesis.student_id)
            surname = student.last_name if student else ""
        safe = re.sub(r"[^0-9A-Za-zÀ-ž_-]+", "_", surname).strip("_") or "prace"
        default_name = f"prace_{safe}_{thesis.type.value}_{thesis.academic_year.replace('/', '-')}.zip"
        path_str, _ = QFileDialog.getSaveFileName(
            self, "Exportovat práci do ZIP", str(Path.home() / default_name),
            "ZIP balík (*.zip)",
        )
        if not path_str:
            return
        try:
            stats = export_thesis_to_zip(self.service, thesis_id, Path(path_str))
        except (ThesisExportError, OSError) as exc:
            QMessageBox.critical(self, "Export", f"Export selhal:\n{exc}")
            return
        QMessageBox.information(
            self, "Export hotov",
            f"Práce byla vyexportována do:\n{path_str}\n\nSouborů: {stats['files']}",
        )

    def _on_rollback_requested(self, thesis_id: str) -> None:
        """Otevře rollback dialog pro vybranou práci."""
        # Flushni rozpracované změny v detail panelu pro tuto práci,
        # aby autosave po našem mazání nezapsal něco zpět.
        try:
            self.detail.flush()
        except Exception:
            pass
        dlg = RollbackThesisDialog(self.service, thesis_id, self)
        dlg.exec()
        if dlg.executed:
            # Práce už neexistuje — vyprázdni detail panel + refresh stromu
            self.detail.set_thesis(None)
            self.tree.refresh()

    def refresh(self) -> None:
        # Combo oponentů musí odrážet aktuální data (import / smazání práce).
        # ``_apply_tree_filter`` přes ``set_filter`` rovnou strom překreslí.
        self._populate_opponent_combo()
        self._apply_tree_filter()


class MainWindow(QMainWindow):
    def __init__(
        self,
        service: ThesisService,
        profile_manager: ProfileManager | None = None,
    ) -> None:
        super().__init__()
        self.service = service
        self.profile_manager = profile_manager
        self.setWindowTitle(self._compose_title())
        self.resize(1400, 960)
        self.setMinimumSize(1100, 760)

        current_year = ThesisService.current_academic_year()
        next_year = ThesisService.next_academic_year()

        # Status-driven filtrace tabů (v0.15.0).
        # Rok ovlivňuje pouze řazení/grupování uvnitř, ne příslušnost k tabu.
        # Migrate v Database._migrate_assigned_status zajistí, že staré
        # 'assigned' už neexistuje — všechny takové práce jsou v IN_PROGRESS.

        self.tabs = QTabWidget()
        pm = self.profile_manager
        self.tab_current = _ThesesTab(
            service,
            lambda t: t.status in STATUSES_CURRENT,
            year_mode=YEAR_MODE_CURRENT,
            profile_manager=pm,
        )
        self.tab_future = _ThesesTab(
            service,
            lambda t: t.status in STATUSES_FUTURE,
            year_mode=YEAR_MODE_FUTURE,
            profile_manager=pm,
            # Budoucí práce ještě nemají známky, posudky ani odeslání.
            hidden_columns=[
                ThesesTreeWidget.COL_GRADES,
                ThesesTreeWidget.COL_REVIEWS,
                ThesesTreeWidget.COL_SENT,
            ],
        )
        self.tab_history = _ThesesTab(
            service,
            lambda t: t.status in STATUSES_HISTORY,
            year_mode=YEAR_MODE_HISTORY,
            profile_manager=pm,
            status_filter_choices=[
                ThesisStatus.DEFENDED,
                ThesisStatus.CANCELLED,
                ThesisStatus.FAILED,
            ],
            status_filter_pref_key="history_status_filter",
            enable_extra_filters=True,
            # Hotové práce → indikace „Posudky" i „Odesláno" jsou irelevantní.
            hidden_columns=[ThesesTreeWidget.COL_REVIEWS, ThesesTreeWidget.COL_SENT],
            # V Historii nepotřebuješ panel „Přechod do stavu".
            show_transitions=False,
        )
        self.tab_all = _ThesesTab(
            service, lambda t: True, year_mode=YEAR_MODE_ALL, profile_manager=pm
        )
        self.tab_opposing = OpposingTab(service, profile_manager=pm)
        self.tab_opposing.send_reviews_requested.connect(self._send_opponent_reviews)
        self.tab_proposals = ProposalsTab(service)
        self.tab_proposals.converted.connect(self._on_proposal_converted)
        self.tab_harmonogram = HarmonogramTab(service)
        self.tab_stats = StatsTab(service)

        # Tab labely (bez roku — status-driven, jeden tab = jeden bucket napříč roky)
        self.tabs.addTab(self.tab_current, "Aktuálně vedené práce")
        self.tabs.addTab(self.tab_future, f"Práce v dalším akademickém roce {next_year}")
        self.tabs.addTab(self.tab_history, "Historie")
        self.tabs.addTab(self.tab_all, "Vše")
        self.tabs.addTab(self.tab_opposing, "🧐 Oponované práce")
        self.tabs.addTab(self.tab_proposals, "💡 Návrhy témat")
        self.tabs.addTab(self.tab_harmonogram, "📅 Harmonogram")
        self.tabs.addTab(self.tab_stats, "📊 Statistiky")

        # Základní titulky záložek s počty (počet doplňuje _refresh_tab_labels);
        # STAG odznak 🔄 se přidává zvlášť (drží se v _stag_badges).
        self._tab_base = {
            id(self.tab_current): "Aktuálně vedené práce",
            id(self.tab_future): f"Práce v dalším akademickém roce {next_year}",
            id(self.tab_opposing): "🧐 Oponované práce",
        }
        self._stag_badges: dict[int, int] = {}

        # Globální vyhledávání + navigace nad záložkami.
        central = QWidget()
        cv = QVBoxLayout(central)
        cv.setContentsMargins(6, 4, 6, 0)
        cv.setSpacing(4)
        search_row = QHBoxLayout()
        self.ed_search = QLineEdit()
        self.ed_search.setClearButtonEnabled(True)
        self.ed_search.setPlaceholderText(
            "🔍 Najít práci: jméno studenta · název práce · ID (Axxxxx) — Enter"
        )
        self.ed_search.returnPressed.connect(self._do_search)
        btn_search = QPushButton("Najít")
        btn_search.clicked.connect(self._do_search)
        search_row.addWidget(self.ed_search, stretch=1)
        search_row.addWidget(btn_search)
        cv.addLayout(search_row)
        # Proužek tiché kontroly STAG (skrytý, dokud kontrola nedoběhne).
        cv.addWidget(self._build_stag_banner())
        cv.addWidget(self.tabs, stretch=1)
        self.setCentralWidget(central)
        self.setStatusBar(QStatusBar())
        # Barevný souhrn posudků (vpravo v dolní liště).
        self._status_reviews = QLabel()
        self._status_reviews.setTextFormat(Qt.TextFormat.RichText)
        self.statusBar().addPermanentWidget(self._status_reviews)

        # Souhrn posudků v dolní liště přepočítej při změně dat i přepnutí tabu.
        for tab in (self.tab_current, self.tab_future, self.tab_history, self.tab_all):
            tab.data_changed.connect(self._update_status)
        self.tab_opposing.changed.connect(self._update_status)
        self.tabs.currentChanged.connect(lambda _: self._update_status())
        self.tabs.currentChanged.connect(self._on_tab_changed)

        self._build_toolbar(current_year, next_year)
        self._update_status()  # nastaví i počty v titulcích záložek
        # Po startu otevři první práci v Aktuálním seznamu (pokud existuje) —
        # uživatel rovnou vidí, na čem aktuálně dělá, nemusí klikat.
        self._auto_select_first_in_current()

        # Tichá kontrola STAG na pozadí (krátce po startu, ať se okno stihne
        # vykreslit). Indikátor v proužku + odznaky na záložkách.
        self._stag_checker: object | None = None
        QTimer.singleShot(900, self._start_stag_check)

    # --- tichá kontrola STAG -------------------------------------------------

    def _build_stag_banner(self) -> QFrame:
        """Proužek s výsledkem tiché kontroly STAG (skrytý, dokud nedoběhne)."""
        bar = QFrame()
        bar.setAutoFillBackground(True)
        bar.setFrameShape(QFrame.Shape.StyledPanel)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(10, 4, 6, 4)
        lay.setSpacing(8)
        # Banner má vždy světlé pozadí → tlačítka stylujeme natvrdo (tmavý text
        # na světlém), jinak by je dark theme vykreslil světle = nečitelně.
        btn_qss = (
            "QPushButton { color:#212121; background:#ffffff; "
            "border:1px solid #9e9e9e; border-radius:4px; padding:3px 10px; } "
            "QPushButton:hover { background:#eeeeee; }"
        )
        self._stag_banner_label = QLabel("")
        self._stag_banner_label.setTextFormat(Qt.TextFormat.RichText)
        self._stag_banner_label.setWordWrap(True)
        lay.addWidget(self._stag_banner_label, stretch=1)
        self._stag_banner_btn = QPushButton("🔎 Detaily…")
        self._stag_banner_btn.setToolTip(
            "Náhled kontroly: co je nové/změněné + seznam zkontrolovaných "
            "a aktuálních prací (pro ověření, že kontrola proběhla)."
        )
        self._stag_banner_btn.setStyleSheet(btn_qss)
        self._stag_banner_btn.clicked.connect(self._show_stag_changes)
        self._stag_banner_btn.setVisible(False)
        lay.addWidget(self._stag_banner_btn)
        btn_recheck = QPushButton("🔄 Zkontrolovat")
        btn_recheck.setStyleSheet(btn_qss)
        btn_recheck.setToolTip("Znovu zkontrolovat změny ve STAG (aktuální rok).")
        btn_recheck.clicked.connect(self._start_stag_check)
        lay.addWidget(btn_recheck)
        btn_close = QToolButton()
        btn_close.setText("✕")
        btn_close.setToolTip("Skrýt proužek")
        btn_close.setStyleSheet(
            "QToolButton { color:#212121; border:none; padding:2px 6px; } "
            "QToolButton:hover { background:#e0e0e0; border-radius:4px; }"
        )
        btn_close.clicked.connect(lambda: self._stag_banner.setVisible(False))
        lay.addWidget(btn_close)
        self._stag_banner = bar
        bar.setVisible(False)
        return bar

    def _set_stag_banner(self, html: str, bg: str, *, show_open: bool) -> None:
        self._stag_banner_label.setText(html)
        # Pozadí je vždy světlý odstín → vynuť tmavý text (jinak by ho dark
        # theme vykreslil světlý = nečitelný). Barvu nastav i na potomky.
        self._stag_banner.setStyleSheet(
            f"QFrame {{ background: {bg}; border: 1px solid rgba(0,0,0,0.10); "
            f"border-radius: 6px; }} "
            f"QLabel {{ color: #212121; background: transparent; }}"
        )
        self._stag_banner_btn.setVisible(show_open)
        self._stag_banner.setVisible(True)

    def _start_stag_check(self) -> None:
        """Spustí tichou kontrolu STAG na pozadí (pokud už neběží)."""
        from .stag_check import StagChecker

        if getattr(self, "_stag_checker", None) is not None:
            return  # už běží
        user_name = ""
        if self.profile_manager and self.profile_manager.active:
            user_name = self.profile_manager.active.user_name or ""
        self._set_stag_banner(
            "⏳ Kontroluji změny ve STAG…", "#e3f2fd", show_open=False
        )
        checker = StagChecker(self.service, user_name, parent=self)
        checker.finished.connect(self._on_stag_check_done)
        self._stag_checker = checker
        checker.start()

    def _on_stag_check_done(self, result) -> None:
        """Zobrazí výsledek tiché kontroly (proužek + odznaky na záložkách)."""
        from datetime import datetime

        self._stag_checker = None
        self._last_stag_result = result
        ts = datetime.now().strftime("%H:%M")

        # Odznaky 🔄 na záložkách (jen aktuální + oponentury).
        self._stag_badges[id(self.tab_current)] = result.supervised_changes if result.ok else 0
        self._stag_badges[id(self.tab_opposing)] = result.opposing_changes if result.ok else 0
        self._refresh_tab_labels()

        if not result.ok:
            self._set_stag_banner(
                f"⚠ STAG: kontrolu se nepodařilo dokončit ({result.error}). "
                f"Naposledy {ts}.",
                "#fff3e0", show_open=False,
            )
            return

        if result.total_changes == 0:
            self._set_stag_banner(
                f"✓ STAG zkontrolováno v {ts} — <b>vše aktuální</b> "
                f"(prošlo {result.checked} prací). Detaily ↓",
                "#e8f5e9", show_open=True,
            )
            return

        parts: list[str] = []
        if result.supervised_changes:
            parts.append(f"{result.supervised_changes}× vedená práce")
        if result.opposing_changes:
            parts.append(f"{result.opposing_changes}× oponentura")
        if result.new_works:
            parts.append(f"🆕 {result.new_works}× nová práce ve STAG")
        self._set_stag_banner(
            f"🔄 STAG zkontrolováno v {ts} — <b>změny: {', '.join(parts)}</b>. "
            "Klikni na „Detaily…“.",
            "#fff8e1", show_open=True,
        )

    def _show_stag_changes(self) -> None:
        """Otevře rychlý náhled změn ze STAG; odtud lze přejít na Import."""
        from .stag_check import StagChangesPreviewDialog

        result = getattr(self, "_last_stag_result", None)
        if result is None:
            self._start_stag_check()
            return
        dlg = StagChangesPreviewDialog(result, self)
        dlg.exec()
        if dlg.open_import:
            self._import_from_stag()

    def _refresh_tab_labels(self) -> None:
        """Doplní k titulkům záložek počty prací (+ STAG odznak 🔄) a barvu.

        Budoucí práce barví podle kapacity (< 15 zeleně, = 15 žlutě, > 15
        červeně). *Aktuálně vedené* a *Oponované práce* barví podle dokončenosti
        posudků: vše hotové **i odeslané** → zeleně, něco chybí → oranžově.
        """
        theses = self.service.list_theses()
        current = [t for t in theses if t.status in STATUSES_CURRENT]
        n_future = sum(1 for t in theses if t.status in STATUSES_FUTURE)
        current_year = ThesisService.current_academic_year()
        opp_current = [
            o for o in self.service.list_opposing_theses()
            if o.academic_year == current_year
        ]

        # Posudek je „kompletní" = hotový soubor (done) A odeslaný sekretářce.
        sup_complete = [
            t.supervisor_review_state == "done" and t.supervisor_review_sent_at is not None
            for t in current
        ]
        opp_complete = [
            o.opponent_review_state == "done" and o.opponent_review_sent_at is not None
            for o in opp_current
        ]

        def _apply(tab, count: int, color: str | None = None) -> None:
            idx = self.tabs.indexOf(tab)
            if idx < 0:
                return
            base = self._tab_base.get(id(tab), "")
            badge = self._stag_badges.get(id(tab), 0)
            text = f"{base} ({count})"
            if badge:
                text += f"  🔄{badge}"
            self.tabs.setTabText(idx, text)
            self.tabs.tabBar().setTabTextColor(
                idx, QColor(color) if color else QColor()
            )

        _apply(self.tab_current, len(current), _reviews_complete_color(sup_complete))
        _apply(self.tab_future, n_future, _future_count_color(n_future))
        _apply(self.tab_opposing, len(opp_current), _reviews_complete_color(opp_complete))

    def _auto_select_first_in_current(self) -> None:
        """Po startu vybere první práci v Aktuální záložce.

        Pokud Aktuální je prázdná, zkusí Budoucí, pak Historie — vždy první
        v dané záložce. Žádná práce v žádném tabu → nic neděláme.
        """
        for tab in (self.tab_current, self.tab_future, self.tab_history):
            first_id = self._first_thesis_id_in_tab(tab)
            if first_id:
                # Přepneme se na danou záložku a vybereme práci
                index = self.tabs.indexOf(tab)
                if index >= 0:
                    self.tabs.setCurrentIndex(index)
                tab.tree.select_thesis(first_id)
                return

    @staticmethod
    def _first_thesis_id_in_tab(tab: "_ThesesTab") -> str | None:
        """Najde první (top-most) ID práce v stromu daného tabu.

        Strom je hierarchický: rok → typ → práce. Procházíme top-down
        a vrátíme první leaf, který reprezentuje thesis.
        """
        from .theses_tree import ROLE_KIND, ROLE_THESIS_ID

        tree = tab.tree
        for i in range(tree.topLevelItemCount()):
            year_item = tree.topLevelItem(i)
            for j in range(year_item.childCount()):
                type_item = year_item.child(j)
                for k in range(type_item.childCount()):
                    leaf = type_item.child(k)
                    if leaf.data(0, ROLE_KIND) == "thesis":
                        tid = leaf.data(0, ROLE_THESIS_ID)
                        if tid:
                            return tid
        return None

    # --- toolbar -------------------------------------------------------------

    # Barvy skupin toolbaru (RGB) — jen jako jemný podklad tlačítek (rgba),
    # aby to fungovalo i v tmavém režimu.
    _GROUP_CREATE = (76, 175, 80)    # zelená — vytvořit
    _GROUP_MANAGE = (33, 150, 243)   # modrá — správa registrů
    _GROUP_REVIEW = (156, 39, 176)   # fialová — posudky
    _GROUP_IMPORT = (0, 150, 136)    # tyrkysová — import
    _GROUP_NEUTRAL = (120, 120, 120)  # šedá — profil / akce

    def _tint_toolbar_button(self, toolbar: QToolBar, action: QAction, rgb) -> None:
        btn = toolbar.widgetForAction(action)
        if btn is not None:
            self._tint_widget(btn, rgb)

    @staticmethod
    def _tint_widget(widget, rgb) -> None:
        r, g, b = rgb
        widget.setStyleSheet(
            f"QToolButton {{ background: rgba({r},{g},{b},0.13); "
            f"border: 1px solid rgba({r},{g},{b},0.34); border-radius: 5px; "
            f"padding: 4px 9px; margin: 2px 2px; }} "
            f"QToolButton:hover {{ background: rgba({r},{g},{b},0.26); }} "
            f"QToolButton:pressed {{ background: rgba({r},{g},{b},0.40); }}"
        )

    def _build_toolbar(self, current_year: str, next_year: str) -> None:
        toolbar = QToolBar("Hlavní")
        toolbar.setMovable(False)
        toolbar.setIconSize(toolbar.iconSize())
        self.addToolBar(toolbar)

        def add(label: str, handler, rgb, tooltip: str = "", shortcut: str = ""):
            act = QAction(label, self)
            if tooltip:
                act.setToolTip(tooltip)
            if shortcut:
                act.setShortcut(shortcut)
            act.triggered.connect(handler)
            toolbar.addAction(act)
            self._tint_toolbar_button(toolbar, act, rgb)
            return act

        # ── Skupina: Vytvořit (zelená) ──────────────────────────────────
        add(
            "➕ Nová práce", lambda: self._new_thesis_smart(), self._GROUP_CREATE,
            "Vytvoří novou práci. Výchozí stav se odvodí z aktuálního tabu:\n"
            "  Aktuální → V řešení\n  Budoucí → Vypsané téma\n"
            "  Historie → Obhájeno\n  Vše → Vypsané téma",
        )
        add(
            "🌱 Zájemce", self._new_future_thesis, self._GROUP_CREATE,
            "Nová budoucí práce — volitelně rovnou vyplníš studenta, obor, "
            "název a anotaci (nic není povinné). Stav default Vypsané téma.",
        )
        add(
            "🕘 Minulá práce", self._new_past_thesis, self._GROUP_CREATE,
            "Rychlý formulář pro historickou práci (vlastní rok + stav).",
        )

        toolbar.addSeparator()

        # ── Skupina: Správa registrů (modrá) ────────────────────────────
        add("🎓 Studenti", self._manage_students, self._GROUP_MANAGE)
        add("🧐 Oponenti", self._manage_opponents, self._GROUP_MANAGE)
        add(
            "👔 Vedoucí", self._manage_supervisors, self._GROUP_MANAGE,
            "Registr vedoucích cizích BP/DP — pro oponentské posudky",
        )
        add(
            "🏷 Obory + sekretářky", self._manage_obory, self._GROUP_MANAGE,
            "Číselník oborů + sekretářky oborů. Dvojklik na hlavičku sekretářky "
            "upraví její kontakt a oslovení hromadně pro všechny její obory.",
        )
        add(
            "🚫 Odmítnutí", self._manage_rejected, self._GROUP_MANAGE,
            "Evidence odmítnutých zájemců o vedení (jméno, obor, rok) — "
            "promítá se do Statistik (kapacita vedení).",
        )

        toolbar.addSeparator()

        # ── Skupina: Posudky (fialová) ──────────────────────────────────
        add(
            "📝 Šablony posudků", self._manage_review_templates, self._GROUP_REVIEW,
            "Knihovna XLSX šablon posudků (vedoucího / oponenta) — "
            "z kontextu konkrétní práce lze vygenerovat předvyplněný posudek.",
        )
        # „Odeslat posudky" s volbou: vedoucího (vedené práce) / oponentské.
        self._send_button = QToolButton()
        self._send_button.setText("✉ Odeslat posudky")
        self._send_button.setToolTip(
            "Odeslání připravených posudků sekretářce e-mailem — vyber, zda "
            "posudky vedoucího (vedené práce) nebo oponentské."
        )
        self._send_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        send_menu = QMenu(self._send_button)
        act_send_sup = send_menu.addAction("🎓 Posudky vedoucího (vedené práce)…")
        act_send_sup.triggered.connect(self._send_supervisor_reviews)
        act_send_opp = send_menu.addAction("🧐 Oponentské posudky…")
        act_send_opp.triggered.connect(self._send_opponent_reviews)
        self._send_button.setMenu(send_menu)
        self._tint_widget(self._send_button, self._GROUP_REVIEW)
        toolbar.addWidget(self._send_button)

        toolbar.addSeparator()

        # ── Skupina: Import (tyrkysová) ─────────────────────────────────
        add(
            "📥 Import ze STAG…", self._import_from_stag, self._GROUP_IMPORT,
            "Import dat z CSV exportu STAG (getKvalifikacniPrace*.csv) — "
            "vytvoří nebo aktualizuje vedené BP/DP a oponentské posudky.",
        )
        add(
            "📦 Import práce ze ZIP…", self._import_thesis_zip, self._GROUP_IMPORT,
            "Naimportuje práci z dříve vyexportovaného ZIP balíku (data, stav, "
            "posudky, soubory) — vytvoří novou práci.",
        )
        add(
            "🔍 Kontrola se STAG", self._check_stag_consistency, self._GROUP_IMPORT,
            "Porovná soubory u prací (vedených i oponovaných) se STAG a vypíše, "
            "kde STAG nabízí dokument (plný text / příloha / posudek), který "
            "v databázi chybí. Read-only — jen kontrola, nic nestahuje.",
        )
        add(
            "🗂 Přeřadit průběh obhajoby", self._reclassify_defense_records,
            self._GROUP_IMPORT,
            "Dotáhne ze STAG původní názvy příloh typu „Jiné“, spáruje je a "
            "v náhledu (s checkboxy) nabídne přeřazení na „Soubor s průběhem "
            "obhajoby“ — protokoly/zápisy obhajoby jsou předzaškrtnuté (se zálohou).",
        )

        toolbar.addSeparator()

        # ── Profil (šedá) + akce ────────────────────────────────────────
        if self.profile_manager is not None:
            self._profile_button = QToolButton()
            self._profile_button.setText(
                "👤 "
                + (self.profile_manager.active.name if self.profile_manager.active else "Profil")
            )
            self._profile_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
            self._tint_widget(self._profile_button, self._GROUP_NEUTRAL)
            self._refresh_profile_menu()
            toolbar.addWidget(self._profile_button)
            toolbar.addSeparator()

        add("🔄 Obnovit", self._refresh_all, self._GROUP_NEUTRAL)
        add(
            "❓ Nápověda", self._show_help, self._GROUP_NEUTRAL,
            "Popis funkcí a jak aplikace funguje (F1).", shortcut="F1",
        )

    def _on_tab_changed(self, index: int) -> None:
        """Při přepnutí na Statistiky je přepočítej z aktuálních dat."""
        widget = self.tabs.widget(index)
        if isinstance(widget, StatsTab):
            widget.refresh()

    def _show_help(self) -> None:
        HelpDialog(self).exec()

    def _send_supervisor_reviews(self) -> None:
        """Otevře dialog pro odeslání posudků vedoucího sekretářce."""
        if self.profile_manager is None:
            return
        # Flushni rozpracované změny, ať se pracuje s aktuálními daty
        for i in range(self.tabs.count()):
            w = self.tabs.widget(i)
            if isinstance(w, _ThesesTab):
                try:
                    w.detail.flush()
                except Exception:
                    pass
        from .send_reviews_dialog import SendReviewsDialog

        dlg = SendReviewsDialog(self.service, self.profile_manager, "supervisor", self)
        dlg.exec()
        self._refresh_all()

    def _send_opponent_reviews(self) -> None:
        """Otevře dialog pro odeslání oponentských posudků sekretářce."""
        if self.profile_manager is None:
            QMessageBox.information(
                self, "Profil",
                "Odesílání e-mailem vyžaduje aktivní profil s vyplněným e-mailem.",
            )
            return
        from .send_reviews_dialog import SendReviewsDialog

        dlg = SendReviewsDialog(self.service, self.profile_manager, "opponent", self)
        dlg.exec()
        self._refresh_all()

    def _open_email_settings(self) -> None:
        """Otevře samostatného správce SMTP nastavení."""
        if self.profile_manager is None:
            return
        from .email_settings_dialog import EmailSettingsDialog

        EmailSettingsDialog(self.profile_manager, self).exec()

    # --- profil --------------------------------------------------------------

    def _compose_title(self) -> str:
        from .. import __version__

        base = f"BPDPManager {__version__}"
        if self.profile_manager and self.profile_manager.active:
            return f"{base} — {self.profile_manager.active.name}"
        return f"{base} — správa BP/DP"

    def _refresh_profile_menu(self) -> None:
        if self.profile_manager is None:
            return
        menu = QMenu(self._profile_button)
        active = self.profile_manager.active
        for p in self.profile_manager.all_profiles():
            label = ("● " if active and p.id == active.id else "   ") + p.name
            act = menu.addAction(label)
            act.setData(p.id)
            act.triggered.connect(
                lambda _checked=False, pid=p.id: self._switch_profile(pid)
            )
        menu.addSeparator()
        act_new = menu.addAction("➕ Nový profil…")
        act_new.triggered.connect(self._action_new_profile)
        act_open = menu.addAction("📂 Otevřít existující složku…")
        act_open.triggered.connect(self._action_open_existing_profile)
        act_import = menu.addAction("📥 Importovat z jiného profilu do aktuálního…")
        act_import.triggered.connect(self._action_import_into_current)
        # Disable pokud není jiný profil
        other_count = sum(
            1
            for p in self.profile_manager.all_profiles()
            if active is None or p.id != active.id
        )
        act_import.setEnabled(other_count > 0 and active is not None)
        menu.addSeparator()
        act_export = menu.addAction("📤 Exportovat aktuální profil do ZIPu…")
        act_export.setToolTip(
            "Vytvoří přenosný ZIP balík profilu — db.json + dokumenty + "
            'harmonogramy. Lze otevřít na jiném zařízení přes „Importovat profil ze ZIPu…".'
        )
        act_export.triggered.connect(self._action_export_profile_zip)
        act_export.setEnabled(active is not None)
        act_import_zip = menu.addAction("📥 Importovat profil ze ZIPu…")
        act_import_zip.setToolTip(
            "Otevře ZIP s exportem z jiného zařízení a vytvoří nový profil."
        )
        act_import_zip.triggered.connect(self._action_import_profile_zip)
        menu.addSeparator()
        act_email = menu.addAction("✉ Nastavení e-mailu (SMTP)…")
        act_email.setToolTip(
            "E-mail odesílatele a SMTP server pro odesílání posudků sekretářkám "
            "(s testem spojení). Heslo se neukládá."
        )
        act_email.triggered.connect(self._open_email_settings)
        act_email.setEnabled(active is not None)
        menu.addSeparator()
        act_manage = menu.addAction("🗂 Správa profilů…")
        act_manage.triggered.connect(self._action_manage_profiles)
        act_backup_now = menu.addAction("💾 Zálohovat teď")
        act_backup_now.setToolTip("Rychlá ruční záloha aktuálního stavu databáze.")
        act_backup_now.triggered.connect(self._action_backup_now)
        act_backup_now.setEnabled(active is not None)
        act_backups = menu.addAction("💾 Zálohy…")
        act_backups.triggered.connect(self._action_show_backups)
        self._profile_button.setMenu(menu)
        # Update label
        if active is not None:
            self._profile_button.setText("👤 " + active.name)

    def _switch_profile(self, profile_id: str) -> None:
        if self.profile_manager is None:
            return
        active = self.profile_manager.active
        if active is not None and active.id == profile_id:
            return  # už jsme tady
        # Flushni rozpracované změny v detail panelech
        for i in range(self.tabs.count()):
            w = self.tabs.widget(i)
            if isinstance(w, _ThesesTab):
                try:
                    w.detail.flush()
                except Exception:
                    pass

        # Lock check
        check = self.profile_manager.check_lock(profile_id)
        force = False
        if check.status == LockStatus.LOCKED_BY_OTHER:
            if not self._confirm_locked(check):
                return
            force = True

        self.profile_manager.close()
        try:
            result = self.profile_manager.open(profile_id, force=force)
        except ProfileError as exc:
            QMessageBox.critical(self, "Přepnutí profilu", str(exc))
            return

        # Vytvoř nový repository nad novou data_dir + bind do existující service
        data_dir = self.profile_manager.active_data_dir()
        new_repo = JsonRepository(
            path=data_dir / "db.json",
            backup_path=data_dir / "db.json.bak",
            backup_manager=BackupManager(data_dir),
        )
        self.service.reset(new_repo)
        # Nově vytvořený profil dostane výchozí obory + šablony.
        self.service.maybe_seed_defaults()

        # Refresh UI a window title
        self.setWindowTitle(self._compose_title())
        self._refresh_all()
        self._refresh_profile_menu()

    def _confirm_locked(self, check) -> bool:
        info = check.existing
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle("Profil je otevřený jinde")
        text = (
            "Profil je zřejmě otevřený na jiném zařízení nebo uživatelem.\n\n"
            f"Zařízení: {info.hostname if info else '?'}\n"
            f"Uživatel:  {info.username if info else '?'}\n"
            f"Začátek:   {info.started_at.strftime('%d.%m.%Y %H:%M:%S') if info else '?'}\n"
            f"Aplikace:  {info.app_version if info else '?'}\n\n"
            "Pokud víš, že tam aplikace neběží (např. po pádu), můžeš pokračovat. "
            "Jinak je lepší zavřít aplikaci na druhém zařízení a počkat na "
            "synchronizaci, aby si vy a druhé zařízení vzájemně nepřepsali změny."
        )
        msg.setText(text)
        btn_ignore = msg.addButton("Otevřít stejně", QMessageBox.ButtonRole.DestructiveRole)
        msg.addButton(QMessageBox.StandardButton.Cancel)
        msg.exec()
        return msg.clickedButton() == btn_ignore

    def _action_new_profile(self) -> None:
        if self.profile_manager is None:
            return
        dlg = NewProfileDialog(self.profile_manager, self)
        if not dlg.exec() or dlg.created is None:
            return
        self._switch_profile(dlg.created.id)

    def _action_open_existing_profile(self) -> None:
        if self.profile_manager is None:
            return
        folder = QFileDialog.getExistingDirectory(
            self, "Vyber existující složku profilu (s db.json)", str(Path.home())
        )
        if not folder:
            return
        name, ok = QInputDialog.getText(
            self,
            "Název profilu",
            "Jak chceš profil pojmenovat?",
            text=Path(folder).name,
        )
        if not ok or not name.strip():
            return
        try:
            profile = self.profile_manager.create(name.strip(), Path(folder))
        except ProfileError as exc:
            QMessageBox.critical(self, "Vytvoření selhalo", str(exc))
            return
        self._switch_profile(profile.id)

    def _action_import_into_current(self) -> None:
        """Import dat z jiného profilu do aktuálního (přepíše db, doplní soubory).

        Vždy předem vytvoří 'before-import' zálohu pro recovery.
        """
        if self.profile_manager is None or self.profile_manager.active is None:
            return

        dlg = ImportIntoCurrentDialog(self.profile_manager, self)
        if not dlg.exec() or dlg.source_id is None:
            return

        active = self.profile_manager.active
        data_dir = self.profile_manager.active_data_dir()
        db_path = data_dir / "db.json"

        # 1) Flush pending changes ve všech detail panelech
        for i in range(self.tabs.count()):
            w = self.tabs.widget(i)
            if isinstance(w, _ThesesTab):
                try:
                    w.detail.flush()
                except Exception:
                    pass

        # 2) Bezpečnostní záloha aktuálního stavu PŘED přepsáním
        bm = BackupManager(data_dir)
        try:
            bm.create_backup(db_path, suffix="before-import", dedupe=False)
        except Exception:  # noqa: BLE001
            # Záloha selhala (např. db.json neexistuje) — pokračujeme bez ní
            pass

        # 3) Provést kopii
        try:
            stats = self.profile_manager.copy_data_into_profile(
                source_id=dlg.source_id,
                target_id=active.id,
                include_documents=dlg.include_documents,
                include_harmonograms=dlg.include_harmonograms,
                overwrite=True,
            )
        except ProfileError as exc:
            QMessageBox.critical(self, "Import selhal", str(exc))
            return

        # 4) Reload service nad přepsanou DB + refresh UI
        self.service.reload()
        self._refresh_all()

        QMessageBox.information(
            self,
            "Import dokončen",
            f"Data importována z profilu „{self.profile_manager.get(dlg.source_id).name}“ "
            f"do „{active.name}“.\n\n"
            f"db.json: {stats['db']}\n"
            f"dokumenty (složek): {stats['documents']}\n"
            f"harmonogramy (souborů): {stats['harmonograms']}\n\n"
            "Pokud bys chtěl předchozí stav vrátit, je k dispozici v "
            "👤 → 💾 Zálohy (značka „before-import“).",
        )

    def _action_export_profile_zip(self) -> None:
        """Export aktuálního profilu jako ZIP."""
        if self.profile_manager is None or self.profile_manager.active is None:
            return
        # Flushni rozpracované změny ve všech detail panelech, aby ZIP měl
        # i poslední editaci.
        for i in range(self.tabs.count()):
            w = self.tabs.widget(i)
            if isinstance(w, _ThesesTab):
                try:
                    w.detail.flush()
                except Exception:
                    pass
        dlg = ExportProfileDialog(
            self.profile_manager, self.profile_manager.active, self
        )
        dlg.exec()

    def _action_import_profile_zip(self) -> None:
        """Import profilu ze ZIPu — vytvoří nový profil nebo provede merge.

        Po dokončení (oba módy) přepne aplikaci na cílový profil.
        Pokud je cílový profil už aktivní (merge), provede se reload
        dat (service.reload + refresh UI) — uživatel ihned vidí přidané
        položky.
        """
        if self.profile_manager is None:
            return
        dlg = ImportProfileDialog(self.profile_manager, self)
        if not dlg.exec() or dlg.created is None:
            return

        # Pokud se merguje do aktuálního profilu, _switch_profile by ho
        # přeskočil. Místo toho udělej reload + refresh.
        active = self.profile_manager.active
        if active is not None and active.id == dlg.created.id:
            self.service.reload()
            self._refresh_all()
            self._refresh_profile_menu()
        else:
            self._switch_profile(dlg.created.id)
            self._refresh_profile_menu()

    def _action_manage_profiles(self) -> None:
        if self.profile_manager is None:
            return
        dlg = ProfileManageDialog(self.profile_manager, self)
        dlg.exec()
        self._refresh_profile_menu()

    def _action_backup_now(self) -> None:
        """Rychlá ruční záloha aktuálního stavu (bez otevírání manažeru)."""
        if self.profile_manager is None or self.profile_manager.active is None:
            return
        data_dir = self.profile_manager.active_data_dir()
        db_path = data_dir / "db.json"
        if not db_path.exists():
            QMessageBox.warning(self, "Záloha", "Databáze zatím neexistuje.")
            return
        try:
            info = BackupManager(data_dir).create_backup(
                db_path, suffix="manual", dedupe=False
            )
        except OSError as exc:
            QMessageBox.critical(self, "Záloha selhala", str(exc))
            return
        name = info.path.name if info else "(záloha)"
        QMessageBox.information(
            self, "Záloha vytvořena", f"Vytvořena ruční záloha:\n{name}"
        )

    def _action_show_backups(self) -> None:
        if self.profile_manager is None or self.profile_manager.active is None:
            return
        data_dir = self.profile_manager.active_data_dir()
        bm = BackupManager(data_dir)
        dlg = BackupBrowserDialog(bm, data_dir / "db.json", self)
        dlg.restored.connect(self._on_backup_restored)
        dlg.exec()

    def _on_backup_restored(self) -> None:
        # Po obnově db.json přemontuj service nad ten samý profil
        self.service.reload()
        self._refresh_all()

    # --- akce ----------------------------------------------------------------

    def _new_thesis_smart(self) -> None:
        """Tab-aware varianta + Nová práce — default status z aktuálního tabu.

        Mapování:
          Aktuální → V řešení (IN_PROGRESS) v aktuálním roce
          Budoucí → Vypsané téma (LISTED) v příštím roce
          Historie → Obhájeno (DEFENDED) v minulém roce
          Vše / Oponentury → Vypsané téma v aktuálním roce
        """
        current_year = ThesisService.current_academic_year()
        next_year = ThesisService.next_academic_year()
        previous_year = ThesisService.previous_academic_year()

        active = self.tabs.currentWidget()
        if active is self.tab_current:
            self._new_thesis(current_year, ThesisStatus.IN_PROGRESS)
        elif active is self.tab_future:
            self._new_thesis(next_year, ThesisStatus.LISTED)
        elif active is self.tab_history:
            self._new_thesis(previous_year, ThesisStatus.DEFENDED)
        else:
            self._new_thesis(current_year, ThesisStatus.LISTED)

    def _new_thesis(self, year: str, status: ThesisStatus = ThesisStatus.RESERVED) -> None:
        thesis_type_label, ok = QInputDialog.getItem(
            self,
            "Typ práce",
            "Vyber typ nové práce:",
            [t.label for t in ThesisType],
            0,
            False,
        )
        if not ok:
            return
        thesis_type = next(t for t in ThesisType if t.label == thesis_type_label)
        thesis = Thesis(type=thesis_type, status=status, academic_year=year)
        self.service.upsert_thesis(thesis)
        self._refresh_all()
        self._focus_thesis(thesis.id)

    def _new_future_thesis(self) -> None:
        """Dialog nové budoucí práce — volitelně předvyplní studenta, obor,
        název a anotaci. Nic není povinné; stav default *Vypsané téma*."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Nová budoucí práce")
        dialog.setMinimumWidth(500)
        layout = QVBoxLayout(dialog)
        form = QFormLayout()

        cb_type = QComboBox()
        for t in ThesisType:
            cb_type.addItem(t.label, t.value)
        ed_year = QLineEdit(ThesisService.next_academic_year())

        cb_status = QComboBox()
        for s in (ThesisStatus.LISTED, ThesisStatus.RESERVED, ThesisStatus.INTERESTED):
            cb_status.addItem(s.label, s.value)

        cb_student = QComboBox()
        cb_student.addItem("(bez studenta)", None)
        for st in self.service.list_students():
            cb_student.addItem(st.full_name, st.id)
        btn_new_student = QPushButton("+ Nový")
        btn_new_student.setToolTip("Založit nového studenta (vč. oboru).")
        student_row = QHBoxLayout()
        student_row.setContentsMargins(0, 0, 0, 0)
        student_row.addWidget(cb_student, stretch=1)
        student_row.addWidget(btn_new_student)
        student_widget = QWidget()
        student_widget.setLayout(student_row)

        # Obor je vždy editovatelný (pole je nepovinné); při výběru studenta se
        # předvyplní jeho oborem.
        cb_obor = QComboBox()
        cb_obor.setEditable(True)
        cb_obor.addItem("")
        for o in self.service.list_obor_objects():
            cb_obor.addItem(o.name)
        cb_obor.lineEdit().setPlaceholderText("Obor (nepovinné)")

        def _on_student() -> None:
            sid = cb_student.currentData()
            if sid:
                st = self.service.get_student(sid)
                cb_obor.setCurrentText((st.obor if st else "") or "")

        cb_student.currentIndexChanged.connect(lambda _i: _on_student())

        def _new_student() -> None:
            from .student_dialog import StudentDialog

            dlg = StudentDialog(self.service, parent=dialog)
            if dlg.exec() != QDialog.DialogCode.Accepted:
                return
            new_st = dlg.student
            cb_student.addItem(new_st.full_name, new_st.id)
            cb_student.setCurrentIndex(cb_student.count() - 1)  # vyvolá _on_student
            if new_st.obor:
                cb_obor.setCurrentText(new_st.obor)

        btn_new_student.clicked.connect(_new_student)

        ed_title = QLineEdit()
        ed_anot = QPlainTextEdit()
        ed_anot.setMaximumHeight(110)

        form.addRow("Typ", cb_type)
        form.addRow("Akademický rok", ed_year)
        form.addRow("Stav", cb_status)
        form.addRow("Student", student_widget)
        form.addRow("Obor", cb_obor)
        form.addRow("Název", ed_title)
        form.addRow("Anotace", ed_anot)
        layout.addLayout(form)

        hint = QLabel(
            "Nepovinné — co nevyplníš, zůstane prázdné. Obor se ukládá "
            "ke zvolenému studentovi (jen pokud je zvolen)."
        )
        hint.setStyleSheet("color:#888;")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        thesis = Thesis(
            type=ThesisType(cb_type.currentData()),
            status=ThesisStatus(cb_status.currentData()),
            academic_year=ed_year.text().strip(),
        )
        thesis.title_cs = ed_title.text().strip()
        thesis.annotation = ed_anot.toPlainText().strip()
        sid = cb_student.currentData()
        if sid:
            thesis.student_id = sid
            obor_text = cb_obor.currentText().strip()
            st = self.service.get_student(sid)
            if st is not None and obor_text and (st.obor or "") != obor_text:
                st.obor = obor_text
                self.service.upsert_student(st)
        self.service.upsert_thesis(thesis)
        self._refresh_all()
        self._focus_thesis(thesis.id)

    def _new_past_thesis(self) -> None:
        """Dialog pro přidání historické práce — libovolný rok, typ, stav."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Přidat minulou práci")
        dialog.setMinimumWidth(420)

        layout = QVBoxLayout(dialog)
        form = QFormLayout()

        ed_year = QLineEdit(ThesisService.previous_academic_year())
        ed_year.setPlaceholderText("např. 2024/2025")

        cb_type = QComboBox()
        for t in ThesisType:
            cb_type.addItem(t.label, t.value)

        cb_status = QComboBox()
        past_statuses = [
            ThesisStatus.DEFENDED,
            ThesisStatus.IN_PROGRESS,
            ThesisStatus.CANCELLED,
        ]
        for s in past_statuses:
            cb_status.addItem(s.label, s.value)

        form.addRow("Akademický rok", ed_year)
        form.addRow("Typ", cb_type)
        form.addRow("Stav", cb_status)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        year = ed_year.text().strip()
        if not year:
            return

        thesis_type = ThesisType(cb_type.currentData())
        status = ThesisStatus(cb_status.currentData())
        thesis = Thesis(type=thesis_type, status=status, academic_year=year)
        self.service.upsert_thesis(thesis)
        self._refresh_all()
        self._focus_thesis(thesis.id)

    def _focus_thesis(self, thesis_id: str) -> None:
        for i in range(self.tabs.count()):
            widget = self.tabs.widget(i)
            if isinstance(widget, _ThesesTab) and widget.tree.select_thesis(thesis_id):
                self.tabs.setCurrentIndex(i)
                widget.detail.set_thesis(self.service.get_thesis(thesis_id))
                return

    def _on_proposal_converted(self, thesis_id: str) -> None:
        """Návrh byl převeden na vedenou práci — obnov a přejdi na ni."""
        self._refresh_all()
        self._focus_thesis(thesis_id)

    def _manage_students(self) -> None:
        StudentsManageDialog(self.service, self).exec()
        self._refresh_all()

    def _manage_opponents(self) -> None:
        OpponentsManageDialog(self.service, self).exec()
        self._refresh_all()

    def _manage_supervisors(self) -> None:
        SupervisorsManageDialog(self.service, self).exec()
        self._refresh_all()

    def _manage_rejected(self) -> None:
        from .rejected_students_dialog import RejectedStudentsDialog

        RejectedStudentsDialog(self.service, self).exec()
        self._refresh_all()

    def _manage_obory(self) -> None:
        OboryManageDialog(self.service, self).exec()
        self._refresh_all()

    def _manage_review_templates(self) -> None:
        ReviewTemplatesDialog(
            self.service, self, profile_manager=self.profile_manager
        ).exec()

    def _import_thesis_zip(self) -> None:
        """Importuje práci z dříve vyexportovaného ZIP balíku."""
        from ..services.thesis_export import ThesisExportError, import_thesis_from_zip

        path_str, _ = QFileDialog.getOpenFileName(
            self, "Import práce ze ZIP", str(Path.home()), "ZIP balík (*.zip)"
        )
        if not path_str:
            return
        try:
            new_id = import_thesis_from_zip(self.service, Path(path_str))
        except (ThesisExportError, OSError) as exc:
            QMessageBox.critical(self, "Import", f"Import selhal:\n{exc}")
            return
        self._refresh_all()
        self._focus_thesis(new_id)
        QMessageBox.information(self, "Import hotov", "Práce byla naimportována.")

    def _check_stag_consistency(self) -> None:
        """Kontrola: které soubory STAG nabízí a v DB chybí (+ dostažení)."""
        dlg = StagConsistencyDialog(
            self.service, self, profile_manager=self.profile_manager
        )
        dlg.exec()
        if dlg.changed_any:
            self._refresh_all()

    def _reclassify_defense_records(self) -> None:
        """Přeřadí přílohy „Jiné" na „Soubor s průběhem obhajoby".

        Protože se původní názvy souborů při stažení ztrácí, dialog je znovu
        dotáhne ze STAG, obnoví původní názvy a v náhledu (s checkboxy) nabídne
        přeřazení; po potvrzení přeřadí (se zálohou).
        """
        from .defense_reclassify_dialog import DefenseReclassifyDialog

        dlg = DefenseReclassifyDialog(
            self.service, self, profile_manager=self.profile_manager
        )
        dlg.exec()
        if dlg.changed:
            self._refresh_all()

    def _import_from_stag(self) -> None:
        """Otevře wizard pro import dat z STAG CSV exportu.

        Po úspěšném importu se aplikace přepne na poslední importovanou
        práci (resp. oponentský posudek) — uživatel ji rovnou vidí.
        """
        # Flushni rozpracované změny v detail panelech, aby je import nepřepsal
        for i in range(self.tabs.count()):
            w = self.tabs.widget(i)
            if isinstance(w, _ThesesTab):
                try:
                    w.detail.flush()
                except Exception:
                    pass

        dlg = StagImportDialog(self.service, self.profile_manager, self)
        if not dlg.exec():
            return  # zrušeno před zápisem

        # Refresh všeho — data, registry, stromy, comba
        self._refresh_all()

        # Auto-navigate na importovanou práci/posudek
        if dlg.focus_thesis_id:
            self._focus_thesis(dlg.focus_thesis_id)
        elif dlg.focus_opposing_id:
            self._focus_opposing_thesis(dlg.focus_opposing_id)

        # Po importu/aktualizaci přepočítej indikátor STAG (banner + odznaky).
        self._start_stag_check()

    def _focus_opposing_thesis(self, opposing_id: str) -> None:
        """Přepne se na záložku Oponentské posudky a vybere konkrétní záznam."""
        for i in range(self.tabs.count()):
            widget = self.tabs.widget(i)
            if isinstance(widget, OpposingTab):
                self.tabs.setCurrentIndex(i)
                try:
                    widget._select_id(opposing_id)
                except Exception:
                    pass
                return

    def _refresh_all(self) -> None:
        self.service.reload()
        for i in range(self.tabs.count()):
            widget = self.tabs.widget(i)
            if isinstance(widget, _ThesesTab):
                widget.refresh()
                # Combo se studenty/oponenty obnov taky — když uživatel
                # přidal studenta/oponenta v management dialogu, ať se
                # hned objeví v rozbalovači u Téma zadání.
                widget.detail.refresh_combos()
            elif isinstance(widget, OpposingTab):
                widget.refresh()
                widget.refresh_combos()
            elif isinstance(widget, ProposalsTab):
                widget.refresh()
            elif isinstance(widget, HarmonogramTab):
                widget._refresh_year_combo()
            elif isinstance(widget, StatsTab):
                widget.refresh()
        self._update_status()
        self._refresh_tab_labels()

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802 (Qt API)
        """Při zavření okna ještě flushne všechny dirty formuláře."""
        for i in range(self.tabs.count()):
            widget = self.tabs.widget(i)
            if isinstance(widget, _ThesesTab):
                widget.detail.flush()
        super().closeEvent(event)

    def _update_status(self) -> None:
        theses = self.service.list_theses()
        opposings = self.service.list_opposing_theses()
        total = len(theses)
        students = len(self.service.list_students())
        opponents = len(self.service.list_opponents())
        obory = len(self.service.list_obory())
        self.statusBar().showMessage(
            f"Vedené práce: {total} • Oponentury: {len(opposings)} • "
            f"Studenti: {students} • Oponenti: {opponents} • Obory: {obory}"
        )

        # Barevný souhrn posudků: vedoucí (jen práce „V řešení") + oponentury.
        in_progress = [t for t in theses if t.status == ThesisStatus.IN_PROGRESS]
        sup_done = sum(1 for t in in_progress if t.supervisor_review_state == "done")
        sup_draft = sum(1 for t in in_progress if t.supervisor_review_state == "draft")
        sup_missing = sum(1 for t in in_progress if t.supervisor_review_state == "none")
        opp_done = sum(1 for o in opposings if o.opponent_review_state == "done")
        opp_missing = sum(1 for o in opposings if o.opponent_review_state == "none")

        g, a, r = (
            REVIEW_STATE_STRONG["done"],
            REVIEW_STATE_STRONG["draft"],
            REVIEW_STATE_STRONG["none"],
        )
        draft_part = (
            f" · <span style='color:{a};'>rozpracováno {sup_draft}</span>"
            if sup_draft else ""
        )
        self._status_reviews.setText(
            f"Posudky vedoucího (V řešení): "
            f"<span style='color:{g};'>hotovo {sup_done}</span>{draft_part} · "
            f"<span style='color:{r};'>chybí {sup_missing}</span>"
            f" &nbsp;&nbsp;‖&nbsp;&nbsp; Oponentury: "
            f"<span style='color:{g};'>hotovo {opp_done}</span> · "
            f"<span style='color:{r};'>chybí {opp_missing}</span>"
        )
        # Počty v titulcích záložek (data se mohla změnit).
        self._refresh_tab_labels()

    # --- globální vyhledávání + navigace -------------------------------------

    def _do_search(self) -> None:
        query = self.ed_search.text().strip()
        if not query:
            return
        hits = self.service.search_works(query)
        if not hits:
            self.statusBar().showMessage(f"Nic nenalezeno: „{query}“", 4000)
            return
        if len(hits) == 1:
            self._navigate_hit(hits[0])
            return

        # Více shod → nabídni výběr (práce v „Aktuální" první, default).
        def rank(h: dict) -> int:
            if h["kind"] == "thesis" and h["status"] in STATUSES_CURRENT:
                return 0
            if h["kind"] == "thesis" and h["status"] in STATUSES_FUTURE:
                return 1
            if h["kind"] == "thesis" and h["status"] in STATUSES_HISTORY:
                return 2
            return 3  # oponentura
        hits = sorted(hits, key=lambda h: (rank(h), h["student"].lower()))

        menu = QMenu(self)
        head = menu.addAction(f"{len(hits)} shod — vyber práci:")
        head.setEnabled(False)
        menu.addSeparator()
        for h in hits:
            uid = f"  ·  {h['uid']}" if h["uid"] else ""
            act = menu.addAction(
                f"[{self._bucket_label(h)}]  {h['student']} — {h['title']}{uid}"
            )
            act.triggered.connect(
                lambda _checked=False, hit=h: self._navigate_hit(hit)
            )
        menu.exec(self.ed_search.mapToGlobal(self.ed_search.rect().bottomLeft()))

    def _bucket_label(self, hit: dict) -> str:
        if hit["kind"] == "opposing":
            return "Oponentura"
        s = hit["status"]
        if s in STATUSES_CURRENT:
            return "Aktuální"
        if s in STATUSES_FUTURE:
            return "Budoucí"
        if s in STATUSES_HISTORY:
            return "Historie"
        return "Vše"

    def _tab_for_status(self, status) -> "_ThesesTab":
        if status in STATUSES_CURRENT:
            return self.tab_current
        if status in STATUSES_FUTURE:
            return self.tab_future
        if status in STATUSES_HISTORY:
            return self.tab_history
        return self.tab_all

    def _navigate_hit(self, hit: dict) -> None:
        if hit["kind"] == "opposing":
            self.tabs.setCurrentWidget(self.tab_opposing)
            self.tab_opposing._select_id(hit["id"])
            return
        tab = self._tab_for_status(hit["status"])
        self.tabs.setCurrentWidget(tab)
        if not tab.tree.select_thesis(hit["id"]):
            # Práce nesedí do filtru tabu (krajní případ) → zkus „Vše".
            self.tabs.setCurrentWidget(self.tab_all)
            self.tab_all.tree.select_thesis(hit["id"])
