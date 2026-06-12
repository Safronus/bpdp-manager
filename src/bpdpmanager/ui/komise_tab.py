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

from PySide6.QtCore import Qt, Signal
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

#: Oficiální stránka FAI se složením komisí a rozpisy.
FAI_KOMISE_URL = (
    "https://fai.utb.cz/student/statni-zaverecne-zkousky/"
    "statni-zaverecne-zkousky-szz/slozeni-komisi-szz-a-rozpis-studentu-na-szz/"
)


def _fold(s: str) -> str:
    nfd = unicodedata.normalize("NFD", s or "")
    return "".join(c for c in nfd if not unicodedata.combining(c)).lower().strip()


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
        btn_import = QPushButton(tr("📄 Importovat PDF komisí…"))
        btn_import.setToolTip(tr(
            "Načte fakultní PDF (složení komisí i rozpis studentů — druh se "
            "rozpozná automaticky, rozpis i podle barvy nadpisů) a po náhledu "
            "uloží. PDF se ukládají do komise/<rok>/."
        ))
        btn_import.clicked.connect(self._import_pdfs)
        top.addWidget(btn_import)
        btn_web = QPushButton(tr("🌐 Otevřít web s rozpisy"))
        btn_web.setToolTip(tr("Otevře stránku FAI se složením komisí a rozpisy SZZ."))
        btn_web.clicked.connect(self._open_web)
        top.addWidget(btn_web)
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

        # ── splitter: strom vlevo, detail vpravo ─────────────────────────
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels([tr("Komise"), tr("Moji studenti")])
        self.tree.setRootIsDecorated(True)
        hdr = self.tree.header()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.tree.itemSelectionChanged.connect(self._on_selected)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._on_context_menu)
        splitter.addWidget(self.tree)

        self.detail = QTextBrowser()
        self.detail.setOpenExternalLinks(True)
        splitter.addWidget(self.detail)
        splitter.setSizes([380, 720])
        splitter.setStretchFactor(1, 2)
        outer.addWidget(splitter, stretch=1)

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
        for year in sorted(by_year, reverse=True):
            year_item = QTreeWidgetItem([f"📅 {year}", ""])
            font = year_item.font(0)
            font.setBold(True)
            year_item.setFont(0, font)
            self.tree.addTopLevelItem(year_item)
            for c in sorted(by_year[year], key=lambda x: (x.level, x.obor, x.color)):
                mine = sum(1 for s in c.slots if self._slot_role(s, roles))
                if self.chk_mine.isChecked() and not mine:
                    continue
                star = "⭐ " if self._is_my_committee(c) else ""
                label = f"{star}● {c.display_name}"
                leaf = QTreeWidgetItem([label, str(mine) if mine else "—"])
                leaf.setForeground(0, QBrush(QColor(committee_color_hex(c.color))))
                leaf.setData(0, ROLE_COMMITTEE_ID, c.id)
                if mine:
                    f2 = leaf.font(0)
                    f2.setBold(True)
                    leaf.setFont(0, f2)
                year_item.addChild(leaf)
            year_item.setExpanded(True)
        self.tree.blockSignals(False)
        if selected:
            self._select_id(selected)
        elif self.tree.topLevelItemCount():
            first = self.tree.topLevelItem(0)
            if first.childCount():
                self.tree.setCurrentItem(first.child(0))
        self._on_selected()

    def _selected_id(self) -> str | None:
        items = self.tree.selectedItems()
        return items[0].data(0, ROLE_COMMITTEE_ID) if items else None

    def _select_id(self, committee_id: str) -> None:
        for i in range(self.tree.topLevelItemCount()):
            year_item = self.tree.topLevelItem(i)
            for j in range(year_item.childCount()):
                leaf = year_item.child(j)
                if leaf.data(0, ROLE_COMMITTEE_ID) == committee_id:
                    self.tree.setCurrentItem(leaf)
                    return

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
        # Složení
        rows = ""
        for m in c.members:
            mine = me and me in _fold(m.name)
            name = escape(m.name)
            if mine:
                name = f"<b>⭐ {name}</b>"
            rows += (
                f"<tr><td style='padding:1px 14px 1px 0;color:#888;'>"
                f"{escape(m.role)}</td><td style='padding:1px 0;'>{name}</td></tr>"
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
    def _open_web(self) -> None:
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices

        QDesktopServices.openUrl(QUrl(FAI_KOMISE_URL))

    def _reset_committees(self) -> None:
        """Smaže všechny komise a načte čistý seed z JSONu (úklid starých dat)."""
        resp = QMessageBox.question(
            self, tr("Načíst komise znovu"),
            tr("Smaže VŠECHNY komise a načte čisté složení z aplikace.\n\n"
               "Použij na úklid starších naimportovaných komisí, které nesedí "
               "(chybí obor, duplicity, zmíchané barvy).\n\n"
               "⚠ Rozpisy studentů z dříve nahraných PDF zmizí — nahraj je "
               "potom znovu přes Importovat PDF komisí (napojí se už na "
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
            self, tr("Vyber PDF s komisemi / rozpisy"), "", "PDF (*.pdf)"
        )
        if not paths:
            return
        from ..services.komise_parser import parse_pdf

        committees = []
        schedules = []
        errors = []
        parsed_files = []
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
            parsed_files.append(Path(p))

        if not committees and not schedules:
            QMessageBox.warning(
                self, tr("Import komisí"),
                tr("Z vybraných PDF se nepodařilo nic načíst.")
                + ("\n\n" + "\n".join(errors) if errors else ""),
            )
            return

        dlg = KomiseImportPreviewDialog(committees, schedules, errors, self)
        if not dlg.exec():
            return
        committees, schedules = dlg.selected()

        # Ulož PDF strukturovaně (rok z první naparsované položky souboru).
        year = next(
            (x.academic_year for x in [*committees, *schedules] if x.academic_year),
            "",
        )
        rels = [self.service.komise_store_pdf(p, year) for p in parsed_files]
        stats = self.service.apply_komise_import(committees, schedules, rels)
        self.refresh()
        self.changed.emit()
        QMessageBox.information(
            self, tr("Import komisí"),
            tr("Hotovo: {created} nových komisí, {updated} aktualizovaných, "
               "{slots} slotů rozpisu.").format(**stats)
            + ("\n\n" + "\n".join(errors) if errors else ""),
        )

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
