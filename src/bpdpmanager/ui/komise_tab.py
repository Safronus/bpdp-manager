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

from PySide6.QtCore import QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStyle,
    QStyledItemDelegate,
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

#: STAG stav obhajoby → (emoji, popisek, barva) pro badge v rozpisu.
_STATE_BADGE = {
    "defended": ("✅", "Obhájeno", "#43a047"),
    "failed": ("❌", "Neobhájeno", "#ef5350"),
    "cancelled": ("⚠", "Nedokončeno", "#ffa726"),
}


def _defense_state_badge(states: dict | None, pnum: str, name: str) -> str:
    """HTML badge stavu obhajoby studenta (✅/❌/⚠) z tiché STAG kontroly.

    Páruje přes osobní číslo (Axxxxx), záložně přes foldované jméno.
    """
    if not states:
        return ""
    val = states.get((pnum or "").strip().upper()) or states.get(_fold(name))
    info = _STATE_BADGE.get(val) if val else None
    if not info:
        return ""
    emoji, label, color = info
    return f" <span style='color:{color};font-weight:bold;'>{emoji} {tr(label)}</span>"


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

    def __init__(self, service: ThesisService, parent=None, *,
                 profile_manager=None) -> None:
        super().__init__(parent)
        self.service = service
        self.profile_manager = profile_manager
        # Stav obhajob z tiché STAG kontroly (klíč → stav); plní se v období
        # státnic. Inicializace před první refresh() (detail ho čte).
        self._stag_states: dict = {}
        self._state_checker = None

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
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)

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
        left.addWidget(self.tree)

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
        row.addWidget(self.left_container)

        # Prostřední panel: detail vybrané komise (členové + studenti) / přehled.
        self.detail = QTextBrowser()
        # Linky neotvírat „navigací" (QTextBrowser by PDF načetl jako text =
        # změť) — odkaz na PDF otevřeme systémově, web v prohlížeči.
        self.detail.setOpenLinks(False)
        self.detail.anchorClicked.connect(self._open_detail_link)
        row.addWidget(self.detail, stretch=1)

        # Pravý panel: nezávislý „Můj harmonogram obhajob" pro vybraný rok.
        self.harmonogram_view = QTextBrowser()
        self.harmonogram_view.setOpenExternalLinks(False)
        self.right_container = QWidget()
        rcl = QVBoxLayout(self.right_container)
        rcl.setContentsMargins(0, 0, 0, 0)
        rcl.addWidget(self.harmonogram_view)
        row.addWidget(self.right_container)

        outer.addLayout(row, stretch=1)

        self._right_year = None
        self.refresh()

        # Tichá kontrola stavu obhajob (jen v období státnic) — vizualizuje,
        # kdo z mých studentů už obhájil. Nezapisuje do DB. Každých 15 minut.
        self._state_timer = QTimer(self)
        self._state_timer.setInterval(15 * 60_000)
        self._state_timer.timeout.connect(self._maybe_check_states)
        self._state_timer.start()
        QTimer.singleShot(3000, self._maybe_check_states)

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
        """„led" / „opp" / "" pro jeden slot rozpisu."""
        pnum = (slot.personal_number or "").strip().upper()
        if pnum and pnum in roles:
            return roles[pnum]
        return roles.get(_fold(slot.student_name), "")

    def _is_my_committee(self, committee) -> bool:
        me = self._user_name_fold()
        if not me:
            return False
        # Porovnání bez titulů: stačí, že foldované jméno člena obsahuje
        # foldované jméno uživatele (tituly jsou okolo jména).
        return any(me in _fold(m.name) for m in committee.members)

    # ── strom ────────────────────────────────────────────────────────────
    def refresh(self) -> None:
        selected = self._selected_id()
        roles = self.service.komise_student_roles()
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
            self.tree.addTopLevelItem(year_item)
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
                year_item.addChild(level_item)
                for c in sorted(by_level[level], key=lambda x: (x.obor, x.color)):
                    led = sum(1 for s in c.slots if self._slot_role(s, roles) == "led")
                    opp = sum(1 for s in c.slots if self._slot_role(s, roles) == "opp")
                    if self.chk_mine.isChecked() and not (led or opp):
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
                level_item.setExpanded(True)
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

    def _open_detail_link(self, url) -> None:
        """Klik na odkaz v detailu: PDF/soubor otevři systémově, web v prohlížeči."""
        from ._os_actions import open_path

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
        """Levý i pravý panel napevno dle obsahu; prostřední bere zbytek.

        Levý = šířka **stromu komisí** (ne PDF seznamu — ten může být širší
        kvůli dlouhým názvům a eliduje se), aby za komisemi nebyla mezera.
        Boky se zmenší poměrně, jen kdyby prostřednímu nezbylo ~320 px.
        """
        self.tree.expandAll()
        total = self.width() or 1400
        lw = max(220, self._tree_width(self.tree))
        if getattr(self, "_harmonogram_has_rows", False):
            doc = self.harmonogram_view.document()
            doc.setTextWidth(-1)
            rw = max(240, int(doc.idealWidth()) + 32)
        else:
            rw = 300   # prázdný harmonogram nemá rozšiřovat pravý panel
        avail = total - 320
        if lw + rw > avail > 0:
            scale = max(0.3, avail / (lw + rw))
            lw, rw = int(lw * scale), int(rw * scale)
        self.left_container.setFixedWidth(lw)
        self.right_container.setFixedWidth(rw)

    def showEvent(self, event) -> None:  # noqa: N802 (Qt API)
        super().showEvent(event)
        self._fit_panels()

    def resizeEvent(self, event) -> None:  # noqa: N802 (Qt API)
        super().resizeEvent(event)
        self._fit_panels()

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
        self._fit_panels()

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
            entries, heading, self._stag_states, nearest=nkey, nearest_text=ntext))

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
                        self._stag_states, s.personal_number, s.student_name)
                    sched_html += (
                        f"<tr><td style='padding:1px 12px 1px 0;color:{_MUTED};'>"
                        f"{escape(s.time)}</td>"
                        f"<td style='padding:1px 12px 1px 0;color:{_MUTED};'>"
                        f"{escape(s.personal_number)}</td>"
                        f"<td style='padding:1px 4px;{style}'>"
                        f"{escape(s.student_name)}{badge}</td>"
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
                               states=self._stag_states)
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
                f"{escape(e['student_name'])}{pnum}</td>"
                f"<td style='padding:2px 0 2px 8px;white-space:nowrap;'>{cd}</td></tr>"
            )
        out += "</table>"
    return out


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
