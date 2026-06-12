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

from PySide6.QtCore import QRectF, QSize, Qt, Signal
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

ROLE_COMMITTEE_ID = Qt.ItemDataRole.UserRole + 1
#: (vedené, oponované) počty studentů komise — pro StudentsVODelegate.
ROLE_VO = Qt.ItemDataRole.UserRole + 2
#: Absolutní cesta k PDF v seznamu souborů (otevření z kontextového menu).
ROLE_PDF_PATH = Qt.ItemDataRole.UserRole + 3

#: Stupeň → pořadí a popisek skupiny ve stromu (Bc před Mgr).
_LEVEL_ORDER = {"Bc": 0, "Mgr": 1}
_LEVEL_LABEL = {"Bc": "Bakalářské (Bc)", "Mgr": "Magisterské (Mgr)"}

#: Barvy badge ve sloupci „Studenti V/O" (vedené modře, oponované červeně).
_VO_LED_BG = "#1e88e5"
_VO_OPP_BG = "#e53935"

#: Barvy „pilulky" role člena komise (světlé pozadí, tmavý text).
_ROLE_COLORS = {
    "předseda": ("#ede7f6", "#4a148c"),       # fialová — předseda
    "místopředseda": ("#e3f2fd", "#0d47a1"),  # modrá — místopředseda
    "tajemník": ("#e8f5e9", "#1b5e20"),       # zelená — tajemník
    "člen": ("#eceff1", "#455a64"),           # šedá — člen
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

        # ── splitter: vlevo strom komisí + seznam PDF, vpravo detail ──────
        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        left = QSplitter(Qt.Orientation.Vertical)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels([tr("Komise"), tr("Studenti V/O"), tr("Termíny")])
        self.tree.setRootIsDecorated(True)
        self.tree.setItemDelegateForColumn(1, StudentsVODelegate(self.tree))
        hdr = self.tree.header()
        # Šířka sloupců dle dat; levý panel se přizpůsobí v _fit_left_pane.
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
        pv.addWidget(QLabel("📎 " + tr("PDF souborů komisí")))
        self.pdf_tree = QTreeWidget()
        self.pdf_tree.setHeaderHidden(True)
        self.pdf_tree.setRootIsDecorated(True)
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
        self.splitter.addWidget(left)

        self.detail = QTextBrowser()
        self.detail.setOpenExternalLinks(True)
        self.splitter.addWidget(self.detail)
        self.splitter.setStretchFactor(1, 2)
        outer.addWidget(self.splitter, stretch=1)

        self.refresh()

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
            self._select_first_leaf()
        self._on_selected()
        self._refresh_pdf_list()
        self._fit_left_pane()

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

    def _select_first_leaf(self) -> None:
        leaf = next(self._iter_leaves(), None)
        if leaf is not None:
            self.tree.setCurrentItem(leaf)

    def _selected_id(self) -> str | None:
        items = self.tree.selectedItems()
        return items[0].data(0, ROLE_COMMITTEE_ID) if items else None

    def _select_id(self, committee_id: str) -> None:
        for leaf in self._iter_leaves():
            if leaf.data(0, ROLE_COMMITTEE_ID) == committee_id:
                self.tree.setCurrentItem(leaf)
                return

    def _fit_left_pane(self) -> None:
        """Šířka levého panelu podle obsahu stromu (sloupce + odsazení)."""
        self.tree.expandAll()
        width = self.tree.header().length() + self.tree.indentation() * 2 + 28
        total = self.splitter.size().width() or 1100
        left = max(280, min(width, int(total * 0.62)))
        self.splitter.setSizes([left, max(total - left, 320)])

    # ── detail ───────────────────────────────────────────────────────────
    def _on_selected(self) -> None:
        cid = self._selected_id()
        committee = self.service.get_committee(cid) if cid else None
        if committee is None:
            self.detail.setHtml(
                "<p style='color:#888;padding:18px;'>"
                + tr("Vyber komisi vlevo, nebo importuj PDF s komisemi.")
                + "</p>"
            )
            return
        self.detail.setHtml(self._committee_html(committee))

    def _committee_html(self, c) -> str:
        from html import escape

        roles = self.service.komise_student_roles()
        me = self._user_name_fold()
        hexcol = committee_color_hex(c.color)
        head = (
            f"<h2 style='margin:4px 0;'><span style='color:{hexcol};'>●</span> "
            f"{escape(c.display_name)}"
            + (" ⭐" if self._is_my_committee(c) else "") + "</h2>"
            f"<p style='color:#888;margin:2px 0 10px 0;'>{escape(c.academic_year)}"
            + (" &nbsp;·&nbsp; " + escape(", ".join(c.dates)) if c.dates else "")
            + "</p>"
        )
        # Složení — role barevně odlišené (předseda/místopředseda/tajemník/člen).
        rows = ""
        for m in c.members:
            mine = me and me in _fold(m.name)
            name = escape(m.name)
            if mine:
                name = f"<b>⭐ {name}</b>"
            bg, fg = _ROLE_COLORS.get(_role_key(m.role), _ROLE_COLORS["člen"])
            role_pill = (
                f"<span style='background:{bg};color:{fg};padding:1px 7px;"
                f"border-radius:7px;white-space:nowrap;'>{escape(m.role)}</span>"
            )
            rows += (
                f"<tr><td style='padding:2px 12px 2px 0;'>{role_pill}</td>"
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
                    sched_html += (
                        f"<tr><td style='padding:1px 12px 1px 0;color:#888;'>"
                        f"{escape(s.time)}</td>"
                        f"<td style='padding:1px 12px 1px 0;color:#888;'>"
                        f"{escape(s.personal_number)}</td>"
                        f"<td style='padding:1px 4px;{style}'>"
                        f"{escape(s.student_name)}{badge}</td></tr>"
                    )
                sched_html += "</table>"
        # Zdrojové PDF
        files_html = ""
        if c.source_files:
            links = " · ".join(
                f"<a href='file://{self.service.komise_pdf_path(rp)}'>"
                f"{escape(Path(rp).name)}</a>"
                for rp in c.source_files
            )
            files_html = (
                f"<p style='color:#888;font-size:11px;margin-top:14px;'>"
                f"{tr('Zdrojová PDF:')} {links}</p>"
            )
        return head + members_html + sched_html + files_html

    # ── akce ─────────────────────────────────────────────────────────────
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
        committees, schedules = dlg.selected()

        # Ulož každé PDF strukturovaně a přejmenované do rozpisy/ nebo slozeni/.
        rels = []
        for path, r in parsed:
            fyear = next(
                (x.academic_year for x in [*r.schedules, *r.committees]
                 if x.academic_year), "",
            )
            if r.schedules:
                name = self._pdf_name(fyear, r.schedules, "rozpis-studentu")
                kind = "rozpisy"
            else:
                name = self._pdf_name(fyear, r.committees, "slozeni-komisi")
                kind = "slozeni"
            rels.append(
                self.service.komise_store_pdf(path, fyear, name=name, kind=kind)
            )
        stats = self.service.apply_komise_import(committees, schedules, rels)
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
