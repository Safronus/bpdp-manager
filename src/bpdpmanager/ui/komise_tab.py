"""Záložka „Komise" — komise SZZ po akademických rocích (složení + rozpis).

Vlevo strom *rok → komise* (barevný badge dle barvy komise), vpravo detail:
složení (role + jména, zvýrazněné tvoje členství) a rozpis studentů se
zvýrazněním 🎓 vedených (přes osobní číslo / jméno) a 🧐 oponovaných (jméno).
Import z fakultních PDF (složení i rozpis — druh se pozná sám); soubory se
ukládají strukturovaně do ``komise/<rok>/``.
"""

from __future__ import annotations

import unicodedata
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QStyle,
    QStyledItemDelegate,
    QTabWidget,
    QTextBrowser,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..i18n import tr
from ..models.komise import committee_color_hex
from ..services import ThesisService

#: Oficiální stránka FAI s PDF ke stažení (obecný odkaz, každý rok stejný).
FAI_KOMISE_URL = (
    "https://fai.utb.cz/student/statni-zaverecne-zkousky/"
    "statni-zaverecne-zkousky-szz/slozeni-komisi-szz-a-rozpis-studentu-na-szz/"
)

ROLE_COMMITTEE_ID = Qt.ItemDataRole.UserRole + 1
#: (vedené, oponované) počty studentů komise — pro StudentsVODelegate.
ROLE_VO = Qt.ItemDataRole.UserRole + 2
#: Absolutní cesta k PDF v seznamu souborů (otevření z kontextového menu).
ROLE_PDF_PATH = Qt.ItemDataRole.UserRole + 3
#: Druh uzlu stromu: "year" / "level" / "committee".
ROLE_KIND = Qt.ItemDataRole.UserRole + 4
ROLE_YEAR = Qt.ItemDataRole.UserRole + 5
ROLE_LEVEL = Qt.ItemDataRole.UserRole + 6

#: Stupeň → pořadí a popisek skupiny ve stromu (Bc před Mgr).
_LEVEL_ORDER = {"Bc": 0, "Mgr": 1}
_LEVEL_LABEL = {"Bc": "Bakalářské (Bc)", "Mgr": "Magisterské (Mgr)"}

#: Barvy badge ve sloupci „Studenti V/O" (vedené modře, oponované červeně).
_VO_LED_BG = "#1e88e5"
_VO_OPP_BG = "#e53935"

#: Barvy „rámečku" role člena komise (světlé pozadí, tmavý text/okraj).
_ROLE_COLORS = {
    "předseda": ("#ede7f6", "#4a148c"),       # fialová — předseda
    "místopředseda": ("#e3f2fd", "#0d47a1"),  # modrá — místopředseda
    "tajemník": ("#e8f5e9", "#1b5e20"),       # zelená — tajemník
    "člen": ("#eceff1", "#455a64"),           # šedá — člen
}
#: Kanonický popisek role (sjednotí „Členové" → „Člen").
_ROLE_LABEL = {
    "předseda": "Předseda", "místopředseda": "Místopředseda",
    "tajemník": "Tajemník", "člen": "Člen",
}


def _role_key(role: str) -> str:
    """Normalizuje název role na klíč do :data:`_ROLE_COLORS`."""
    r = _fold(role)
    if "predsed" in r and "mist" not in r:
        return "předseda"
    if "mistopredsed" in r or "místopředsed" in r:
        return "místopředseda"
    if "tajemn" in r:
        return "tajemník"
    return "člen"


def _fold(s: str) -> str:
    nfd = unicodedata.normalize("NFD", s or "")
    return "".join(c for c in nfd if not unicodedata.combining(c)).lower().strip()


#: Barvy textu čitelné na světlém i tmavém pozadí (panel detailu může být tmavý).
_MUTED = "#9aa0a6"     # sekundární text (datum, čas, osobní číslo)
_C_LED = "#43a047"     # vedené (zelená)
_C_OPP = "#ab47bc"     # oponované (fialová)
#: Barva klikacího odkazu na studenta. MUSÍ být explicitní — QTextBrowser
#: vyhodnotí ``color:inherit`` u <a> na ČERNOU (a přebije i paletu Link i CSS),
#: takže na tmavém pozadí by byl odkaz nečitelný. Světle modrá = čitelná na
#: tmavém a zároveň signalizuje klikatelnost.
_SZZ_LINK = "#8ab4f8"

#: STAG stav obhajoby → (emoji, popisek, barva) pro badge v rozpisu.
_STATE_BADGE = {
    "defended": ("✅", "Obhájeno", "#43a047"),
    "failed": ("❌", "Neobhájeno", "#ef5350"),
    "cancelled": ("⚠", "Nedokončeno", "#ffa726"),
    "unfinished": ("⚠", "Nedokončeno", "#ffa726"),  # kategorie ze statistiky komisí
}


def _defense_state_badge(states: dict | None, pnum: str, name: str) -> str:
    """HTML badge stavu obhajoby studenta (✅/❌/⚠) z tiché STAG kontroly.

    Páruje přes osobní číslo (Axxxxx), záložně přes foldované jméno.
    """
    if not states:
        return ""
    from ..services.komise_stats import student_name_key

    val = states.get((pnum or "").strip().upper()) or states.get(student_name_key(name))
    info = _STATE_BADGE.get(val) if val else None
    if not info:
        return ""
    emoji, label, color = info
    return f" <span style='color:{color};font-weight:bold;'>{emoji} {tr(label)}</span>"


def _szz_student_anchor(os_cislo: str, name: str, inner_html: str) -> str:
    """Obalí jméno studenta odkazem ``szz:OSCISLO?n=NAME`` (klik/kontext → souhrn SZZ).

    Odkaz má explicitní čitelnou barvu (``_SZZ_LINK``) — viz tam, proč nelze
    ``color:inherit``. Klik (i pravý) otevře souhrn SZZ studenta. Bez osobního
    čísla vrátí ``inner_html`` beze změny.
    """
    from urllib.parse import quote

    oc = (os_cislo or "").strip()
    if not oc:
        return inner_html
    href = "szz:" + oc + "?n=" + quote(name or "")
    return (f"<a href=\"{href}\" style=\"color:{_SZZ_LINK};text-decoration:none;\" "
            f"title=\"Souhrn SZZ studenta\">{inner_html}</a>")


def _parse_szz_href(href: str):
    """``szz:OSCISLO?n=NAME`` → ``(os_cislo, jmeno)`` nebo ``None``."""
    from urllib.parse import unquote

    if not href or not str(href).startswith("szz:"):
        return None
    oc, _, q = str(href)[4:].partition("?")
    oc = oc.strip()
    name = unquote(q[2:]) if q.startswith("n=") else ""
    return (oc, name) if oc else None


class StudentsVODelegate(QStyledItemDelegate):
    """Sloupec „Studenti V/O": vedené číslo v modrém a oponované v červeném
    zaobleném badge vedle sebe (styl jako známky u prací). Prázdné = beze
    studentů; badge se ukáže jen pro nenulový počet."""

    _GAP = 6
    _PAD = 7
    _MIN_W = 22
    _BADGE_H = 18

    @staticmethod
    def _counts(index):
        v = index.data(ROLE_VO)
        return v if isinstance(v, (tuple, list)) and len(v) == 2 else None

    def _badges(self, led: int, opp: int):
        out = []
        if led:
            out.append((str(led), _VO_LED_BG))
        if opp:
            out.append((str(opp), _VO_OPP_BG))
        return out

    def _width(self, fm, badges) -> int:
        if not badges:
            return 0
        w = sum(max(self._MIN_W, fm.horizontalAdvance(t) + 2 * self._PAD)
                for t, _ in badges)
        return w + self._GAP * (len(badges) - 1)

    def paint(self, painter, option, index) -> None:
        counts = self._counts(index)
        if counts is None:
            super().paint(painter, option, index)
            return
        led, opp = counts
        badges = self._badges(led, opp)
        painter.save()
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
        fm = option.fontMetrics
        total = self._width(fm, badges)
        rect = option.rect
        x = rect.x() + max(4, (rect.width() - total) // 2)
        y = rect.y() + (rect.height() - self._BADGE_H) // 2
        font = painter.font()
        font.setBold(True)
        painter.setFont(font)
        for text, bg in badges:
            w = max(self._MIN_W, fm.horizontalAdvance(text) + 2 * self._PAD)
            br = QRectF(x, y, w, self._BADGE_H)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(bg))
            painter.drawRoundedRect(br, 4, 4)
            painter.setPen(QColor("white"))
            painter.drawText(br, Qt.AlignmentFlag.AlignCenter, text)
            x += w + self._GAP
        painter.restore()

    def sizeHint(self, option, index) -> QSize:  # noqa: N802 (Qt API)
        counts = self._counts(index)
        if counts is None:
            return super().sizeHint(option, index)
        badges = self._badges(*counts)
        base = super().sizeHint(option, index)
        return QSize(self._width(option.fontMetrics, badges) + 12,
                     max(base.height(), self._BADGE_H + 6))


class KomiseTab(QWidget):
    """Komise SZZ: strom roků/komisí + detail (složení, rozpis, zvýraznění)."""

    changed = Signal()
    open_szz_admin = Signal()         # požadavek otevřít okno Státnice (admin)
    open_szz_student = Signal(str, str)   # (os_cislo, jmeno) → souhrn SZZ studenta

    def __init__(self, service: ThesisService, parent=None, *,
                 profile_manager=None) -> None:
        super().__init__(parent)
        self.service = service
        self.profile_manager = profile_manager
        # Stav obhajob z tiché STAG kontroly (klíč → stav); plní se v období
        # státnic. Inicializace před první refresh() (detail ho čte).
        self._stag_states: dict = {}
        self._state_checker = None
        # Kategorie obhajob VŠECH studentů komisí (statistika dole) — cache
        # napříč překreslením; terminální stavy se ze STAG znovu nedotazují.
        # Načte se z disku (z minulého běhu), ať se statistika ukáže hned a STAG
        # se nemusí ptát na už zjištěné studenty.
        self._committee_states: dict = self.service.load_komise_defense_states()
        self._stats_checker = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)

        # ── horní lišta ──────────────────────────────────────────────────
        top = QHBoxLayout()
        btn_import = QPushButton(tr("📄 Import PDF rozpisu studentů…"))
        btn_import.setToolTip(tr(
            "Načte fakultní PDF rozpisu studentů (komise se pozná podle barvy "
            "nadpisů a oboru, studenti se napojí na správnou komisi). Lze načíst "
            "i složení komisí. PDF se přejmenují a uloží do komise/<rok>/."
        ))
        btn_import.clicked.connect(self._import_pdfs)
        top.addWidget(btn_import)
        btn_reset = QPushButton(tr("🔄 Načíst komise znovu"))
        btn_reset.setToolTip(tr(
            "Smaže všechny komise a načte čisté složení z aplikace. Použij na "
            "úklid starých naimportovaných komisí, které nesedí (chybí obor, "
            "duplicity). Rozpisy studentů z dříve nahraných PDF zmizí — nahraj "
            "je znovu."
        ))
        btn_reset.clicked.connect(self._reset_committees)
        top.addWidget(btn_reset)
        btn_sched = QPushButton(tr("📅 Můj harmonogram obhajob"))
        btn_sched.setToolTip(tr(
            "Chronologický přehled, kdy a kde obhajují studenti, které vedeš "
            "nebo oponuješ — tvůj osobní rozvrh u komisí."
        ))
        btn_sched.clicked.connect(self._show_my_schedule)
        top.addWidget(btn_sched)
        self.chk_mine = QCheckBox(tr("Jen komise s mými studenty"))
        self.chk_mine.toggled.connect(self.refresh)
        top.addWidget(self.chk_mine)
        top.addStretch(1)
        self.lbl_legend = QLabel(
            "<span style='background:#c8e6c9;'>&nbsp;🎓&nbsp;</span> "
            + tr("vedený student") + " &nbsp; "
            "<span style='background:#e1bee7;'>&nbsp;🧐&nbsp;</span> "
            + tr("oponovaný student") + " &nbsp; ⭐ " + tr("tvoje komise")
        )
        self.lbl_legend.setTextFormat(Qt.TextFormat.RichText)
        top.addWidget(self.lbl_legend)
        outer.addLayout(top)

        # ── 3 panely: vlevo komise+PDF (dle obsahu), uprostřed detail komise,
        #    vpravo nezávislý harmonogram (dle obsahu); prostřední bere zbytek.
        # QSplitter (ne fixed-width QHBoxLayout) → na malém okně se panely
        # zmenší/ořežou (nikdy nepřekrývají) a uživatel je může přetáhnout.
        # Na velkém monitoru zůstává rozložení stejné: _fit_panels dá splitteru
        # přes setSizes přesně dopočítané šířky (součet = šířka → bez škálování).
        self.cols_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.cols_splitter.setHandleWidth(8)
        self.cols_splitter.setChildrenCollapsible(True)
        # Po ručním přetažení přestaneme auto-dopočítávat šířky (necháme volbu
        # uživatele) — viz _on_cols_splitter_moved / _fit_panels.
        self._cols_user_adjusted = False

        left = QSplitter(Qt.Orientation.Vertical)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels([tr("Komise"), tr("Studenti V/O"), tr("Termíny")])
        self.tree.setRootIsDecorated(True)
        self.tree.setItemDelegateForColumn(1, StudentsVODelegate(self.tree))
        hdr = self.tree.header()
        # Šířka sloupců dle dat; levý panel se přizpůsobí v _fit_panels.
        for col in range(self.tree.columnCount()):
            hdr.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setStretchLastSection(False)
        self.tree.itemSelectionChanged.connect(self._on_selected)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._on_context_menu)
        # Filtr komisí podle jména člena / studenta (část jména, bez diakritiky).
        tree_box = QWidget()
        tbl = QVBoxLayout(tree_box)
        tbl.setContentsMargins(0, 0, 0, 0)
        tbl.setSpacing(4)
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText(
            tr("🔎 Filtr: jméno člena nebo studenta…"))
        self.filter_edit.setClearButtonEnabled(True)
        self.filter_edit.setToolTip(tr(
            "Zobrazí jen komise, kde je člen nebo student odpovídající textu "
            "(stačí část jména, nezáleží na velikosti písmen ani diakritice)."
        ))
        self.filter_edit.textChanged.connect(self.refresh)
        tbl.addWidget(self.filter_edit)
        tbl.addWidget(self.tree)
        left.addWidget(tree_box)

        # Seznam PDF souborů (rok → Složení / Rozpisy), otevíratelné z menu.
        pdf_box = QWidget()
        pv = QVBoxLayout(pdf_box)
        pv.setContentsMargins(0, 6, 0, 0)
        pv.setSpacing(2)
        pdf_head = QHBoxLayout()
        pdf_head.setContentsMargins(0, 0, 0, 0)
        pdf_head.addWidget(QLabel("📎 " + tr("PDF soubory")))
        pdf_head.addStretch(1)
        lbl_dl = QLabel(
            f"<a href='{FAI_KOMISE_URL}'>⬇ {tr('Stáhnout z webu FAI')}</a>"
        )
        lbl_dl.setOpenExternalLinks(True)
        lbl_dl.setToolTip(tr("Otevře stránku FAI s PDF složení komisí a rozpisů "
                             "ke stažení (obecný odkaz, každý rok stejný)."))
        pdf_head.addWidget(lbl_dl)
        pv.addLayout(pdf_head)
        self.pdf_tree = QTreeWidget()
        self.pdf_tree.setHeaderHidden(True)
        self.pdf_tree.setRootIsDecorated(True)
        # Dlouhé názvy PDF se elidují (…) a nedrží šířku levého panelu — ten
        # se řídí stromem komisí. Plný název je v tooltipu.
        self.pdf_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.pdf_tree.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.pdf_tree.setSelectionMode(
            QTreeWidget.SelectionMode.ExtendedSelection
        )
        self.pdf_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.pdf_tree.customContextMenuRequested.connect(self._on_pdf_context_menu)
        self.pdf_tree.itemDoubleClicked.connect(lambda *_: self._open_selected_pdfs())
        pv.addWidget(self.pdf_tree)
        left.addWidget(pdf_box)
        left.setStretchFactor(0, 3)
        left.setStretchFactor(1, 1)
        self.left_container = QWidget()
        lc = QVBoxLayout(self.left_container)
        lc.setContentsMargins(0, 0, 0, 0)
        lc.addWidget(left)
        self.cols_splitter.addWidget(self.left_container)

        # Prostřední panel: nahoře detail komise (členové + studenti) / přehled,
        # který na výšku FITUJE OBSAH; dole sekce statistiky obhajob, která bere
        # zbývající výšku.
        self.detail = QTextBrowser()
        # Linky neotvírat „navigací" (QTextBrowser by PDF načetl jako text =
        # změť) — odkaz na PDF otevřeme systémově, web v prohlížeči.
        self.detail.setOpenLinks(False)
        self.detail.anchorClicked.connect(self._open_detail_link)
        # Bez zalamování — na úzkém okně se obsah (termíny po dnech) nevejde na
        # šířku, ale místo nafouknutí do výšky se přidá **vodorovný posuvník**.
        self.detail.setLineWrapMode(QTextBrowser.LineWrapMode.NoWrap)
        self.detail.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        # Horní detail se výškově přizpůsobuje obsahu (viz _fit_detail_height).
        self.detail.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        stats_box = QWidget()
        sbl = QVBoxLayout(stats_box)
        sbl.setContentsMargins(0, 6, 0, 0)
        stats_hdr = QHBoxLayout()
        stats_hdr.setContentsMargins(0, 0, 0, 0)
        self.lbl_stats = QLabel("📊 Statistika obhajob")
        stats_hdr.addWidget(self.lbl_stats)
        stats_hdr.addStretch()
        # Průběh kontroly ze STAG (vlevo od tlačítka): „kontroluji X/Y" → „hotovo".
        self.lbl_stats_progress = QLabel("")
        self.lbl_stats_progress.setStyleSheet(f"color:{_MUTED};")
        stats_hdr.addWidget(self.lbl_stats_progress)
        self.btn_refresh_stats = QPushButton("🔄 Aktualizovat")
        self.btn_refresh_stats.setToolTip(
            "Vynutí kontrolu ze STAG u všech zbývajících studentů „bez "
            "obhajoby\", jejichž obhajoba je **dnes nebo dříve** (budoucí dny "
            "se přeskočí) — i když na ně podle harmonogramu ještě nepřišla řada "
            "(průběh může jít rychleji). Hotové se cachují a tichá kontrola je "
            "už znovu neřeší. (Tichá kontrola na pozadí drží časové okno.)"
        )
        self.btn_refresh_stats.clicked.connect(self._refresh_stats_now)
        stats_hdr.addWidget(self.btn_refresh_stats)
        sbl.addLayout(stats_hdr)

        # Statistika je VŽDY ve 3 záložkách (na velkém i malém rozlišení) —
        # každá sekce dostane plnou šířku a vlastní posuvníky. Sjednocené,
        # konzistentní a bez křehkého přeparentování mezi režimy.
        self.stats_committee = QTextBrowser()
        self.stats_committee.setOpenExternalLinks(False)
        self.stats_members = QTextBrowser()
        self.stats_members.setOpenExternalLinks(False)
        self.stats_chart = _DefenseBarChart()

        # Graf ve scroll area (vlastní svislý/vodorovný posuvník, když je málo
        # místa).
        self.stats_chart_scroll = QScrollArea()
        self.stats_chart_scroll.setWidgetResizable(True)
        self.stats_chart_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.stats_chart_scroll.setWidget(self.stats_chart)

        # Záložka Průběh SZZ (admin): lišta s tlačítkem + indikací nad výpisem.
        self.stats_szz = QTextBrowser()
        self.stats_szz.setOpenExternalLinks(False)
        self.stats_szz.setOpenLinks(False)
        # Klik na jméno v sekci „Neúspěšní studenti" otevře souhrn SZZ studenta.
        self.stats_szz.anchorClicked.connect(self._handle_szz_url)
        self.stats_szz.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.stats_szz.customContextMenuRequested.connect(
            lambda p: self._szz_context_menu(self.stats_szz, p))
        szz_panel = QWidget()
        szz_v = QVBoxLayout(szz_panel)
        szz_v.setContentsMargins(0, 0, 0, 0)
        szz_bar = QHBoxLayout()
        self.btn_szz_admin = QPushButton(tr("🔐 Stáhnout / aktualizovat…"))
        self.btn_szz_admin.setToolTip(tr(
            "Otevře okno Státnice (admin) — přihlášení do portálu a stažení "
            "průběhu SZZ (vyžaduje roli Zapisovatel státnic)."))
        self.btn_szz_admin.clicked.connect(self.open_szz_admin.emit)
        szz_bar.addWidget(self.btn_szz_admin)
        self.lbl_szz_status = QLabel("")
        self.lbl_szz_status.setStyleSheet(f"color:{_MUTED};")
        szz_bar.addWidget(self.lbl_szz_status)
        szz_bar.addStretch(1)
        szz_v.addLayout(szz_bar)
        szz_v.addWidget(self.stats_szz, 1)

        self.stats_tabs = QTabWidget()
        self.stats_tabs.setDocumentMode(True)
        self.stats_tabs.addTab(self.stats_committee, tr("📋 Podle komise"))
        self.stats_tabs.addTab(self.stats_chart_scroll, tr("📊 Graf"))
        self.stats_tabs.addTab(self.stats_members, tr("👤 Podle členů"))
        self.stats_tabs.addTab(szz_panel, tr("🏛 Průběh SZZ"))
        sbl.addWidget(self.stats_tabs, stretch=1)

        mid = QWidget()
        mid.setMinimumWidth(300)
        ml = QVBoxLayout(mid)
        ml.setContentsMargins(0, 0, 0, 0)
        ml.addWidget(self.detail)            # nahoře: fituje obsah na výšku
        ml.addWidget(stats_box, stretch=1)   # dole: bere zbývající výšku
        self.cols_splitter.addWidget(mid)

        # Pravý panel: nezávislý „Můj harmonogram obhajob" pro vybraný rok.
        self.harmonogram_view = QTextBrowser()
        self.harmonogram_view.setOpenExternalLinks(False)
        self.harmonogram_view.setOpenLinks(False)
        self.harmonogram_view.anchorClicked.connect(self._handle_szz_url)
        self.harmonogram_view.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu)
        self.harmonogram_view.customContextMenuRequested.connect(
            lambda p: self._szz_context_menu(self.harmonogram_view, p))
        self.detail.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.detail.customContextMenuRequested.connect(
            lambda p: self._szz_context_menu(self.detail, p))
        self.right_container = QWidget()
        rcl = QVBoxLayout(self.right_container)
        rcl.setContentsMargins(0, 0, 0, 0)
        self.btn_add_calendar = QPushButton("📆 Přidat do kalendáře")
        self.btn_add_calendar.setToolTip(
            "Nadcházející obhajoby z vybraného roku do kalendáře "
            "(Apple / Outlook / Google) jako .ics s připomínkou."
        )
        self.btn_add_calendar.clicked.connect(self._on_add_to_calendar)
        rcl.addWidget(self.btn_add_calendar)
        rcl.addWidget(self.harmonogram_view)
        self.cols_splitter.addWidget(self.right_container)

        # Minima panelů: auto-fit (setSizes) je nesmí přerůst; pod nimi se
        # ořezává (ne překrývá). Prostřední je chráněný širším minimem.
        self.left_container.setMinimumWidth(150)
        self.right_container.setMinimumWidth(150)
        self.cols_splitter.setStretchFactor(0, 0)
        self.cols_splitter.setStretchFactor(1, 1)   # extra šířku bere prostřední
        self.cols_splitter.setStretchFactor(2, 0)
        self.cols_splitter.splitterMoved.connect(self._on_cols_splitter_moved)
        outer.addWidget(self.cols_splitter, stretch=1)

        # Malá minima vnitřních widgetů, ať se obsah dá na úzkém monitoru
        # zmenšit (jinak by intrinsic minima bránila zmenšení a pravý panel by
        # se ořízl). Na velkém monitoru se nic nemění — šířky řídí _fit_panels.
        for _w in (self.tree, self.pdf_tree, self.detail, self.stats_committee,
                   self.stats_members, self.stats_chart, self.harmonogram_view):
            _w.setMinimumWidth(60)

        self._right_year = None
        self.refresh()

        # Tichá kontrola stavu obhajob (jen v období státnic) — vizualizuje,
        # kdo z mých studentů už obhájil. Nezapisuje do DB. Každých 15 minut.
        self._state_timer = QTimer(self)
        self._state_timer.setInterval(15 * 60_000)
        self._state_timer.timeout.connect(self._maybe_check_states)
        self._state_timer.timeout.connect(self._maybe_check_committee_stats)
        self._state_timer.start()
        QTimer.singleShot(3000, self._maybe_check_states)
        QTimer.singleShot(3500, self._maybe_check_committee_stats)

        # Odpočet u nejbližší obhajoby — překresli pravý panel každou minutu.
        self._countdown_timer = QTimer(self)
        self._countdown_timer.setInterval(60_000)
        self._countdown_timer.timeout.connect(self._render_harmonogram)
        self._countdown_timer.start()

    # ── tichá kontrola stavu obhajob ──────────────────────────────────────
    def _maybe_check_states(self) -> None:
        """Během období státnic na pozadí zjistí STAG stav mých obhajob."""
        from datetime import date

        if self._state_checker is not None:
            return
        try:
            if not self.service.in_committee_period(date.today()):
                return
        except Exception:
            return
        from .stag_check import KomiseStateChecker

        checker = KomiseStateChecker(self.service, parent=self)
        checker.finished.connect(self._on_states_ready)
        self._state_checker = checker
        checker.start()

    def _on_states_ready(self, states) -> None:
        self._state_checker = None
        if isinstance(states, dict) and states != self._stag_states:
            self._stag_states = states
            self._on_selected()   # překresli detail s badge stavů obhajob

    # ── data / zvýraznění ────────────────────────────────────────────────
    def _user_name_fold(self) -> str:
        if self.profile_manager and self.profile_manager.active:
            return _fold(self.profile_manager.active.user_name or "")
        return ""

    def _slot_role(self, slot, roles: dict[str, str]) -> str:
        """„led" / „opp" / "" pro jeden slot rozpisu.

        Primárně dle **osobního čísla** (jednoznačné), fallback dle jména
        **bez titulů** (v rozpisu mívají studenti tituly, v práci ne).
        """
        from ..services.komise_stats import student_name_key

        pnum = (slot.personal_number or "").strip().upper()
        if pnum and pnum in roles:
            return roles[pnum]
        return roles.get(student_name_key(slot.student_name), "")

    def _is_my_committee(self, committee) -> bool:
        me = self._user_name_fold()
        if not me:
            return False
        # Porovnání bez titulů: stačí, že foldované jméno člena obsahuje
        # foldované jméno uživatele (tituly jsou okolo jména).
        return any(me in _fold(m.name) for m in committee.members)

    @staticmethod
    def _committee_matches_filter(committee, flt: str) -> bool:
        """Komise odpovídá filtru, je-li ``flt`` (foldovaný) v jméně **člena**
        nebo **studenta** (rozpis), případně v osobním čísle studenta."""
        if not flt:
            return True
        if any(flt in _fold(m.name) for m in committee.members):
            return True
        return any(
            flt in _fold(s.student_name) or flt in (s.personal_number or "").lower()
            for s in committee.slots
        )

    def _merged_states(self) -> dict:
        """Stavy obhajob pro vizualizaci: kompletní kontrola komisí
        (:attr:`_committee_states`) doplněná přesnými stavy mých prací
        (:attr:`_stag_states`). Kategorie „none" (bez výsledku) nepřepisuje."""
        merged = dict(self._stag_states)
        for k, v in self._committee_states.items():
            if v and v != "none":
                merged[k] = v
        return merged

    # ── strom ────────────────────────────────────────────────────────────
    def refresh(self) -> None:
        selected = self._selected_id()
        roles = self.service.komise_student_roles()
        flt = _fold(self.filter_edit.text().strip()) if hasattr(self, "filter_edit") else ""
        self.tree.blockSignals(True)
        self.tree.clear()
        committees = self.service.list_committees()
        by_year: dict[str, list] = {}
        for c in committees:
            by_year.setdefault(c.academic_year or "(bez roku)", []).append(c)

        def _bold(item: QTreeWidgetItem) -> None:
            f = item.font(0)
            f.setBold(True)
            item.setFont(0, f)

        for year in sorted(by_year, reverse=True):
            year_item = QTreeWidgetItem([f"📅 {year}", "", ""])
            _bold(year_item)
            year_item.setFirstColumnSpanned(True)
            year_item.setData(0, ROLE_KIND, "year")
            year_item.setData(0, ROLE_YEAR, year)
            # Skupina podle stupně (Bc/Mgr) a uvnitř podle oboru + barvy.
            by_level: dict[str, list] = {}
            for c in by_year[year]:
                by_level.setdefault(c.level or "", []).append(c)
            for level in sorted(by_level, key=lambda lv: _LEVEL_ORDER.get(lv, 9)):
                lvl_label = _LEVEL_LABEL.get(level, level or "(bez stupně)")
                level_item = QTreeWidgetItem([f"📚 {tr(lvl_label)}", "", ""])
                _bold(level_item)
                level_item.setFirstColumnSpanned(True)
                level_item.setData(0, ROLE_KIND, "level")
                level_item.setData(0, ROLE_YEAR, year)
                level_item.setData(0, ROLE_LEVEL, level)
                for c in sorted(by_level[level], key=lambda x: (x.obor, x.color)):
                    led = sum(1 for s in c.slots if self._slot_role(s, roles) == "led")
                    opp = sum(1 for s in c.slots if self._slot_role(s, roles) == "opp")
                    if self.chk_mine.isChecked() and not (led or opp):
                        continue
                    if flt and not self._committee_matches_filter(c, flt):
                        continue
                    star = "⭐ " if self._is_my_committee(c) else ""
                    obor = f" ({c.obor})" if c.obor else ""
                    label = f"{star}● {tr('Komise')} {c.color}{obor}"
                    leaf = QTreeWidgetItem([label, "", ", ".join(c.dates)])
                    leaf.setForeground(0, QBrush(QColor(committee_color_hex(c.color))))
                    leaf.setData(0, ROLE_COMMITTEE_ID, c.id)
                    leaf.setData(0, ROLE_KIND, "committee")
                    leaf.setData(0, ROLE_YEAR, year)
                    leaf.setData(1, ROLE_VO, (led, opp))
                    leaf.setToolTip(
                        1, tr("Vedení: {led} · Oponované: {opp}").format(led=led, opp=opp)
                    )
                    if led or opp:
                        f2 = leaf.font(0)
                        f2.setBold(True)
                        leaf.setFont(0, f2)
                    level_item.addChild(leaf)
                if level_item.childCount():   # prázdné skupiny (filtr) nepřidávej
                    year_item.addChild(level_item)
                    level_item.setExpanded(True)
            if year_item.childCount():
                self.tree.addTopLevelItem(year_item)
                year_item.setExpanded(True)
        self.tree.blockSignals(False)
        if selected:
            self._select_id(selected)
        elif self.tree.topLevelItemCount():
            self._select_default_year()
        self._on_selected()
        self._refresh_pdf_list()
        self._fit_panels()

    def _select_default_year(self) -> None:
        """Po startu vyber aktuální akademický rok (jinak nejnovější)."""
        cur = self.service.current_academic_year()
        for i in range(self.tree.topLevelItemCount()):
            it = self.tree.topLevelItem(i)
            if it.data(0, ROLE_YEAR) == cur:
                self.tree.setCurrentItem(it)
                return
        self.tree.setCurrentItem(self.tree.topLevelItem(0))

    def _refresh_pdf_list(self) -> None:
        """Naplní seznam PDF: rok → Složení / Rozpisy / Nezařazené → soubory."""
        self.pdf_tree.clear()
        inv = self.service.komise_pdf_inventory()
        groups = (("slozeni", "📋 " + tr("Složení komisí")),
                  ("rozpisy", "👥 " + tr("Rozpisy studentů")),
                  ("nezarazene", "⚠ " + tr("Nezařazené (starší import)")))
        for year in sorted(inv, reverse=True):
            data = inv[year]
            if not any(data.get(k) for k, _ in groups):
                continue
            yitem = QTreeWidgetItem([f"📅 {year}"])
            f = yitem.font(0)
            f.setBold(True)
            yitem.setFont(0, f)
            self.pdf_tree.addTopLevelItem(yitem)
            for key, label in groups:
                files = data.get(key) or []
                if not files:
                    continue
                kitem = QTreeWidgetItem([f"{label} ({len(files)})"])
                if key == "nezarazene":
                    kitem.setForeground(0, QBrush(QColor("#e65100")))
                yitem.addChild(kitem)
                for pdf in files:
                    leaf = QTreeWidgetItem([pdf.name])
                    leaf.setData(0, ROLE_PDF_PATH, str(pdf))
                    leaf.setToolTip(0, str(pdf))
                    kitem.addChild(leaf)
                kitem.setExpanded(True)
            yitem.setExpanded(True)

    def _selected_pdf_paths(self) -> list[str]:
        out = []
        for it in self.pdf_tree.selectedItems():
            p = it.data(0, ROLE_PDF_PATH)
            if p:
                out.append(p)
        return out

    def _handle_szz_url(self, url) -> bool:
        """Odkaz ``szz:OSCISLO?n=NAME`` → otevři souhrn SZZ studenta."""
        if url.scheme() != "szz":
            return False
        from PySide6.QtCore import QUrlQuery

        oc = url.path().strip()
        if oc:
            self.open_szz_student.emit(oc, QUrlQuery(url).queryItemValue("n"))
        return True

    def _szz_context_menu(self, view, pos) -> None:
        """Kontextové menu nad studentem (zachová standardní + přidá Souhrn SZZ)."""
        menu = view.createStandardContextMenu(pos)
        parsed = _parse_szz_href(view.anchorAt(pos))
        if parsed:
            menu.addSeparator()
            act = menu.addAction(tr("📋 Souhrn SZZ studenta…"))
            act.triggered.connect(
                lambda _c=False, oc=parsed[0], jm=parsed[1]:
                self.open_szz_student.emit(oc, jm))
        menu.exec(view.viewport().mapToGlobal(pos))

    def _open_detail_link(self, url) -> None:
        """Klik na odkaz v detailu: SZZ souhrn / PDF systémově / web v prohlížeči."""
        from ._os_actions import open_path

        if self._handle_szz_url(url):
            return
        if url.isLocalFile() or url.scheme() == "file":
            p = Path(url.toLocalFile())
            if p.exists():
                open_path(p)
            else:
                QMessageBox.warning(self, tr("Otevřít"),
                                    tr("Soubor neexistuje:") + f"\n{p}")
        else:
            from PySide6.QtGui import QDesktopServices
            QDesktopServices.openUrl(url)

    def _open_selected_pdfs(self) -> None:
        from ._os_actions import open_path

        paths = self._selected_pdf_paths()
        missing = []
        for p in paths:
            if Path(p).exists():
                open_path(Path(p))
            else:
                missing.append(p)
        if missing:
            QMessageBox.warning(
                self, tr("Otevřít"),
                tr("Některé soubory neexistují:") + "\n" + "\n".join(missing),
            )

    def _on_pdf_context_menu(self, pos) -> None:
        from PySide6.QtGui import QAction
        from PySide6.QtWidgets import QMenu

        paths = self._selected_pdf_paths()
        # Pravý klik mimo výběr → vezmi položku pod kurzorem.
        if not paths:
            item = self.pdf_tree.itemAt(pos)
            if item is not None and item.data(0, ROLE_PDF_PATH):
                item.setSelected(True)
                paths = [item.data(0, ROLE_PDF_PATH)]
        if not paths:
            return
        menu = QMenu(self.pdf_tree)
        n = len(paths)
        act_open = QAction(tr("📂 Otevřít") + (f" ({n})" if n > 1 else ""),
                           self.pdf_tree)
        act_open.triggered.connect(lambda _c=False: self._open_selected_pdfs())
        menu.addAction(act_open)
        # Mazat lze jen lokální PDF (ne dodaná v gitu).
        deletable = [p for p in paths if self._is_local_pdf(p)]
        if deletable:
            menu.addSeparator()
            act_del = QAction(
                tr("🗑 Smazat soubor z disku")
                + (f" ({len(deletable)})" if len(deletable) > 1 else ""),
                self.pdf_tree,
            )
            act_del.triggered.connect(lambda _c=False: self._delete_pdfs(deletable))
            menu.addAction(act_del)
        menu.exec(self.pdf_tree.viewport().mapToGlobal(pos))

    def _is_local_pdf(self, path: str) -> bool:
        """True, když PDF leží ve složce profilu komise/ (lze ho mazat)."""
        from ..config import komise_dir

        try:
            Path(path).resolve().relative_to(komise_dir().resolve())
            return True
        except (ValueError, OSError):
            return False

    def _delete_pdfs(self, paths: list[str]) -> None:
        n = len(paths)
        resp = QMessageBox.question(
            self, tr("Smazat soubor"),
            tr("Smazat {n} PDF souborů z disku? Tuto akci nelze vrátit.")
            .format(n=n) if n > 1 else
            tr("Smazat soubor {name} z disku? Tuto akci nelze vrátit.")
            .format(name=Path(paths[0]).name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if resp != QMessageBox.StandardButton.Yes:
            return
        for p in paths:
            self.service.komise_delete_pdf(p)
        self._refresh_pdf_list()

    def _iter_leaves(self):
        """Projde všechny komise-listy (rok → stupeň → komise)."""
        for i in range(self.tree.topLevelItemCount()):
            year_item = self.tree.topLevelItem(i)
            for j in range(year_item.childCount()):
                level_item = year_item.child(j)
                for k in range(level_item.childCount()):
                    yield level_item.child(k)

    def _selected_id(self) -> str | None:
        items = self.tree.selectedItems()
        return items[0].data(0, ROLE_COMMITTEE_ID) if items else None

    def _select_id(self, committee_id: str) -> None:
        for leaf in self._iter_leaves():
            if leaf.data(0, ROLE_COMMITTEE_ID) == committee_id:
                self.tree.setCurrentItem(leaf)
                return

    @staticmethod
    def _tree_width(tree: QTreeWidget) -> int:
        """Obsahová šířka stromu — JEN ``sizeHintForColumn`` (stabilní, nezávislé
        na aktuální šířce sloupců; ``columnWidth`` by tvořil zpětnou vazbu a panel
        by se s každým fitem rozšiřoval)."""
        cols = sum(tree.sizeHintForColumn(c) for c in range(tree.columnCount()))
        return cols + tree.indentation() * 3 + 36

    def _fit_panels(self) -> None:
        """Šířky panelů dle obsahu; prostřední bere zbytek (přes splitter).

        Levý = šířka **stromu komisí** (ne PDF seznamu — ten může být širší
        kvůli dlouhým názvům a eliduje se), pravý = obsah harmonogramu. Na
        velkém okně součet vyjde přesně = šířka okna → splitter nic neškáluje
        (= dnešní vzhled). Na úzkém okně setSizes Qt poměrně zmenší (respektuje
        minima panelů) → panely se ořežou, **nepřekrývají**. Po ručním
        přetažení uživatelem (``_cols_user_adjusted``) už šířky nepřepisujeme.
        """
        if self._cols_user_adjusted:
            return
        self.tree.expandAll()
        total = self.width() or 1400
        lw = max(220, self._tree_width(self.tree))
        if getattr(self, "_harmonogram_has_rows", False):
            doc = self.harmonogram_view.document()
            doc.setTextWidth(-1)
            rw = max(240, int(doc.idealWidth()) + 32)
        else:
            rw = 300   # prázdný harmonogram nemá rozšiřovat pravý panel
        # Pravý panel musí pojmout i tlačítko „Přidat do kalendáře".
        rw = max(rw, self.btn_add_calendar.sizeHint().width() + 24)
        mid_w = max(360, total - lw - rw)
        self.cols_splitter.setSizes([lw, mid_w, rw])

    def _on_cols_splitter_moved(self, *_args) -> None:
        """Uživatel přetáhl rozhraní panelů → přestaň auto-dopočítávat šířky."""
        self._cols_user_adjusted = True

    def _fit_detail_height(self) -> None:
        """Horní detail (komise/přehled) na výšku fituje obsah.

        Bez zalamování (NoWrap) — výšku počítáme z **přirozené** výšky obsahu
        (řádky na jeden řádek), takže se detail při úzkém okně nenafoukne do
        výšky; když se obsah nevejde na šířku, přidá se **vodorovný posuvník**
        (a započítá se jeho výška). Zbývající výšku panelu dostane statistika;
        výška detailu je zastropovaná na ~65 % (delší detail má svislý posuvník).
        """
        doc = self.detail.document()
        doc.setTextWidth(-1)   # bez zalamování → přirozená (nezalomená) výška
        frame = 2 * self.detail.frameWidth()
        content = int(doc.size().height()) + frame + 6
        # Když je obsah širší než viewport, bude vodorovný posuvník → přidej
        # jeho výšku, ať neukrojí poslední řádek.
        if doc.idealWidth() > self.detail.viewport().width() + 1:
            content += self.detail.horizontalScrollBar().sizeHint().height()
        cap = max(160, int(self.height() * 0.65))
        self.detail.setFixedHeight(max(60, min(content, cap)))

    def showEvent(self, event) -> None:  # noqa: N802 (Qt API)
        super().showEvent(event)
        self._fit_panels()
        self._fit_detail_height()

    def resizeEvent(self, event) -> None:  # noqa: N802 (Qt API)
        super().resizeEvent(event)
        self._fit_panels()
        self._fit_detail_height()

    # ── detail (prostřední) + harmonogram (pravý) ─────────────────────────
    def _on_selected(self) -> None:
        items = self.tree.selectedItems()
        item = items[0] if items else (
            self.tree.topLevelItem(0) if self.tree.topLevelItemCount() else None
        )
        kind = item.data(0, ROLE_KIND) if item is not None else None
        if kind == "committee":
            c = self.service.get_committee(item.data(0, ROLE_COMMITTEE_ID))
            self.detail.setHtml(self._committee_html(c) if c else self._empty_html())
        elif kind in ("year", "level"):
            self.detail.setHtml(self._overview_html(
                item.data(0, ROLE_YEAR), item.data(0, ROLE_LEVEL)))
        else:
            self.detail.setHtml(self._empty_html())
        # Pravý panel je nezávislý: harmonogram pro ROK výběru (default aktuální).
        self._right_year = (
            item.data(0, ROLE_YEAR) if item is not None else None
        ) or self.service.current_academic_year()
        self._render_harmonogram()
        self._render_stats()
        self._fit_panels()
        self._fit_detail_height()

    @staticmethod
    def _empty_html() -> str:
        return (f"<p style='color:{_MUTED};padding:18px;'>"
                + tr("Vyber komisi, rok nebo stupeň vlevo, "
                     "nebo importuj PDF rozpisu studentů.") + "</p>")

    # ── pravý panel: Můj harmonogram (nezávislý, pro vybraný rok) ──────────
    @staticmethod
    def _fmt_countdown(seconds: float) -> str:
        mins = int(seconds // 60)
        if mins < 60:
            return tr("za {n} min").format(n=max(mins, 0))
        if mins < 24 * 60:
            return tr("za {h} h {m} min").format(h=mins // 60, m=mins % 60)
        return tr("za {n} dní").format(n=mins // (24 * 60))

    @staticmethod
    def _nearest_upcoming(entries: list[dict], now):
        best = best_dt = None
        for e in entries:
            dt = ThesisService._parse_slot_dt(e["date"], e["time"])
            if dt is not None and dt > now and (best_dt is None or dt < best_dt):
                best, best_dt = e, dt
        return best, best_dt

    def _render_harmonogram(self) -> None:
        from datetime import datetime

        year = getattr(self, "_right_year", None) or self.service.current_academic_year()
        entries = [e for e in self.service.my_defense_schedule()
                   if e["academic_year"] == year]
        self._harmonogram_has_rows = bool(entries)
        now = datetime.now()
        nearest, ndt = self._nearest_upcoming(entries, now)
        nkey = None
        ntext = ""
        if nearest is not None:
            nkey = (nearest["date"], nearest["time"],
                    nearest["personal_number"], nearest["student_name"])
            ntext = self._fmt_countdown((ndt - now).total_seconds())
        heading = tr("📅 Můj harmonogram obhajob") + f" — {year}"
        self.harmonogram_view.setHtml(_schedule_section_html(
            entries, heading, self._merged_states(), nearest=nkey, nearest_text=ntext))
        # Tlačítko do kalendáře jen když je co přidat (nadcházející ve `year`).
        has_upcoming = any(
            (dt := ThesisService._parse_slot_dt(e["date"], e["time"])) and dt > now
            for e in entries
        )
        self.btn_add_calendar.setEnabled(has_upcoming)

    # ── statistika obhajob (spodní sekce prostředního panelu) ─────────────
    def _committees_in_scope(self) -> tuple[list, str]:
        """Komise pro statistiku dle výběru ve stromu + popisek rozsahu.

        Komise → jen ta; rok/stupeň → komise toho roku; jinak (default) →
        všechny roky.
        """
        items = self.tree.selectedItems()
        item = items[0] if items else None
        kind = item.data(0, ROLE_KIND) if item is not None else None
        all_committees = self.service.list_committees()
        if kind == "committee":
            c = self.service.get_committee(item.data(0, ROLE_COMMITTEE_ID))
            if c is not None:
                label = f"komise {c.color} ({c.level or '?'} · {c.obor or '?'})"
                return [c], label
        if kind in ("year", "level"):
            year = item.data(0, ROLE_YEAR)
            return ([c for c in all_committees if c.academic_year == year],
                    f"rok {year}")
        return all_committees, "všechny roky"

    def rerender_stats(self) -> None:
        """Znovu vykreslí statistiku (např. po stažení SZZ dat v admin okně)."""
        self._render_stats()

    def _render_stats(self) -> None:
        from ..services.komise_stats import committee_defense_stats
        from ..services.szz_stats import szz_admin_stats

        committees, scope = self._committees_in_scope()
        stats = committee_defense_stats(committees, self._committee_states)
        self.lbl_stats.setText(f"📊 Statistika obhajob — {scope}")
        self.stats_committee.setHtml(_stats_committee_html(stats, scope))
        self.stats_members.setHtml(_stats_members_html(stats))
        self.stats_chart.set_data(stats.get("by_color", []))
        # Admin: průběh SZZ z lokální cache (hned po startu, bez připojení).
        szz_cache = self.service.load_szz_results()
        szz = szz_admin_stats(szz_cache, committees)
        szz_scope = scope
        if szz_cache and szz["totals"]["students"] == 0:
            # Výběr nic neobsahuje, ale cache má data → ukaž celou cache, ať je
            # průběh SZZ vidět hned (nezávisle na výběru/rozpisech).
            szz = szz_admin_stats(szz_cache, [])
            szz_scope = tr("vše (cache)")
        self.stats_szz.setHtml(_stats_szz_html(szz, szz_scope, len(szz_cache)))
        self.lbl_szz_status.setText(_szz_status_line(szz_cache))

    def _refresh_stats_now(self) -> None:
        """Ruční obnova statistiky ze STAG (všechny komise → plní cache)."""
        self._start_committee_stats_check(manual=True)

    def _maybe_check_committee_stats(self) -> None:
        """Na pozadí během období státnic doplní kategorie obhajob komisí."""
        from datetime import date

        try:
            if not self.service.in_committee_period(date.today()):
                return
        except Exception:
            return
        self._start_committee_stats_check(manual=False)

    def _start_committee_stats_check(self, *, manual: bool) -> None:
        from datetime import datetime

        from .stag_check import KomiseStatsChecker

        if self._stats_checker is not None:
            if manual:
                QMessageBox.information(
                    self, "Statistika obhajob",
                    "Aktualizace už běží — chvilku počkej.")
            return
        committees = self.service.list_committees()
        if not committees:
            return
        self.btn_refresh_stats.setEnabled(False)
        self.lbl_stats_progress.setText("kontroluji…")
        # Ruční „Aktualizovat" vynutí kontrolu VŠECH zbývajících (force) bez
        # ohledu na čas obhajoby; tichá kontrola na pozadí drží časové okno.
        checker = KomiseStatsChecker(
            self.service, committees, datetime.now(),
            dict(self._committee_states), parent=self, force=manual)
        checker.progress.connect(self._on_stats_progress)
        checker.finished.connect(self._on_committee_stats_ready)
        self._stats_checker = checker
        checker.start()

    def _on_stats_progress(self, done: int, total: int) -> None:
        if total <= 0:
            self.lbl_stats_progress.setText("nic ke kontrole")
        else:
            self.lbl_stats_progress.setText(f"kontroluji… {done}/{total}")

    def _on_committee_stats_ready(self, states) -> None:
        self._stats_checker = None
        self.btn_refresh_stats.setEnabled(True)
        self.lbl_stats_progress.setText("✓ hotovo")
        if isinstance(states, dict):
            self._committee_states = states
            self.service.save_komise_defense_states(states)   # ulož pro příští start
            # Překresli i detail/rozpis a harmonogram (badge stavů studentů).
            self._on_selected()

    def _on_add_to_calendar(self) -> None:
        """Dialog → vygeneruje .ics nadcházejících obhajob a předá kalendáři."""
        from datetime import datetime

        year = (getattr(self, "_right_year", None)
                or self.service.current_academic_year())
        now = datetime.now()
        dlg = AddToCalendarDialog(self.service, year, now, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        opts = dlg.options()
        events = self.service.calendar_events(
            year, include_led=opts["led"], include_opp=opts["opp"], now=now)
        if not events:
            QMessageBox.information(
                self, "Přidat do kalendáře",
                "Žádné nadcházející obhajoby k přidání "
                "(zkontroluj výběr vedené/oponované).")
            return
        for ev in events:
            ev["reminder_min"] = opts["reminder"]
        from ..services.ics_export import build_ics
        ics = build_ics(events, dtstamp=now)
        self._deliver_ics(ics, opts["provider"], year, len(events))

    def _deliver_ics(self, ics: str, provider: str, year: str, count: int) -> None:
        """Zapíše .ics a předá ho zvolenému kalendáři (best-effort)."""
        from ._os_actions import open_path, open_with_app, reveal_in_file_manager

        fname = f"obhajoby_{year.replace('/', '-')}.ics"
        if provider == "save":
            dest, _ = QFileDialog.getSaveFileName(
                self, "Uložit .ics", str(Path.home() / fname),
                "iCalendar (*.ics)")
            if not dest:
                return
            try:
                Path(dest).write_text(ics, encoding="utf-8")
            except OSError as exc:
                QMessageBox.warning(self, "Přidat do kalendáře",
                                    f"Soubor se nepodařilo uložit:\n{exc}")
                return
            reveal_in_file_manager(dest)
            QMessageBox.information(
                self, "Přidat do kalendáře",
                f"Uloženo {count} obhajob do:\n{dest}")
            return

        # Apple/Outlook/Google: zapiš do dočasné složky a předej.
        import tempfile

        path = Path(tempfile.gettempdir()) / fname
        try:
            path.write_text(ics, encoding="utf-8")
        except OSError as exc:
            QMessageBox.warning(self, "Přidat do kalendáře",
                                f"Soubor se nepodařilo vytvořit:\n{exc}")
            return

        if provider == "apple":
            open_with_app(path, "Calendar")
        elif provider == "outlook":
            open_with_app(path, "Microsoft Outlook")
        elif provider == "google":
            # Google nemá hromadné přidání přes odkaz → import souboru.
            home_dest = Path.home() / "Downloads"
            target = (home_dest if home_dest.is_dir() else Path.home()) / fname
            try:
                target.write_text(ics, encoding="utf-8")
                path = target
            except OSError:
                pass
            reveal_in_file_manager(path)
            open_path("https://calendar.google.com/calendar/u/0/r/settings/export")
            QMessageBox.information(
                self, "Google Kalendář — import",
                f"Soubor s {count} obhajobami byl uložen a zobrazen ve Finderu:\n"
                f"{path}\n\n"
                "V otevřeném Google Kalendáři zvol vlevo „Import a export → "
                "Import“, vyber tento .ics soubor a potvrď.")
            return
        else:
            open_path(path)

    def _overview_html(self, year: str, level: str | None) -> str:
        """Prostřední panel: přehled všech komisí roku (nebo stupně)."""
        from html import escape

        roles = self.service.komise_student_roles()
        committees = [
            c for c in self.service.list_committees()
            if (c.academic_year or "(bez roku)") == year
            and (level is None or c.level == level)
        ]
        title = f"📅 {escape(year)}"
        if level:
            title += " — " + escape(tr(_LEVEL_LABEL.get(level, level)))
        out = f"<h2 style='margin:4px 0 8px;'>{title}</h2>"
        # Rok bez kurátorovaného složení (jen z importu rozpisů) → upozornění.
        if committees and not any(c.from_seed for c in committees):
            out += (
                "<p style='background:#fff3e0;color:#e65100;padding:6px 10px;"
                "border-radius:6px;'>⚠ "
                + tr("Složení komisí pro tento rok zatím není v aplikaci - "
                     "bude doplněno aktualizací aplikace.")
                + "</p>"
            )
        by_level: dict[str, list] = {}
        for c in committees:
            by_level.setdefault(c.level or "", []).append(c)
        for lv in sorted(by_level, key=lambda x: _LEVEL_ORDER.get(x, 9)):
            if level is None:
                out += (f"<h3 style='color:#ffa726;margin:12px 0 4px;'>📚 "
                        f"{escape(tr(_LEVEL_LABEL.get(lv, lv or '(bez stupně)')))}</h3>")
            out += "<table cellspacing='0'>"
            for c in sorted(by_level[lv], key=lambda x: (x.obor, x.color)):
                led = sum(1 for s in c.slots if self._slot_role(s, roles) == "led")
                opp = sum(1 for s in c.slots if self._slot_role(s, roles) == "opp")
                dot = committee_color_hex(c.color)
                obor = f" ({escape(c.obor)})" if c.obor else ""
                star = " ⭐" if self._is_my_committee(c) else ""
                vo = ""
                if led:
                    vo += f"<span style='color:{_C_LED};'>🎓 {led}</span> "
                if opp:
                    vo += f"<span style='color:{_C_OPP};'>🧐 {opp}</span>"
                out += (
                    "<tr>"
                    f"<td style='padding:2px 14px 2px 0;white-space:nowrap;'>"
                    f"<span style='color:{dot};'>●</span> {tr('Komise')} "
                    f"{escape(c.color)}{obor}{star}</td>"
                    f"<td style='padding:2px 14px 2px 0;color:{_MUTED};'>"
                    f"{escape(', '.join(c.dates))}</td>"
                    f"<td style='padding:2px 0;'>{vo}</td></tr>"
                )
            out += "</table>"
        return out

    #: Pevná šířka/výška rámečku role (px) — všechny role stejně široké.
    _ROLE_BADGE_W = 116
    _ROLE_BADGE_H = 18

    def _role_badge_img(self, key: str) -> str:
        """``<img>`` se zaobleným barevným rámečkem role (cache dle klíče)."""
        cache = getattr(self, "_role_badge_cache", None)
        if cache is None:
            cache = self._role_badge_cache = {}
        if key in cache:
            return cache[key]
        import base64

        from PySide6.QtCore import QBuffer, QByteArray, QIODevice
        from PySide6.QtGui import QPainter, QPen, QPixmap

        bg, fg = _ROLE_COLORS.get(key, _ROLE_COLORS["člen"])
        label = _ROLE_LABEL.get(key, key)
        w, h, scale = self._ROLE_BADGE_W, self._ROLE_BADGE_H, 2
        pm = QPixmap(w * scale, h * scale)
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.scale(scale, scale)
        p.setPen(QPen(QColor(fg), 1))
        p.setBrush(QColor(bg))
        p.drawRoundedRect(QRectF(0.5, 0.5, w - 1, h - 1), 6, 6)
        p.setPen(QColor(fg))
        f = p.font()
        f.setBold(True)
        f.setPointSizeF(9)
        p.setFont(f)
        p.drawText(QRectF(0, 0, w, h), Qt.AlignmentFlag.AlignCenter, label)
        p.end()
        ba = QByteArray()
        buf = QBuffer(ba)
        buf.open(QIODevice.OpenModeFlag.WriteOnly)
        pm.save(buf, "PNG")
        b64 = base64.b64encode(bytes(ba)).decode("ascii")
        img = (f'<img src="data:image/png;base64,{b64}" '
               f'width="{w}" height="{h}">')
        cache[key] = img
        return img

    def _committee_html(self, c) -> str:
        from html import escape

        roles = self.service.komise_student_roles()
        me = self._user_name_fold()
        states = self._merged_states()
        hexcol = committee_color_hex(c.color)
        head = (
            f"<h2 style='margin:4px 0;'><span style='color:{hexcol};'>●</span> "
            f"{escape(c.display_name)}"
            + (" ⭐" if self._is_my_committee(c) else "") + "</h2>"
            f"<p style='color:{_MUTED};margin:2px 0 10px 0;'>{escape(c.academic_year)}"
            + (" &nbsp;·&nbsp; " + escape(", ".join(c.dates)) if c.dates else "")
            + "</p>"
        )
        # Upozornění pro rok, jehož složení komisí ještě není v aplikaci
        # (komise vznikla jen z importovaného rozpisu, bez členů).
        if not c.members:
            head += (
                "<p style='background:#fff3e0;color:#e65100;padding:6px 10px;"
                "border-radius:6px;'>⚠ "
                + tr("Složení této komise zatím není v aplikaci - bude doplněno "
                     "aktualizací aplikace (nebo nahraj PDF složení komisí).")
                + "</p>"
            )
        # Složení — role jako zaoblené rámečky stejné šířky (PNG, protože
        # border-radius v QTextBrowser HTML nefunguje); text na střed.
        rows = ""
        for m in c.members:
            mine = me and me in _fold(m.name)
            name = escape(m.name)
            if mine:
                name = f"<b>⭐ {name}</b>"
            badge = self._role_badge_img(_role_key(m.role))
            rows += (
                f"<tr><td style='padding:2px 12px 2px 0;'>{badge}</td>"
                f"<td style='padding:2px 0;'>{name}</td></tr>"
            )
        members_html = (
            f"<h3 style='color:#ffa726;margin:10px 0 4px 0;'>{tr('Složení komise')}</h3>"
            f"<table>{rows}</table>" if rows else ""
        )
        # Rozpis po dnech
        sched_html = ""
        if c.slots:
            sched_html = (
                f"<h3 style='color:#ffa726;margin:14px 0 4px 0;'>"
                f"{tr('Rozpis studentů')}</h3>"
            )
            by_date: dict[str, list] = {}
            for s in c.slots:
                by_date.setdefault(s.date or "—", []).append(s)
            for date in sorted(by_date, key=_date_key):
                sched_html += (
                    f"<p style='margin:8px 0 2px 0;'><b>{escape(date)}</b></p>"
                    "<table>"
                )
                for s in sorted(by_date[date], key=lambda x: x.time):
                    role = self._slot_role(s, roles)
                    badge = ""
                    style = ""
                    if role == "led":
                        badge = " 🎓"
                        style = "background:#c8e6c9;color:#1b5e20;"
                    elif role == "opp":
                        badge = " 🧐"
                        style = "background:#e1bee7;color:#4a148c;"
                    state = _defense_state_badge(
                        states, s.personal_number, s.student_name)
                    sched_html += (
                        f"<tr><td style='padding:1px 12px 1px 0;color:{_MUTED};'>"
                        f"{escape(s.time)}</td>"
                        f"<td style='padding:1px 12px 1px 0;color:{_MUTED};'>"
                        f"{escape(s.personal_number)}</td>"
                        f"<td style='padding:1px 4px;{style}'>"
                        f"{_szz_student_anchor(s.personal_number, s.student_name, escape(s.student_name))}{badge}</td>"
                        f"<td style='padding:1px 0 1px 8px;'>{state}</td></tr>"
                    )
                sched_html += "</table>"
        # Zdrojová PDF této komise: složení (dodané v gitu, dle stupně+oboru)
        # + rozpis(y), ze kterých se sloty načetly. Jen existující, s proklikem.
        files_html = ""
        srcs = self._committee_source_pdfs(c)
        if srcs:
            links = " · ".join(
                f"<a href='file://{p}'>{escape(p.name)}</a>" for p in srcs
            )
            files_html = (
                f"<p style='color:{_MUTED};font-size:11px;margin-top:14px;'>"
                f"{tr('Zdrojová PDF:')} {links}</p>"
            )
        return head + members_html + sched_html + files_html

    def _committee_source_pdfs(self, c) -> list:
        """PDF patřící KE konkrétní komisi: složení (dodané v gitu dle
        stupně+oboru) + rozpisy z ``source_files``. Deduplikované, existující."""
        out = []
        inv = self.service.komise_pdf_inventory().get(c.academic_year, {})
        for p in inv.get("slozeni", []):
            if c.level and c.obor and c.level in p.name and c.obor in p.name:
                out.append(p)
        for rp in c.source_files:
            ap = self.service.komise_pdf_path(rp)
            if ap.exists():
                out.append(ap)
        seen, uniq = set(), []
        for p in out:
            if str(p) not in seen:
                seen.add(str(p))
                uniq.append(p)
        return uniq

    # ── akce ─────────────────────────────────────────────────────────────
    def _show_my_schedule(self) -> None:
        """Otevře dialog s osobním harmonogramem obhajob (vedené + oponované)."""
        dlg = MyScheduleDialog(self.service.my_defense_schedule(), self,
                               states=self._merged_states())
        dlg.exec()

    def _reset_committees(self) -> None:
        """Smaže všechny komise a načte čistý seed z JSONu (úklid starých dat)."""
        resp = QMessageBox.question(
            self, tr("Načíst komise znovu"),
            tr("Smaže VŠECHNY komise a načte čisté složení z aplikace.\n\n"
               "Použij na úklid starších naimportovaných komisí, které nesedí "
               "(chybí obor, duplicity, zmíchané barvy).\n\n"
               "⚠ Rozpisy studentů z dříve nahraných PDF zmizí — nahraj je "
               "potom znovu přes Import PDF rozpisu studentů (napojí se už na "
               "správné komise).\n\nPokračovat?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if resp != QMessageBox.StandardButton.Yes:
            return
        stats = self.service.reset_committees_from_seed()
        self.refresh()
        self.changed.emit()
        QMessageBox.information(
            self, tr("Hotovo"),
            tr("Načteno {n} komisí z aplikace. Teď nahraj PDF rozpisů studentů.")
            .format(n=stats.get("created", 0)),
        )

    def _import_pdfs(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self, tr("Vyber PDF rozpisu studentů (nebo složení komisí)"), "",
            "PDF (*.pdf)"
        )
        if not paths:
            return
        from ..services.komise_parser import parse_pdf

        committees = []
        schedules = []
        errors = []
        parsed: list[tuple[Path, object]] = []   # (cesta, ParsedPdf)
        for p in paths:
            try:
                r = parse_pdf(Path(p))
            except Exception as exc:  # vadné PDF přeskočíme
                errors.append(f"{Path(p).name}: {exc}")
                continue
            if not r.committees and not r.schedules:
                errors.append(
                    f"{Path(p).name}: " + tr("nerozpoznán formát (složení/rozpis)")
                )
                continue
            committees.extend(r.committees)
            schedules.extend(r.schedules)
            parsed.append((Path(p), r))

        if not committees and not schedules:
            QMessageBox.warning(
                self, tr("Import rozpisu studentů"),
                tr("Z vybraných PDF se nepodařilo nic načíst.")
                + ("\n\n" + "\n".join(errors) if errors else ""),
            )
            return

        dlg = KomiseImportPreviewDialog(committees, schedules, errors, self)
        if not dlg.exec():
            return
        sel_c = set(map(id, dlg.selected()[0]))
        sel_s = set(map(id, dlg.selected()[1]))

        # Import a uložení PER SOUBOR — zdrojové PDF se tak přilepí JEN ke
        # komisím, které daný soubor opravdu obsahuje (ne ke všem z dávky).
        stats = {"created": 0, "updated": 0, "slots": 0}
        for path, r in parsed:
            fc = [c for c in r.committees if id(c) in sel_c]
            fs = [s for s in r.schedules if id(s) in sel_s]
            if not (fc or fs):
                continue
            fyear = next(
                (x.academic_year for x in [*fs, *fc] if x.academic_year), "",
            )
            if fs:
                name = self._pdf_name(fyear, fs, "rozpis-studentu")
                kind = "rozpisy"
            else:
                name = self._pdf_name(fyear, fc, "slozeni-komisi")
                kind = "slozeni"
            rel = self.service.komise_store_pdf(path, fyear, name=name, kind=kind)
            st = self.service.apply_komise_import(fc, fs, [rel])
            for k in stats:
                stats[k] += st[k]
        self.refresh()
        self.changed.emit()
        QMessageBox.information(
            self, tr("Import rozpisu studentů"),
            tr("Hotovo: {created} nových komisí, {updated} aktualizovaných, "
               "{slots} slotů rozpisu.").format(**stats)
            + ("\n\n" + "\n".join(errors) if errors else ""),
        )

    @staticmethod
    def _pdf_name(year: str, items, prefix: str) -> str:
        """Sestaví popisný název PDF: ``prefix_<stupně>_<obory>_<rok>.pdf``."""
        levels = sorted({getattr(x, "level", "") for x in items if getattr(x, "level", "")})
        obory = sorted({getattr(x, "obor", "") for x in items if getattr(x, "obor", "")})
        tag = "-".join(levels)
        if obory:
            tag = (tag + "_" if tag else "") + "-".join(obory)
        y = (year or "").replace("/", "-")
        parts = [prefix] + ([tag] if tag else []) + ([y] if y else [])
        return "_".join(parts) + ".pdf"

    def _on_context_menu(self, pos) -> None:
        from PySide6.QtGui import QAction
        from PySide6.QtWidgets import QMenu

        item = self.tree.itemAt(pos)
        if item is None or not item.data(0, ROLE_COMMITTEE_ID):
            return
        cid = item.data(0, ROLE_COMMITTEE_ID)
        menu = QMenu(self.tree)
        act_del = QAction(tr("🗑 Smazat komisi"), self.tree)
        act_del.triggered.connect(lambda _c=False: self._delete(cid))
        menu.addAction(act_del)
        menu.exec(self.tree.viewport().mapToGlobal(pos))

    def _delete(self, committee_id: str) -> None:
        c = self.service.get_committee(committee_id)
        if c is None:
            return
        resp = QMessageBox.question(
            self, tr("Smazat komisi"),
            tr("Smazat komisi {name} ({year})? Zdrojová PDF na disku "
               "zůstanou.").format(name=c.display_name, year=c.academic_year),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if resp == QMessageBox.StandardButton.Yes:
            self.service.delete_committee(committee_id)
            self.refresh()
            self.changed.emit()


#: Barvy kategorií statistiky (čitelné v obou tématech).
_CAT_COLORS = {
    "defended": "#43a047",     # obhájeno (zelená)
    "failed": "#e53935",       # neobhájeno (červená)
    "unfinished": "#fb8c00",   # nedokončeno (oranžová)
    "none": _MUTED,            # bez obhajoby (šedá)
}


def _cat_head_cells() -> str:
    """Hlavičkové buňky 4 kategorií + Celkem (sdílené oběma tabulkami)."""
    from html import escape

    from ..services.komise_stats import CATEGORIES, CATEGORY_LABELS

    cells = ""
    for cat in CATEGORIES:
        cells += (f"<th style='padding:2px 8px 2px 0;text-align:right;"
                  f"color:{_CAT_COLORS[cat]};'>"
                  f"{escape(tr(CATEGORY_LABELS[cat]))}</th>")
    cells += (f"<th style='padding:2px 0;text-align:right;color:{_MUTED};'>"
              f"{escape(tr('Celkem'))}</th>")
    return cells


def _stats_committee_html(stats: dict, scope: str) -> str:
    """Tabulka statistiky podle barvy komise — počty **a procenta**."""
    from html import escape

    from ..services.komise_stats import CATEGORIES

    def _pct_cell(v: int, total: int, cat: str, *, top: str = "") -> str:
        color = _CAT_COLORS.get(cat, _MUTED)
        weight = "bold" if v else "normal"
        pct = f"{round(v / total * 100)} %" if total else "-"
        return (f"<td style='padding:2px 8px 2px 0;text-align:right;{top}'>"
                f"<span style='color:{color};font-weight:{weight};'>{v}</span>"
                f"<br><span style='color:{_MUTED};font-size:10px;'>{pct}</span></td>")

    by_color = stats.get("by_color", [])
    totals = stats.get("totals", {})

    out = ("<h3 style='margin:2px 0 4px;'>🎨 "
           + escape(tr("Podle komise (barva)")) + "</h3>")
    if not by_color:
        return out + (f"<p style='color:{_MUTED};'>"
                      + escape(tr("Žádné komise v tomto rozsahu.")) + "</p>")
    out += "<table style='border-collapse:collapse;'><tr>"
    out += (f"<th style='padding:2px 12px 2px 0;text-align:left;color:{_MUTED};'>"
            f"{escape(tr('Komise'))}</th>") + _cat_head_cells() + "</tr>"
    for rowd in by_color:
        dot = committee_color_hex(rowd["color"])
        meta = " · ".join(x for x in (rowd.get("level"), rowd.get("obor")) if x)
        label = escape(rowd["color"] or "?")
        if meta:
            label += f" <span style='color:{_MUTED};'>({escape(meta)})</span>"
        total = rowd.get("total", 0)
        out += (f"<tr><td style='padding:2px 12px 2px 0;white-space:nowrap;"
                f"vertical-align:top;'>"
                f"<span style='color:{dot};'>●</span> {label}</td>")
        for cat in CATEGORIES:
            out += _pct_cell(rowd.get(cat, 0), total, cat, top="vertical-align:top;")
        out += (f"<td style='padding:2px 0;text-align:right;vertical-align:top;'>"
                f"{total}</td></tr>")
    # Souhrnný řádek se Σ a procenty z celku.
    grand = sum(totals.get(cat, 0) for cat in CATEGORIES)
    border = f"border-top:1px solid {_MUTED};"
    out += (f"<tr><td style='padding:4px 12px 2px 0;{border}color:{_MUTED};'>"
            f"Σ {escape(tr('celkem'))}</td>")
    for cat in CATEGORIES:
        out += _pct_cell(totals.get(cat, 0), grand, cat, top=border)
    out += (f"<td style='padding:4px 0 2px;text-align:right;{border}"
            f"font-weight:bold;'>{grand}</td></tr></table>")
    return out


def _stats_members_html(stats: dict) -> str:
    """Tabulka statistiky podle členů komise (řazeno dle příjmení)."""
    from html import escape

    from ..services.komise_stats import CATEGORIES

    def _num(v: int, cat: str) -> str:
        color = _CAT_COLORS.get(cat, _MUTED)
        weight = "bold" if v else "normal"
        return (f"<td style='padding:2px 8px 2px 0;text-align:right;'>"
                f"<span style='color:{color};font-weight:{weight};'>{v}</span></td>")

    by_member = stats.get("by_member", [])
    out = ("<h3 style='margin:2px 0 4px;'>👤 "
           + escape(tr("Podle členů komise")) + "</h3>")
    if not by_member:
        return out + (f"<p style='color:{_MUTED};'>"
                      + escape(tr("Komise nemají vyplněné členy.")) + "</p>")
    out += "<table style='border-collapse:collapse;'><tr>"
    out += (f"<th style='padding:2px 12px 2px 0;text-align:left;color:{_MUTED};'>"
            f"{escape(tr('Člen'))}</th>") + _cat_head_cells() + "</tr>"
    for m in by_member:
        out += (f"<tr><td style='padding:2px 12px 2px 0;white-space:nowrap;'>"
                f"{escape(m['name'])}</td>")
        for cat in CATEGORIES:
            out += _num(m.get(cat, 0), cat)
        out += (f"<td style='padding:2px 0;text-align:right;'>"
                f"{m.get('total', 0)}</td></tr>")
    out += "</table>"
    return out


_GRADE_COLORS = {"A": "#2e7d32", "B": "#7cb342", "C": "#f9a825",
                 "D": "#ef6c00", "E": "#e64a19", "F": "#c62828"}


def _szz_dist_inline(dist: dict) -> str:
    """Kompaktní barevné rozložení známek: A6 B5 C3 … (0 = šedě)."""
    from ..services.szz_stats import GRADES

    parts = []
    for g in GRADES:
        c = dist.get(g, 0)
        col = _GRADE_COLORS[g] if c else _MUTED
        parts.append(f"<span style='color:{col};'>{g}{c}</span>")
    return "&nbsp; ".join(parts)


def _fail_labels(items: list) -> list:
    """Z fails-položek vrátí jména (nebo os. číslo) studentů, dedup dle os. čísla."""
    seen: set = set()
    out: list = []
    for f in items or []:
        oc = (f.get("os") or "").strip().upper()
        if oc and oc in seen:
            continue
        seen.add(oc)
        out.append((f.get("jmeno") or "").strip() or oc or "?")
    return out


def _szz_dist_bar(dist: dict, title: str, fail_labels: list | None = None) -> str:
    """Vodorovný proužek rozložení A-F (segmenty šířky ∝ počtu).

    Do tooltipu F segmentu se vepíší jména studentů, kteří v dané dimenzi
    neuspěli (``fail_labels``) — kdyby je klient nezobrazil, je tu i seznam níže.
    """
    from html import escape

    from ..services.szz_stats import GRADES

    total = sum(dist.values())
    if not total:
        return ""
    segs = ""
    for g in GRADES:
        c = dist.get(g, 0)
        if not c:
            continue
        w = max(2, round(c / total * 240))
        tip = f"{g}: {c}"
        if g == "F" and fail_labels:
            tip += " — " + ", ".join(fail_labels[:15])
            if len(fail_labels) > 15:
                tip += f", +{len(fail_labels) - 15}"
        segs += (f"<td width='{w}' bgcolor='{_GRADE_COLORS[g]}' "
                 f"title='{escape(tip)}'>&nbsp;</td>")
    return (f"<p style='margin:6px 0 2px;color:{_MUTED};'>{escape(title)} "
            f"<span style='color:{_MUTED};'>(n={total})</span></p>"
            f"<table cellspacing='0' cellpadding='0'><tr>{segs}</tr></table>")


# Čitelnější odstíny na tmavém pozadí (os. číslo / sekundární text v tabulce).
_FAIL_OS = "#bdc1c6"


def _szz_name_cell(f: dict) -> str:
    """Buňka se jménem studenta jako klikací odkaz (fallback na os. číslo)."""
    from html import escape

    oc = (f.get("os") or "").strip()
    name = (f.get("jmeno") or "").strip()
    return _szz_student_anchor(oc, name or oc, escape(name or oc or "?"))


def _szz_fails_html(fails: dict) -> str:
    """Tabulky neúspěchů (F/FX) po dimenzích: kdo a v čem neuspěl (klik → souhrn).

    Dimenze: předmětové zkoušky (dílčí, vč. zkoušejícího), celkový výsledek
    z předmětů, neobhájili a celkově „Neprospěl". Vše dle os. čísla; jméno
    z rozpisu komise. Zarovnáno do tabulek a čitelné i na tmavém pozadí.
    """
    from html import escape

    fails = fails or {}
    keys = ("subjects", "predmety", "defense", "overall")
    if not sum(len(fails.get(k, [])) for k in keys):
        return ""

    cn = "padding:2px 14px 2px 0;white-space:nowrap;"           # jméno
    co = f"padding:2px 14px 2px 0;color:{_FAIL_OS};white-space:nowrap;"  # os
    cm = f"padding:2px 0;color:{_MUTED};"                        # doplněk

    def _hdr(label: str, n: int) -> str:
        return (f"<p style='margin:10px 0 2px;'><b>{escape(label)}</b> "
                f"<span style='color:{_MUTED};'>({n})</span></p>")

    def _table(rows: str, *headers: str) -> str:
        th = "".join(
            f"<th style='padding:2px 14px 3px 0;text-align:left;"
            f"color:{_MUTED};font-weight:normal;'>{escape(h)}</th>"
            for h in headers)
        return ("<table style='border-collapse:collapse;margin:1px 0 4px;'>"
                f"<tr>{th}</tr>{rows}</table>")

    def _os_cell(f: dict) -> str:
        return f"<td style='{co}'>{escape((f.get('os') or '').strip())}</td>"

    out = ("<h4 style='margin:14px 0 2px;'>❌ "
           + escape(tr("Neúspěšní studenti (F)")) + "</h4>")
    out += (f"<p style='margin:2px 0 6px;color:{_MUTED};font-size:11px;'>"
            + escape(tr("Kdo a v čem neuspěl (F/FX), rozděleno podle dimenzí. "
                        "Klik na jméno otevře souhrn SZZ studenta.")) + "</p>")

    subs = fails.get("subjects", [])
    if subs:
        rows = "".join(
            f"<tr><td style='{cn}'>{_szz_name_cell(f)}</td>{_os_cell(f)}"
            f"<td style='{cn}'><b>{escape(f.get('predmet') or '?')}</b></td>"
            f"<td style='{cm}'>{escape((f.get('zkousejici') or '').strip())}</td></tr>"
            for f in subs)
        out += _hdr(tr("Předmětové zkoušky"), len(subs))
        out += _table(rows, tr("Student"), tr("Os. číslo"),
                      tr("Předmět"), tr("Zkoušející"))

    pred = fails.get("predmety", [])
    if pred:
        rows = "".join(
            f"<tr><td style='{cn}'>{_szz_name_cell(f)}</td>{_os_cell(f)}</tr>"
            for f in pred)
        out += _hdr(tr("Celkový výsledek z předmětů"), len(pred))
        out += _table(rows, tr("Student"), tr("Os. číslo"))

    dfn = fails.get("defense", [])
    if dfn:
        rows = "".join(
            f"<tr><td style='{cn}'>{_szz_name_cell(f)}</td>{_os_cell(f)}</tr>"
            for f in dfn)
        out += _hdr(tr("Neobhájili (obhajoba práce)"), len(dfn))
        out += _table(rows, tr("Student"), tr("Os. číslo"))

    ov = fails.get("overall", [])
    if ov:
        rows = "".join(
            f"<tr><td style='{cn}'>{_szz_name_cell(f)}</td>{_os_cell(f)}</tr>"
            for f in ov)
        out += _hdr(tr("Celkově „Neprospěl"), len(ov))
        out += _table(rows, tr("Student"), tr("Os. číslo"))

    return out


def _szz_avg_cell(avg) -> str:
    return "-" if avg is None else f"{avg:.1f}".replace(".", ",")


def _heat_color(t: float) -> str:
    """``t`` ∈ [0,1] → barva heatmapy: 0 = zelená, 0,5 = amber, 1 = červená.

    Pro náročnost zkoušejícího: nejnižší průměr (nejhodnější) → zelená,
    nejvyšší → červená. Čitelné na tmavém pozadí.
    """
    t = max(0.0, min(1.0, t))
    # Dvě úsečky: zelená → amber (t ≤ 0,5), amber → červená (t > 0,5).
    if t <= 0.5:
        c0, c1, f = (67, 160, 71), (249, 168, 37), t / 0.5
    else:
        c0, c1, f = (249, 168, 37), (229, 57, 53), (t - 0.5) / 0.5
    r = round(c0[0] + (c1[0] - c0[0]) * f)
    g = round(c0[1] + (c1[1] - c0[1]) * f)
    b = round(c0[2] + (c1[2] - c0[2]) * f)
    return f"#{r:02x}{g:02x}{b:02x}"


def _szz_avg_heat(avg, lo, hi) -> str:
    """Ø buňka obarvená gradientem dle náročnosti (``lo``/``hi`` = min/max Ø).

    Bez známky (``avg is None``) zůstává neutrální „-"; když je jen jeden
    průměr (``hi == lo``), nedává smysl gradient → neutrální.
    """
    if avg is None:
        return f"<span style='color:{_MUTED};'>-</span>"
    t = (avg - lo) / (hi - lo) if (hi is not None and hi > lo) else 0.5
    return (f"<b style='color:{_heat_color(t)};'>"
            f"{_szz_avg_cell(avg)}</b>")


def _szz_status_line(cache: dict) -> str:
    """Indikace stavu SZZ cache: počet, hotových a naposledy staženo."""
    if not cache:
        return tr("📂 zatím nic staženo")
    stamps = [getattr(r, "fetched_at", "") for r in cache.values()
              if getattr(r, "fetched_at", "")]
    last = max(stamps).replace("T", " ")[:16] if stamps else "?"
    n_term = sum(1 for r in cache.values() if getattr(r, "terminal", False))
    return (f"📂 {len(cache)} {tr('záznamů')} ({n_term} {tr('hotových')})"
            f" · {tr('naposledy')} {last}")


def _stats_szz_html(szz: dict, scope: str, cache_count: int) -> str:
    """Záložka „Průběh SZZ" (admin) — per komise / zkoušející / předmět + graf."""
    from html import escape

    head = "<h3 style='margin:2px 0 4px;'>🏛 " + escape(tr("Průběh SZZ")) + "</h3>"
    if cache_count == 0:
        return head + (
            f"<p style='color:{_MUTED};'>"
            + escape(tr("Zatím žádná data. Stáhni průběh SZZ přes 👤 profil → "
                        "🏛 Státnice (admin) — vyžaduje roli Zapisovatel státnic.")) + "</p>")

    tot = szz.get("totals", {})
    n = tot.get("students", 0)
    if not n:
        return head + (f"<p style='color:{_MUTED};'>"
                       + escape(tr("V tomto rozsahu zatím žádná SZZ data "
                                   "(stažené záznamy jsou jiných komisí).")) + "</p>")
    pct = f"{round(tot.get('prospel', 0) / n * 100)} %" if n else "-"
    out = head + (
        f"<p style='margin:2px 0 8px;color:{_MUTED};'>{n} {escape(tr('studentů'))}"
        f" &nbsp;·&nbsp; <span style='color:#2e7d32;'>{escape(tr('Prospělo'))} "
        f"{tot.get('prospel', 0)} ({pct})</span> &nbsp;·&nbsp; "
        f"<span style='color:#c62828;'>{escape(tr('Neprospělo'))} "
        f"{tot.get('neprospel', 0)}</span> &nbsp;·&nbsp; "
        f"<span style='color:{_MUTED};'>{escape(tr('Bez známky'))} "
        f"{tot.get('bez_znamky', 0)}</span>"
        + (f" &nbsp;·&nbsp; <span style='color:#fb8c00;'>⏳ {escape(tr('Nedostupné'))} "
           f"{tot.get('nedostupne', 0)}</span>" if tot.get('nedostupne') else "")
        + f" &nbsp;·&nbsp; {escape(tr('Ø známka'))} "
        f"<b>{_szz_avg_cell(tot.get('avg'))}</b></p>")

    def _table(title_html, rows_html, head_label):
        h = (f"<th style='padding:2px 12px 2px 0;text-align:left;color:{_MUTED};'>"
             f"{head_label}</th>"
             f"<th style='padding:2px 10px 2px 0;text-align:right;color:{_MUTED};'>"
             f"{escape(tr('Počet'))}</th>"
             f"<th style='padding:2px 10px 2px 0;text-align:left;color:{_MUTED};'>"
             f"{escape(tr('Rozložení A-F'))}</th>"
             f"<th style='padding:2px 0;text-align:right;color:{_MUTED};'>Ø</th>")
        return (title_html + "<table style='border-collapse:collapse;'><tr>"
                + h + "</tr>" + rows_html + "</table>")

    # Per komise
    rows = ""
    for r in szz.get("by_komise", []):
        dot = committee_color_hex(r["komise"])
        res = (f"<span style='color:#2e7d32;'>{r['pass']}✓</span> "
               f"<span style='color:#c62828;'>{r['fail']}✗</span>")
        if r.get("none"):
            res += f" <span style='color:{_MUTED};'>{r['none']}?</span>"
        if r.get("nedostupne"):
            res += f" <span style='color:#fb8c00;'>{r['nedostupne']}⏳</span>"
        rows += (f"<tr><td style='padding:2px 12px 2px 0;white-space:nowrap;'>"
                 f"<span style='color:{dot};'>●</span> {escape(r['komise'])} "
                 f"<span style='color:{_MUTED};font-size:10px;'>{res}</span></td>"
                 f"<td style='padding:2px 10px 2px 0;text-align:right;'>{r['n']}</td>"
                 f"<td style='padding:2px 10px 2px 0;'>{_szz_dist_inline(r['dist'])}</td>"
                 f"<td style='padding:2px 0;text-align:right;'>{_szz_avg_cell(r['avg'])}</td></tr>")
    out += _table("<h4 style='margin:10px 0 2px;'>🎨 " + escape(tr("Per komise"))
                  + f" <span style='color:{_MUTED};font-weight:normal;font-size:11px;'>"
                  + escape(tr("— rozložení = celkový výsledek SZZ")) + "</span></h4>",
                  rows, escape(tr("Komise")))

    # Per zkoušející — Ø obarvené gradientem náročnosti (nejnižší Ø zeleně,
    # nejvyšší červeně; normalizováno přes zobrazené zkoušející).
    examiners = szz.get("by_examiner", [])
    _avgs = [r["avg"] for r in examiners if r["avg"] is not None]
    _lo, _hi = (min(_avgs), max(_avgs)) if _avgs else (None, None)
    rows = ""
    for r in examiners:
        rows += (f"<tr><td style='padding:2px 12px 2px 0;white-space:nowrap;'>"
                 f"{escape(r['jmeno'] or '?')}</td>"
                 f"<td style='padding:2px 10px 2px 0;text-align:right;'>{r['n']}</td>"
                 f"<td style='padding:2px 10px 2px 0;'>{_szz_dist_inline(r['dist'])}</td>"
                 f"<td style='padding:2px 0;text-align:right;'>"
                 f"{_szz_avg_heat(r['avg'], _lo, _hi)}</td></tr>")
    out += _table("<h4 style='margin:12px 0 2px;'>🧑‍🏫 "
                  + escape(tr("Per zkoušející (náročnost)"))
                  + f" <span style='color:{_MUTED};font-weight:normal;font-size:11px;'>"
                  + escape(tr("— předmětové zkoušky, Ø zeleně=nejhodnější … "
                              "červeně=nejpřísnější")) + "</span></h4>", rows,
                  escape(tr("Zkoušející")))

    # Per předmět
    rows = ""
    for r in szz.get("by_predmet", []):
        rows += (f"<tr><td style='padding:2px 12px 2px 0;white-space:nowrap;'>"
                 f"{escape(r['predmet'])}</td>"
                 f"<td style='padding:2px 10px 2px 0;text-align:right;'>{r['n']}</td>"
                 f"<td style='padding:2px 10px 2px 0;'>{_szz_dist_inline(r['dist'])}</td>"
                 f"<td style='padding:2px 0;text-align:right;'>{_szz_avg_cell(r['avg'])}</td></tr>")
    out += _table("<h4 style='margin:12px 0 2px;'>📚 " + escape(tr("Per předmět SZZ"))
                  + f" <span style='color:{_MUTED};font-weight:normal;font-size:11px;'>"
                  + escape(tr("— předmětové zkoušky")) + "</span></h4>",
                  rows, escape(tr("Předmět")))

    # Rozložení známek po dimenzích (zvlášť, ať je jasné co je co).
    dist = szz.get("dist", {})
    out += ("<h4 style='margin:14px 0 2px;'>📊 "
            + escape(tr("Rozložení známek po dimenzích")) + "</h4>")
    out += (f"<p style='margin:2px 0 4px;color:{_MUTED};font-size:11px;'>"
            + escape(tr("Různé dimenze se počítají zvlášť: dílčí zkoušky z "
                        "předmětů, jejich celkový výsledek, obhajoba a celkový "
                        "výsledek SZZ. Proto se počty F mezi sekcemi mohou lišit "
                        "(per komise = celkový výsledek SZZ; per zkoušející = "
                        "dílčí předmětové zkoušky; obhajoba je samostatná).")) + "</p>")
    fails = szz.get("fails", {})
    out += _szz_dist_bar(dist.get("subjects", {}), tr("Předmětové zkoušky (dílčí)"),
                         _fail_labels(fails.get("subjects", [])))
    out += _szz_dist_bar(dist.get("predmety", {}), tr("Celkový výsledek z předmětů"),
                         _fail_labels(fails.get("predmety", [])))
    out += _szz_dist_bar(dist.get("defense", {}), tr("Obhajoba práce"),
                         _fail_labels(fails.get("defense", [])))
    out += _szz_dist_bar(dist.get("overall", {}), tr("Celkový výsledek SZZ"),
                         _fail_labels(fails.get("overall", [])))

    # Neúspěšní studenti (F) — kdo a v čem neuspěl, po dimenzích.
    out += _szz_fails_html(fails)

    # Otázky (po předmětech, zkráceně)
    questions = szz.get("questions", {})
    if questions:
        out += "<h4 style='margin:14px 0 2px;'>❓ " + escape(tr("Otázky z průběhu")) + "</h4>"
        for pred in sorted(questions):
            qs = questions[pred]
            out += (f"<p style='margin:6px 0 2px;'><b>{escape(pred)}</b> "
                    f"<span style='color:{_MUTED};'>({len(qs)})</span></p>")
            for q in qs[:20]:
                txt = q if len(q) <= 200 else q[:200] + "…"
                out += (f"<p style='margin:0 0 0 10px;color:{_MUTED};'>• "
                        f"{escape(txt)}</p>")
    return out


def _nice_step(value: int, divisions: int = 4) -> int:
    """Hezký krok osy (1/2/5 * 10^n) tak, aby ~``divisions`` dílků pokrylo ``value``."""
    import math

    if value <= divisions:
        return 1
    raw = value / divisions
    exp = math.floor(math.log10(raw))
    base = 10 ** exp
    for m in (1, 2, 5, 10):
        if raw <= m * base:
            return int(m * base)
    return int(10 * base)


class _DefenseBarChart(QWidget):
    """Sloupcový graf obhajob: per komise (barva) 3 sloupce kategorií vedle sebe.

    Sloupce mají barvu komise (skupina), kategorii poznáš podle **ikony** pod
    sloupcem (✓ Obhájeno zeleně, ✗ Neobhájeno červeně, ○ Bez obhajoby šedě);
    nulová kategorie se kreslí jako malá patka s „0", takže nevzniká matoucí
    mezera. Sloupec je dál rozdělen na **segmenty po dnech rozpisu** s oddělovači;
    datum se vepíše do dostatečně vysokého segmentu a vždy je v tooltipu sloupce.
    """

    # Odstín barvy komise podle kategorie (jen jemný náznak; rozhoduje ikona).
    _ALPHAS = (255, 205, 120)  # defended (nejtmavší) → none (nejsvětlejší)
    # Sémantická barva ikony kategorie (pořadí = CATEGORIES).
    _ICON_COLORS = ("#2e7d32", "#c62828", "#9e9e9e")

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._groups: list[dict] = []
        self._hit_rects: list[tuple] = []   # (QRectF, group, cat_index) pro tooltip
        self.setMinimumHeight(260)
        self.setToolTip(
            "Sloupce: Obhájeno (✓) / Neobhájeno (✗) / Bez obhajoby (○). "
            "Barva sloupců = barva komise; segmenty = dny rozpisu. "
            "Najetím na sloupec se zobrazí rozpad po dnech s datem."
        )

    def set_data(self, by_color: list[dict]) -> None:
        from ..services.komise_stats import CATEGORIES

        groups: list[dict] = []
        for r in by_color or []:
            days = [
                {"date": d.get("date") or "",
                 "counts": [d.get(c, 0) for c in CATEGORIES]}
                for d in (r.get("by_day") or [])
            ]
            groups.append({
                "label": r.get("color") or "?",
                "sub": " · ".join(x for x in (r.get("level"), r.get("obor")) if x),
                "hex": committee_color_hex(r.get("color") or ""),
                "counts": [r.get(c, 0) for c in CATEGORIES],
                "days": days,
            })
        self._groups = groups
        self.update()

    @staticmethod
    def _short_day(date_str: str) -> str:
        """„17. 6. 2026" → „17.6." (pro vepsání do segmentu)."""
        import re

        m = re.search(r"(\d{1,2})\.\s*(\d{1,2})\.", date_str or "")
        return f"{int(m.group(1))}.{int(m.group(2))}." if m else ""

    @staticmethod
    def _contrast_on(hexcol: str) -> QColor:
        """Černá/bílá podle jasu barvy komise — čitelnost datumu v segmentu."""
        c = QColor(hexcol)
        lum = 0.299 * c.red() + 0.587 * c.green() + 0.114 * c.blue()
        return QColor("#1a1a1a") if lum > 150 else QColor("#ffffff")

    def _draw_icon(self, p: QPainter, cat_index: int, cx: float, cy: float,
                   r: float) -> None:
        """Ikona kategorie (✓ / ✗ / ○) jako tvar v sémantické barvě."""
        col = QColor(self._ICON_COLORS[cat_index])
        pen = QPen(col, 2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        if cat_index == 0:        # ✓ obhájeno
            path = [(cx - r, cy), (cx - r * 0.3, cy + r * 0.7), (cx + r, cy - r * 0.8)]
            p.drawPolyline([QPointF(*pt) for pt in path])
        elif cat_index == 1:      # ✗ neobhájeno
            p.drawLine(QPointF(cx - r, cy - r), QPointF(cx + r, cy + r))
            p.drawLine(QPointF(cx + r, cy - r), QPointF(cx - r, cy + r))
        else:                     # ○ bez obhajoby
            p.drawEllipse(QPointF(cx, cy), r * 0.85, r * 0.85)

    def _tooltip_at(self, pos) -> str:
        from ..services.komise_stats import CATEGORIES, CATEGORY_LABELS

        for rect, g, i in self._hit_rects:
            if rect.contains(pos.x(), pos.y()):
                cat = CATEGORIES[i]
                lines = [f"{g['label']}"
                         + (f" — {g['sub']}" if g["sub"] else ""),
                         f"{tr(CATEGORY_LABELS[cat])}: {g['counts'][i]}"]
                for d in g.get("days", []):
                    c = d["counts"][i]
                    if c:
                        lines.append(f"   {d['date'] or '—'}: {c}")
                return "\n".join(lines)
        return ""

    def event(self, e) -> bool:
        from PySide6.QtCore import QEvent
        from PySide6.QtWidgets import QToolTip

        if e.type() == QEvent.Type.ToolTip:
            text = self._tooltip_at(e.pos())
            if text:
                QToolTip.showText(e.globalPos(), text, self)
            else:
                QToolTip.hideText()
            return True
        return super().event(e)

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt API)
        from ..services.komise_stats import CATEGORIES, CATEGORY_LABELS

        self._hit_rects = []
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        text_col = self.palette().windowText().color()
        win_bg = self.palette().window().color()
        muted = QColor(_MUTED)
        grid = QColor(_MUTED)
        grid.setAlpha(55)
        w, h = self.width(), self.height()
        base_font = QFont(self.font())
        base_font.setPointSize(10)
        sub_font = QFont(self.font())
        sub_font.setPointSize(9)
        p.setFont(base_font)

        if not self._groups:
            p.setPen(muted)
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                       tr("Bez dat ke grafu"))
            p.end()
            return

        left, right, top, bottom = 42, 12, 44, 54
        plot_w = max(20, w - left - right)
        plot_h = max(20, h - top - bottom)
        base_y = top + plot_h
        maxv = max((max(g["counts"]) for g in self._groups), default=0) or 1
        step = _nice_step(maxv, 4)
        top_val = step * (maxv // step + (1 if maxv % step else 0))
        top_val = max(top_val, step)

        # Legenda nahoře: ikona kategorie + popisek.
        p.setFont(sub_font)
        lx = left
        for i, cat in enumerate(CATEGORIES):
            self._draw_icon(p, i, lx + 7, 15, 6)
            label = tr(CATEGORY_LABELS[cat])
            tw = p.fontMetrics().horizontalAdvance(label)
            p.setPen(text_col)
            p.drawText(lx + 18, 8, tw + 6, 16,
                       Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                       label)
            lx += 18 + tw + 18

        # Osa Y s mřížkou a popisky hodnot.
        p.setFont(sub_font)
        v = 0
        while v <= top_val:
            y = base_y - (v / top_val) * plot_h
            p.setPen(QPen(grid, 1))
            p.drawLine(left, int(y), left + plot_w, int(y))
            p.setPen(muted)
            p.drawText(0, int(y) - 8, left - 5, 16,
                       Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                       str(v))
            v += step
        # Osy X a Y.
        p.setPen(QPen(muted, 1))
        p.drawLine(left, top, left, base_y)
        p.drawLine(left, base_y, left + plot_w, base_y)

        n = len(self._groups)
        gap = 14
        gw = max(20, (plot_w - gap * (n - 1)) / n)
        bgap = 3
        n_cat = max(1, len(CATEGORIES))   # počet sloupců ve skupině (kategorie)
        bw = max(4, (gw - bgap * (n_cat - 1)) / n_cat)
        nub = 3                           # výška „patky" u nulové kategorie
        x = left + gap / 2 if n == 1 else left
        for g in self._groups:
            days = g.get("days") or []
            for i in range(n_cat):
                bx = x + i * (bw + bgap)
                cnt = g["counts"][i]
                bh = (cnt / top_val) * plot_h
                base_col = QColor(g["hex"])
                # Plocha sloupce pro tooltip (celá výška grafu nad osou).
                self._hit_rects.append(
                    (QRectF(bx, top, bw, plot_h), g, i))
                if cnt <= 0:
                    col = QColor(base_col)
                    col.setAlpha(self._ALPHAS[i])
                    p.fillRect(int(bx), int(base_y - nub), int(bw), nub, col)
                else:
                    seg = [d for d in days if d["counts"][i] > 0]
                    if not seg:           # bez denních dat → jeden segment
                        seg = [{"date": "", "counts": g["counts"]}]
                    y0 = base_y
                    for di, d in enumerate(seg):
                        sh = (d["counts"][i] / top_val) * plot_h
                        seg_top = y0 - sh
                        col = QColor(base_col)
                        col.setAlpha(self._ALPHAS[i])
                        p.fillRect(int(bx), int(seg_top), int(bw),
                                   round(sh), col)
                        if di < len(seg) - 1:   # oddělovač mezi dny
                            p.setPen(QPen(win_bg, 1))
                            p.drawLine(int(bx), int(seg_top),
                                       int(bx + bw), int(seg_top))
                        short = self._short_day(d["date"])
                        if short and sh >= 22 and bw >= 9:
                            p.save()
                            p.translate(bx + bw / 2, seg_top + sh / 2)
                            p.rotate(-90)
                            df = QFont(self.font())
                            df.setPointSize(7)
                            p.setFont(df)
                            p.setPen(self._contrast_on(g["hex"]))
                            p.drawText(QRectF(-sh / 2, -7, sh, 14),
                                       Qt.AlignmentFlag.AlignCenter, short)
                            p.restore()
                        y0 = seg_top
                # Počet nad sloupcem (i u nuly).
                top_of_bar = base_y - (bh if cnt > 0 else nub)
                p.setPen(text_col)
                p.setFont(sub_font)
                p.drawText(int(bx - 4), int(top_of_bar - 16), int(bw + 8), 14,
                           Qt.AlignmentFlag.AlignHCenter, str(cnt))
                # Ikona kategorie pod sloupcem.
                self._draw_icon(p, i, bx + bw / 2, base_y + 11, 5)
            # Popisek skupiny (barva komise) + podtitul (stupeň · obor).
            p.setPen(text_col)
            p.setFont(base_font)
            p.drawText(int(x), base_y + 22, int(gw), 16,
                       Qt.AlignmentFlag.AlignHCenter, g["label"])
            if g["sub"]:
                p.setFont(sub_font)
                p.setPen(muted)
                p.drawText(int(x), base_y + 40, int(gw), 14,
                           Qt.AlignmentFlag.AlignHCenter, g["sub"])
            x += gw + gap
        p.end()


def _date_key(d: str):
    import re

    m = re.search(r"(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})", d)
    return (m.group(3), int(m.group(2)), int(m.group(1))) if m else ("9999", 99, 99)


def _schedule_section_html(entries: list[dict], heading: str,
                           states: dict | None = None, *,
                           nearest: tuple | None = None,
                           nearest_text: str = "") -> str:
    """HTML sekce harmonogramu (nadpis + počty + sloty po dnech).

    Sdílí ji dialog *Můj harmonogram* i pravý panel záložky. Vstup ``entries``
    je výstup ``ThesisService.my_defense_schedule`` (chronologicky seřazený),
    případně předfiltrovaný na rok. ``states`` (z tiché STAG kontroly) přidá
    badge Obhájeno/Neobhájeno. ``nearest`` = klíč (date, time, pnum, name)
    nejbližšího nadcházejícího slotu — ten se zvýrazní a doplní se odpočet
    ``nearest_text`` („za X min").
    """
    from html import escape

    out = f"<h3 style='color:#ffa726;margin:14px 0 4px;'>{escape(heading)}</h3>"
    if not entries:
        return out + (
            f"<p style='color:{_MUTED};'>"
            + tr("Zatím žádné obhajoby tvých studentů. Nahraj rozpisy "
                 "studentů z PDF — vedené a oponované se sem doplní.")
            + "</p>"
        )
    led = sum(1 for e in entries if e["role"] == "led")
    opp = sum(1 for e in entries if e["role"] == "opp")
    out += (
        f"<p style='color:{_MUTED};margin:2px 0 8px;'>{len(entries)} {tr('obhajob')}"
        f" &nbsp;·&nbsp; <span style='color:{_C_LED};'>🎓 {tr('vedené')} {led}</span>"
        f" &nbsp; <span style='color:{_C_OPP};'>🧐 {tr('oponované')} {opp}</span></p>"
    )
    by_date: dict[str, list[dict]] = {}
    for e in entries:
        by_date.setdefault(e["date"] or "—", []).append(e)
    for date in sorted(by_date, key=_date_key):
        out += (f"<p style='margin:8px 0 2px;'><b>{escape(date)}</b></p>"
                "<table cellspacing='0'>")
        for e in by_date[date]:
            dot = committee_color_hex(e["color"])
            obor = f" ({escape(e['obor'])})" if e["obor"] else ""
            place = f"{tr('Komise')} {escape(e['color'])}{obor}"
            if e["role"] == "led":
                badge, style = "🎓", "background:#c8e6c9;color:#1b5e20;"
            else:
                badge, style = "🧐", "background:#e1bee7;color:#4a148c;"
            pnum = (f" <span style='color:{_MUTED};'>{escape(e['personal_number'])}</span>"
                    if e["personal_number"] else "")
            state = _defense_state_badge(states, e["personal_number"], e["student_name"])
            # Nejbližší nadcházející slot: zvýraznit jasným akcentem (čas + odpočet
            # oranžově, tučně) — BEZ světlého pozadí, aby zůstal čitelný na tmavém.
            is_near = nearest is not None and nearest == (
                e["date"], e["time"], e["personal_number"], e["student_name"])
            time_style = ("color:#ffa726;font-weight:bold;" if is_near
                          else f"color:{_MUTED};")
            cd = (f"<b style='color:#ffa726;'>⏳ {escape(nearest_text)}</b>"
                  if is_near and nearest_text else state)
            arrow = "▶ " if is_near else ""
            out += (
                "<tr>"
                f"<td style='padding:2px 12px 2px 0;{time_style}'>"
                f"{arrow}{escape(e['time'])}</td>"
                f"<td style='padding:2px 12px 2px 0;white-space:nowrap;'>"
                f"<span style='color:{dot};'>●</span> {escape(place)}</td>"
                f"<td style='padding:2px 4px;{style}'>{badge} "
                f"{_szz_student_anchor(e['personal_number'], e['student_name'], escape(e['student_name']))}{pnum}</td>"
                f"<td style='padding:2px 0 2px 8px;white-space:nowrap;'>{cd}</td></tr>"
            )
        out += "</table>"
    return out


class AddToCalendarDialog(QDialog):
    """Volby pro export nadcházejících obhajob do kalendáře (.ics).

    Uživatel zvolí vedené/oponované (default obojí), připomínku (default 15 min
    předem) a cílový kalendář (Apple / Outlook / Google / jen uložit soubor).
    Počet vybraných obhajob se přepočítává živě dle zaškrtnutí.
    """

    _REMINDERS = [
        ("bez připomínky", None),
        ("5 minut předem", 5),
        ("10 minut předem", 10),
        ("15 minut předem", 15),
        ("30 minut předem", 30),
        ("1 hodinu předem", 60),
    ]
    _PROVIDERS = [
        ("apple", "Apple Kalendář"),
        ("outlook", "Microsoft Outlook"),
        ("google", "Google Kalendář (import souboru)"),
        ("save", "Jen uložit soubor .ics"),
    ]

    def __init__(self, service: ThesisService, year: str, now, parent=None) -> None:
        super().__init__(parent)
        self._service = service
        self._year = year
        self._now = now
        self.setWindowTitle("📆 Přidat obhajoby do kalendáře")
        self.setMinimumWidth(380)
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(f"Nadcházející obhajoby — <b>{year}</b>"))

        self.cb_led = QCheckBox("🎓 Vedené")
        self.cb_opp = QCheckBox("🧐 Oponované")
        self.cb_led.setChecked(True)
        self.cb_opp.setChecked(True)
        self.cb_led.toggled.connect(self._update_count)
        self.cb_opp.toggled.connect(self._update_count)
        lay.addWidget(self.cb_led)
        lay.addWidget(self.cb_opp)

        self.lbl_count = QLabel()
        self.lbl_count.setStyleSheet("color:#9aa0a6;")
        lay.addWidget(self.lbl_count)

        row_r = QHBoxLayout()
        row_r.addWidget(QLabel("Připomínka:"))
        self.cmb_reminder = QComboBox()
        for label, _ in self._REMINDERS:
            self.cmb_reminder.addItem(label)
        self.cmb_reminder.setCurrentIndex(3)   # 15 minut předem
        row_r.addWidget(self.cmb_reminder, stretch=1)
        lay.addLayout(row_r)

        row_p = QHBoxLayout()
        row_p.addWidget(QLabel("Kalendář:"))
        self.cmb_provider = QComboBox()
        for _, label in self._PROVIDERS:
            self.cmb_provider.addItem(label)
        row_p.addWidget(self.cmb_provider, stretch=1)
        lay.addLayout(row_p)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Přidat")
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        lay.addWidget(self.buttons)
        self._update_count()

    def _count(self) -> int:
        return len(self._service.calendar_events(
            self._year, include_led=self.cb_led.isChecked(),
            include_opp=self.cb_opp.isChecked(), now=self._now))

    def _update_count(self) -> None:
        n = self._count()
        self.lbl_count.setText(f"Vybráno: {n} obhajob")
        ok = self.buttons.button(QDialogButtonBox.StandardButton.Ok)
        ok.setEnabled(n > 0)

    def options(self) -> dict:
        return {
            "led": self.cb_led.isChecked(),
            "opp": self.cb_opp.isChecked(),
            "reminder": self._REMINDERS[self.cmb_reminder.currentIndex()][1],
            "provider": self._PROVIDERS[self.cmb_provider.currentIndex()][0],
        }


class MyScheduleDialog(QDialog):
    """Osobní harmonogram obhajob — kdy a kde obhajují moji studenti."""

    def __init__(self, entries: list[dict], parent=None, *,
                 states: dict | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("📅 Můj harmonogram obhajob"))
        self.setMinimumSize(680, 560)
        lay = QVBoxLayout(self)
        view = QTextBrowser()
        view.setOpenExternalLinks(False)
        view.setHtml(_schedule_section_html(
            entries, tr("📅 Můj harmonogram obhajob"), states))
        lay.addWidget(view, stretch=1)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        lay.addWidget(buttons)


class KomiseImportPreviewDialog(QDialog):
    """Náhled importu: zaškrtni, které komise / rozpisy uložit."""

    def __init__(self, committees, schedules, errors, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Import komisí — náhled"))
        self.setMinimumSize(640, 480)
        self._committees = committees
        self._schedules = schedules

        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(tr("Zaškrtni, co uložit (merge dle roku + barvy):")))
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels([tr("Položka"), tr("Detail")])
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        lay.addWidget(self.tree, stretch=1)

        self._items: list[tuple[QTreeWidgetItem, str, object]] = []
        if committees:
            top = QTreeWidgetItem([tr("Složení komisí"), ""])
            self.tree.addTopLevelItem(top)
            for c in committees:
                label = f"● Komise {c.color} ({c.level or '?'}) {c.academic_year}"
                detail = f"{len(c.members)} členů · {c.program_label[:50]}"
                leaf = QTreeWidgetItem([label, detail])
                leaf.setFlags(leaf.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                leaf.setCheckState(0, Qt.CheckState.Checked)
                leaf.setForeground(0, QBrush(QColor(committee_color_hex(c.color))))
                top.addChild(leaf)
                self._items.append((leaf, "committee", c))
            top.setExpanded(True)
        if schedules:
            top2 = QTreeWidgetItem([tr("Rozpisy studentů"), ""])
            self.tree.addTopLevelItem(top2)
            for s in schedules:
                label = f"● Komise {s.color} ({s.level or '?'}) {s.academic_year}"
                detail = f"{len(s.slots)} studentů · {', '.join(s.dates)}"
                leaf = QTreeWidgetItem([label, detail])
                leaf.setFlags(leaf.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                leaf.setCheckState(0, Qt.CheckState.Checked)
                leaf.setForeground(0, QBrush(QColor(committee_color_hex(s.color))))
                top2.addChild(leaf)
                self._items.append((leaf, "schedule", s))
            top2.setExpanded(True)
        if errors:
            lay.addWidget(QLabel("⚠ " + " · ".join(errors)))

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        lay.addWidget(buttons)

    def selected(self) -> tuple[list, list]:
        committees = [obj for it, kind, obj in self._items
                      if kind == "committee" and it.checkState(0) == Qt.CheckState.Checked]
        schedules = [obj for it, kind, obj in self._items
                     if kind == "schedule" and it.checkState(0) == Qt.CheckState.Checked]
        return committees, schedules
