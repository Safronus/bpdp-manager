from __future__ import annotations

import shutil
from pathlib import Path

from PySide6.QtCore import QMimeData, Qt, QUrl, Signal
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...models import Attachment, AttachmentKind
from ...services import ThesisService
from ...services.file_naming import guess_kind_from_filename
from .._os_actions import open_path, print_path, reveal_in_file_manager


def _human_size(num_bytes: int) -> str:
    """Velikost souboru jako čitelný řetězec (B / KB / MB / GB / TB)."""
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{int(size)} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


# Barevné odlišení kategorií dokumentů (barva nadpisu skupiny).
_KIND_COLORS: dict[AttachmentKind, str] = {
    AttachmentKind.THESIS_TEXT: "#1565c0",        # modrá — plný text
    AttachmentKind.THESIS_APPENDIX: "#00838f",    # tyrkysová — přílohy
    AttachmentKind.THESIS_BUNDLE: "#00695c",      # tmavě tyrkysová — text+přílohy
    AttachmentKind.WORK_JOURNAL: "#6d4c41",       # hnědá — deník
    AttachmentKind.ASSIGNMENT: "#5e35b1",         # fialová — zadání
    AttachmentKind.SUPERVISOR_REVIEW: "#c62828",  # červená — posudky
    AttachmentKind.OPPONENT_REVIEW: "#ad1457",    # vínová — posudky
    AttachmentKind.PRESENTATION: "#ef6c00",       # oranžová — prezentace
    AttachmentKind.DEFENSE_RECORD: "#283593",     # indigo — průběh obhajoby
    AttachmentKind.STAG_EXPORT: "#546e7a",        # šedomodrá — STAG export
    AttachmentKind.OTHER: "#455a64",              # šedá — jiné
}
_REVIEW_KINDS = (AttachmentKind.SUPERVISOR_REVIEW, AttachmentKind.OPPONENT_REVIEW)
_REVIEW_GROUP_COLOR = "#b71c1c"  # nadřazená skupina „Posudky"


class DocumentsWidget(QWidget):
    """Widget pro správu dokumentů a odkazů u jedné práce.

    Akce (nahrání souboru, odebrání, smazání ze složky) se promítají
    do služby okamžitě, aby data nedopadla rozhozená.
    """

    changed = Signal()

    def __init__(self, service: ThesisService, parent=None, *, profile_manager=None) -> None:
        super().__init__(parent)
        self.service = service
        self.profile_manager = profile_manager  # pro „Odeslat mailem" (SMTP)
        self.thesis_id: str | None = None
        # Když True, widget pracuje s OpposingThesis (oponentský posudek) —
        # volá opposing_* metody služby. Jinak s vedenou Thesis.
        self.opposing: bool = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Strom — agregace podle typu souboru (AttachmentKind → soubory).
        self.tree = QTreeWidget()
        self.tree.setColumnCount(5)
        self.tree.setHeaderLabels(
            ["Typ / soubor", "Verze", "Velikost", "Formát", "Cesta k souboru"]
        )
        self.tree.setRootIsDecorated(True)
        self.tree.setAlternatingRowColors(True)
        self.tree.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        h = self.tree.header()
        # První sloupce se přizpůsobí obsahu; poslední (cesta k souboru) zabere
        # zbývající šířku, ať za ním nezůstává prázdné místo.
        for col in range(4):
            h.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        h.setStretchLastSection(True)
        self.tree.itemDoubleClicked.connect(self._open_selected)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._on_context_menu)
        layout.addWidget(self.tree)

        # Toggle pro starší verze (defaultně schované)
        self.chk_show_old = QCheckBox("Zobrazit starší verze (superseded)")
        self.chk_show_old.setChecked(True)  # výchozí: ukázat i archiv/starší verze
        self.chk_show_old.setToolTip(
            "Když je odškrtnuto, vidíš jen aktuální verzi každého typu. "
            "Při nahrání nové verze se předchozí automaticky schová."
        )
        self.chk_show_old.toggled.connect(lambda _: self.refresh())
        layout.addWidget(self.chk_show_old)

        # tlačítka
        row = QHBoxLayout()

        self.cb_kind = QComboBox()
        for k in AttachmentKind:
            self.cb_kind.addItem(k.label, k.value)
        # Sleduje, jestli uživatel ručně přepnul typ — pak heuristika
        # při uploadu nepřepisuje jeho volbu.
        self._user_changed_kind = False
        self.cb_kind.activated.connect(self._on_kind_activated)
        row.addWidget(self.cb_kind)

        self.btn_upload = QPushButton("📎 Nahrát soubor…")
        self.btn_upload.clicked.connect(self._upload)
        row.addWidget(self.btn_upload)

        self.btn_url = QPushButton("🔗 Přidat odkaz/URL…")
        self.btn_url.clicked.connect(self._add_url)
        row.addWidget(self.btn_url)

        # Po dokončení uploadu: smazat originální soubor (default zapnuto —
        # uživatel typicky nechce, aby zdroj zůstal v Downloads a duplikoval
        # se s kopií v documents/).
        self.chk_delete_source = QCheckBox("🗑 Smazat originál po nahrání")
        self.chk_delete_source.setChecked(True)
        self.chk_delete_source.setToolTip(
            "Po úspěšném nahrání soubor odstraní z původního umístění "
            "(typicky Downloads). Kopie je bezpečně uložená v documents/ "
            "konkrétní práce, takže o nic nepřijdeš. Pro testování / "
            "opakované nahrávání odškrtni."
        )
        row.addWidget(self.chk_delete_source)

        row.addStretch()

        self.btn_open = QPushButton("Otevřít")
        self.btn_open.clicked.connect(self._open_selected)
        row.addWidget(self.btn_open)

        self.btn_reveal = QPushButton("📂 Ve Finderu")
        self.btn_reveal.setToolTip("Zobrazí vybraný soubor ve správci souborů (Finder / Explorer).")
        self.btn_reveal.clicked.connect(self._reveal_selected)
        row.addWidget(self.btn_reveal)

        self.btn_remove = QPushButton("Odebrat")
        self.btn_remove.clicked.connect(self._remove_selected)
        row.addWidget(self.btn_remove)

        layout.addLayout(row)

        # Druhá řádka — úklid mrtvých záznamů (soubory smazané mimo aplikaci).
        row2 = QHBoxLayout()
        self.lbl_missing = QLabel("")
        self.lbl_missing.setStyleSheet("color:#c62828;")
        row2.addWidget(self.lbl_missing, stretch=1)
        self.btn_prune = QPushButton("🧹 Odklidit chybějící")
        self.btn_prune.setToolTip(
            "Odebere ze seznamu záznamy, jejichž soubor byl smazán mimo aplikaci "
            "(např. ručně ve Finderu). Existující soubory ani odkazy se nedotkne."
        )
        self.btn_prune.clicked.connect(self._prune_missing)
        self.btn_prune.setVisible(False)
        row2.addWidget(self.btn_prune)
        layout.addLayout(row2)

    # --- veřejné API ---------------------------------------------------------

    def set_thesis_id(self, thesis_id: str | None) -> None:
        """Nastaví widget na vedenou práci (Thesis)."""
        self.opposing = False
        self.thesis_id = thesis_id
        # Při přepnutí na jinou práci resetujeme „uživatel si vybral typ",
        # aby heuristika v rámci nové práce mohla zase navrhovat.
        self._user_changed_kind = False
        self.refresh()

    def set_opposing_id(self, op_id: str | None) -> None:
        """Nastaví widget na oponentský posudek (OpposingThesis)."""
        self.opposing = True
        self.thesis_id = op_id
        self._user_changed_kind = False
        self.refresh()

    # --- dispatch (Thesis × OpposingThesis) ----------------------------------

    def _get_work(self):
        if not self.thesis_id:
            return None
        return (
            self.service.get_opposing_thesis(self.thesis_id)
            if self.opposing
            else self.service.get_thesis(self.thesis_id)
        )

    def _abs_path(self, att: Attachment):
        return (
            self.service.opposing_document_absolute_path(self.thesis_id, att)
            if self.opposing
            else self.service.document_absolute_path(self.thesis_id, att)
        )

    def _size_text(self, att: Attachment) -> str:
        """Lidsky čitelná velikost souboru (prázdné u odkazů / chybějících)."""
        if not att.is_file:
            return ""
        path = self._abs_path(att)
        try:
            if path is None or not path.is_file():
                return ""
            return _human_size(path.stat().st_size)
        except OSError:
            return ""

    def _attach(self, path: Path, kind: AttachmentKind, delete_source: bool):
        if self.opposing:
            return self.service.opposing_attach_document(
                self.thesis_id, path, kind=kind, delete_source=delete_source
            )
        return self.service.attach_document(
            self.thesis_id, path, kind=kind, delete_source=delete_source
        )

    def _remove(self, index: int, delete_file: bool) -> None:
        if self.opposing:
            self.service.opposing_remove_document(
                self.thesis_id, index, delete_file=delete_file
            )
        else:
            self.service.remove_document(
                self.thesis_id, index, delete_file=delete_file
            )

    def _upsert_work(self, work) -> None:
        if self.opposing:
            self.service.upsert_opposing_thesis(work)
        else:
            self.service.upsert_thesis(work)

    def _prune(self) -> int:
        return (
            self.service.opposing_prune_missing_documents(self.thesis_id)
            if self.opposing
            else self.service.prune_missing_documents(self.thesis_id)
        )

    def _format_text(self, att: Attachment, is_missing: bool) -> str:
        """Indikátor druhu souboru ve sloupci „Formát": přípona (PDF/ZIP/…),
        nebo odkaz / chybějící soubor."""
        if not att.is_file:
            return "🔗 odkaz"
        if is_missing:
            return "⚠ chybí"
        ext = Path(att.url_or_path).suffix.lstrip(".").upper()
        return ext or "soubor"

    def _path_text(self, att: Attachment) -> str:
        """Celá cesta k souboru od kořene (u odkazů samotná URL)."""
        if not att.is_file:
            return att.url_or_path
        path = self._abs_path(att)
        return str(path) if path is not None else att.url_or_path

    def _make_group_item(self, label: str, color: str) -> QTreeWidgetItem:
        """Tučný barevný nadpis skupiny (kategorie dokumentů)."""
        item = QTreeWidgetItem([label, "", "", "", ""])
        gf = item.font(0)
        gf.setBold(True)
        item.setFont(0, gf)
        item.setForeground(0, QBrush(QColor(color)))
        return item

    def _make_leaf(self, real_idx: int, att: Attachment) -> QTreeWidgetItem:
        """Řádek jednoho dokumentu/odkazu."""
        gray_fg = QBrush(QColor("#888"))
        red_fg = QBrush(QColor("#c62828"))
        version_text = f"v{att.version}" + (" ✓" if att.is_current else "")
        # Soubor smazaný mimo aplikaci (např. ručně ve Finderu) → indikuj.
        is_missing = att.is_file and self._is_missing(att)
        leaf = QTreeWidgetItem([
            att.label,
            version_text,
            self._size_text(att) if not is_missing else "",
            self._format_text(att, is_missing),
            self._path_text(att),
        ])
        leaf.setData(0, Qt.ItemDataRole.UserRole, real_idx)
        leaf.setTextAlignment(
            2, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        if is_missing:
            for c in range(5):
                leaf.setForeground(c, red_fg)
        elif not att.is_current:
            for c in range(5):
                leaf.setForeground(c, gray_fg)
            lf = leaf.font(0)
            lf.setItalic(True)
            leaf.setFont(0, lf)
        return leaf

    def refresh(self) -> None:
        self.tree.clear()
        if not self.thesis_id:
            return
        thesis = self._get_work()
        if thesis is None:
            return

        show_old = self.chk_show_old.isChecked()

        # Seskup přílohy podle AttachmentKind. Pořadí skupin podle pořadí
        # v enumu AttachmentKind (Text práce, Přílohy, Deník, Zadání,
        # Posudky, Prezentace, STAG export, Jiné).
        by_kind: dict[AttachmentKind, list[tuple[int, "Attachment"]]] = {}
        for idx, att in enumerate(thesis.attachments):
            by_kind.setdefault(att.kind, []).append((idx, att))

        kind_order = list(AttachmentKind)
        posudky_parent: QTreeWidgetItem | None = None

        for kind in kind_order:
            items = by_kind.get(kind)
            if not items:
                continue
            # Filtruj superseded podle toggle
            visible = items if show_old else [(i, a) for i, a in items if a.is_current]
            if not visible:
                continue
            # Řazení uvnitř skupiny: current first, pak version desc
            visible.sort(key=lambda pair: (0 if pair[1].is_current else 1, -pair[1].version))

            superseded_count = sum(1 for _, a in items if not a.is_current)
            count_visible = len(visible)
            extra = ""
            if superseded_count and not show_old:
                extra = f"  (+{superseded_count} starší verze)"
            label = f"{kind.label}  ·  {count_visible}×{extra}"
            color = _KIND_COLORS.get(kind, "#455a64")

            # Posudky (vedoucího/oponenta) sdruž do nadřazené skupiny „Posudky".
            if kind in _REVIEW_KINDS:
                if posudky_parent is None:
                    posudky_parent = self._make_group_item(
                        "Posudky", _REVIEW_GROUP_COLOR
                    )
                    self.tree.addTopLevelItem(posudky_parent)
                    posudky_parent.setExpanded(True)
                group_item = self._make_group_item(label, color)
                posudky_parent.addChild(group_item)
            else:
                group_item = self._make_group_item(label, color)
                self.tree.addTopLevelItem(group_item)

            for real_idx, att in visible:
                group_item.addChild(self._make_leaf(real_idx, att))
            group_item.setExpanded(True)

        # Spočítej chybějící napříč VŠEMI přílohami (i schovanými staršími),
        # ať se úklid nabídne i pro mrtvé záznamy mimo aktuální filtr.
        missing_count = sum(
            1 for att in thesis.attachments if att.is_file and self._is_missing(att)
        )
        if missing_count:
            self.lbl_missing.setText(
                f"⚠ {missing_count}× chybí soubor na disku (smazán mimo aplikaci)."
            )
            self.btn_prune.setVisible(True)
        else:
            self.lbl_missing.setText("")
            self.btn_prune.setVisible(False)

    def _is_missing(self, att: Attachment) -> bool:
        """True, pokud jde o soubor, jehož fyzická cesta neexistuje."""
        if not att.is_file:
            return False
        path = self._abs_path(att)
        return path is None or not path.exists()

    # --- akce ----------------------------------------------------------------

    def _selected_index(self) -> int | None:
        item = self.tree.currentItem()
        if item is None:
            return None
        data = item.data(0, Qt.ItemDataRole.UserRole)
        return data if isinstance(data, int) else None

    def _current_kind(self) -> AttachmentKind:
        return AttachmentKind(self.cb_kind.currentData())

    def _upload(self) -> None:
        if not self.thesis_id:
            QMessageBox.information(
                self,
                "Nahrát soubor",
                "Před nahráním dokumentu nejdřív uložte rozpracovanou práci.",
            )
            return
        path_str, _ = QFileDialog.getOpenFileName(
            self,
            "Vyber soubor pro nahrání",
            str(Path.home()),
            "Všechny soubory (*.*);;PDF (*.pdf);;Word (*.docx *.doc)",
        )
        if not path_str:
            return
        # Auto-detekce typu z původního názvu — jen pokud heuristika něco vrátí
        # a uživatel ještě explicitně nepřepnul ComboBox (typicky výchozí
        # ``THESIS_TEXT`` nebo ``OTHER``). Když si vybral něco jiného, jeho
        # volbu respektujeme a nepřepisujeme ji.
        kind = self._current_kind()
        guessed = guess_kind_from_filename(Path(path_str).name)
        if guessed is not None and not self._user_changed_kind:
            kind = guessed
            self._select_kind(kind)
        delete_source = self.chk_delete_source.isChecked()
        try:
            self._attach(Path(path_str), kind, delete_source)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Chyba", f"Nepodařilo se nahrát soubor:\n{exc}")
            return
        self.refresh()
        self.changed.emit()

    def _select_kind(self, kind: AttachmentKind) -> None:
        """Najde položku v ComboBoxu podle ``AttachmentKind`` a vybere ji.

        Programové přepnutí (z heuristiky) **neoznačí** typ jako ručně zvolený.
        """
        for i in range(self.cb_kind.count()):
            if self.cb_kind.itemData(i) == kind.value:
                self.cb_kind.blockSignals(True)
                try:
                    self.cb_kind.setCurrentIndex(i)
                finally:
                    self.cb_kind.blockSignals(False)
                return

    def _on_kind_activated(self, _index: int) -> None:
        """Uživatel vybral typ ručně — od teď heuristika nezasahuje."""
        self._user_changed_kind = True

    def _add_url(self) -> None:
        if not self.thesis_id:
            return
        url, ok = QInputDialog.getText(self, "Přidat odkaz", "URL nebo cesta:")
        if not ok or not url.strip():
            return
        label, ok = QInputDialog.getText(self, "Popis", "Popis odkazu:", text=url.strip())
        if not ok:
            return
        thesis = self._get_work()
        if thesis is None:
            return
        # Verzování i pro URL — supersede stávající current téhož kind
        kind = self._current_kind()
        same_kind = [a for a in thesis.attachments if a.kind == kind]
        next_version = max((a.version for a in same_kind), default=0) + 1
        for a in same_kind:
            a.is_current = False
        thesis.attachments.append(
            Attachment(
                label=label.strip() or url.strip(),
                url_or_path=url.strip(),
                kind=kind,
                is_file=False,
                version=next_version,
                is_current=True,
            )
        )
        self._upsert_work(thesis)
        self.refresh()
        self.changed.emit()

    def _remove_selected(self) -> None:
        if not self.thesis_id:
            return
        idx = self._selected_index()
        if idx is None:
            return
        thesis = self._get_work()
        if thesis is None:
            return
        att = thesis.attachments[idx]
        if att.is_file:
            confirm = QMessageBox.question(
                self,
                "Odebrat dokument",
                f"Odebrat „{att.label}“ ze seznamu?\n\nSouběžně smazat i soubor ze složky?",
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No
                | QMessageBox.StandardButton.Cancel,
            )
            if confirm == QMessageBox.StandardButton.Cancel:
                return
            delete_file = confirm == QMessageBox.StandardButton.Yes
        else:
            confirm = QMessageBox.question(self, "Odebrat odkaz", f"Odebrat „{att.label}“?")
            if confirm != QMessageBox.StandardButton.Yes:
                return
            delete_file = False
        self._remove(idx, delete_file)
        self.refresh()
        self.changed.emit()

    def _open_selected(self, *_args) -> None:
        if not self.thesis_id:
            return
        idx = self._selected_index()
        if idx is None:
            return
        thesis = self._get_work()
        if thesis is None:
            return
        att = thesis.attachments[idx]

        if att.is_file:
            path = self._abs_path(att)
            if path is None or not path.exists():
                QMessageBox.warning(self, "Otevřít", f"Soubor neexistuje:\n{path}")
                return
            open_path(path)
        else:
            open_path(att.url_or_path)

    def _selected_file_attachments(self) -> list[Attachment]:
        """Vrátí přílohy-soubory napříč aktuálním výběrem (ne odkazy/skupiny)."""
        work = self._get_work()
        if work is None:
            return []
        out: list[Attachment] = []
        for it in self.tree.selectedItems():
            idx = it.data(0, Qt.ItemDataRole.UserRole)
            if isinstance(idx, int) and 0 <= idx < len(work.attachments):
                att = work.attachments[idx]
                if att.is_file:
                    out.append(att)
        return out

    def _selected_indices(self) -> list[int]:
        """Indexy všech vybraných dokumentů (soubory i odkazy), bez skupin."""
        work = self._get_work()
        if work is None:
            return []
        idxs = set()
        for it in self.tree.selectedItems():
            idx = it.data(0, Qt.ItemDataRole.UserRole)
            if isinstance(idx, int) and 0 <= idx < len(work.attachments):
                idxs.add(idx)
        return sorted(idxs)

    def _remove_many_selected(self) -> None:
        """Hromadně odebere vybrané dokumenty (volitelně i smaže soubory)."""
        if not self.thesis_id:
            return
        work = self._get_work()
        if work is None:
            return
        idxs = self._selected_indices()
        if not idxs:
            return
        n_files = sum(1 for i in idxs if work.attachments[i].is_file)
        confirm = QMessageBox.question(
            self, "Odebrat dokumenty",
            f"Odebrat {len(idxs)} vybraných dokumentů ze seznamu?"
            + (f"\n\nSouběžně smazat i {n_files} souborů ze složky?" if n_files else ""),
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No
            | QMessageBox.StandardButton.Cancel,
        )
        if confirm == QMessageBox.StandardButton.Cancel:
            return
        delete_file = confirm == QMessageBox.StandardButton.Yes
        # Mazání odzadu — nižší indexy zůstávají platné.
        for i in sorted(idxs, reverse=True):
            self._remove(i, delete_file)
        self.refresh()
        self.changed.emit()

    def _on_context_menu(self, pos) -> None:
        item = self.tree.itemAt(pos)
        # Jen nad konkrétní přílohou (leaf má UserRole index), ne nad skupinou.
        if item is None or not isinstance(item.data(0, Qt.ItemDataRole.UserRole), int):
            return
        # Když kliknutý není ve výběru, vyber jen jeho (jinak zachovej multi-výběr).
        if item not in self.tree.selectedItems():
            self.tree.setCurrentItem(item)
        idx = item.data(0, Qt.ItemDataRole.UserRole)
        work = self._get_work()
        att = work.attachments[idx] if (work and 0 <= idx < len(work.attachments)) else None
        is_file = att is not None and att.is_file
        sel_files = self._selected_file_attachments()
        multi = len(sel_files) > 1

        menu = QMenu(self)
        act_open = menu.addAction("Otevřít")
        act_reveal = menu.addAction("📂 Zobrazit ve Finderu")
        act_copy = act_export = act_email = None
        act_export_many = act_email_many = None
        n_sel = len(self._selected_indices())
        if multi:
            menu.addSeparator()
            act_export_many = menu.addAction(f"💾 Exportovat vybrané ({len(sel_files)})…")
            act_email_many = menu.addAction(f"✉ Odeslat vybrané mailem ({len(sel_files)})…")
        act_print = None
        if is_file:
            menu.addSeparator()
            if att.url_or_path.lower().endswith((".pdf", ".xlsx")):
                act_print = menu.addAction("🖨 Tisk")
            act_copy = menu.addAction("📋 Kopírovat soubor (do schránky)")
            act_export = menu.addAction("💾 Exportovat na disk…")
            act_email = menu.addAction("✉ Odeslat mailem…")
        menu.addSeparator()
        act_remove_many = None
        if n_sel > 1:
            act_remove_many = menu.addAction(f"🗑 Odebrat vybrané ({n_sel})…")
            act_remove = None
        else:
            act_remove = menu.addAction("Odebrat")
        chosen = menu.exec(self.tree.viewport().mapToGlobal(pos))
        if chosen is None:
            return
        if chosen == act_open:
            self._open_selected()
        elif chosen == act_reveal:
            self._reveal_selected()
        elif chosen == act_remove:
            self._remove_selected()
        elif chosen == act_remove_many:
            self._remove_many_selected()
        elif chosen == act_copy:
            self._copy_file_to_clipboard(att)
        elif chosen == act_export:
            self._export_file(att)
        elif chosen == act_email:
            self._email_file(att)
        elif chosen == act_print:
            self._print_file(att)
        elif chosen == act_export_many:
            self._export_files(sel_files)
        elif chosen == act_email_many:
            self._email_files(sel_files)

    # --- akce nad souborem ---------------------------------------------------

    def _export_files(self, atts: list[Attachment]) -> None:
        """Exportuje více souborů do zvolené složky."""
        paths = [(att, self._abs_path(att)) for att in atts]
        paths = [(att, p) for att, p in paths if p is not None and p.exists()]
        if not paths:
            QMessageBox.warning(self, "Exportovat", "Žádný z vybraných souborů neexistuje.")
            return
        target_dir = QFileDialog.getExistingDirectory(
            self, "Exportovat vybrané soubory do složky", str(Path.home())
        )
        if not target_dir:
            return
        ok, errors = 0, []
        for _att, p in paths:
            try:
                shutil.copy2(p, Path(target_dir) / p.name)
                ok += 1
            except OSError as exc:
                errors.append(f"{p.name}: {exc}")
        msg = f"Exportováno {ok} z {len(paths)} souborů do:\n{target_dir}"
        if errors:
            msg += "\n\nChyby:\n" + "\n".join(errors)
        QMessageBox.information(self, "Export", msg)

    def _email_files(self, atts: list[Attachment]) -> None:
        """Odešle více souborů jako přílohy jednoho e-mailu."""
        paths = []
        for att in atts:
            p = self._abs_path(att)
            if p is not None and p.exists():
                paths.append(p)
        if not paths:
            QMessageBox.warning(self, "Odeslat mailem", "Žádný z vybraných souborů neexistuje.")
            return
        if self.profile_manager is None or self.profile_manager.active is None:
            QMessageBox.information(
                self, "Odeslat mailem",
                "Odesílání e-mailem vyžaduje aktivní profil s vyplněným e-mailem "
                "(👤 → Nastavení e-mailu).",
            )
            return
        from ..send_file_dialog import SendFileDialog

        SendFileDialog(
            self.profile_manager, paths,
            default_subject=f"Soubory ({len(paths)})", parent=self,
        ).exec()

    def _print_file(self, att: Attachment) -> None:
        """Vytiskne soubor (PDF přímo na tiskárnu, XLSX otevře k ručnímu tisku)."""
        path = self._abs_path(att)
        if path is None or not path.exists():
            QMessageBox.warning(self, "Tisk", f"Soubor neexistuje:\n{path}")
            return
        result = print_path(path)
        if result == "printed":
            QMessageBox.information(
                self, "Tisk", f"Soubor byl odeslán na výchozí tiskárnu:\n{path.name}"
            )
        elif result == "opened":
            QMessageBox.information(
                self, "Tisk",
                f"Soubor jsem otevřel v aplikaci — vytiskni ho odtud (Cmd/Ctrl+P):"
                f"\n{path.name}",
            )
        else:
            QMessageBox.warning(self, "Tisk", f"Tisk se nezdařil:\n{path.name}")

    def _copy_file_to_clipboard(self, att: Attachment) -> None:
        """Zkopíruje SOUBOR do schránky (jde vložit do Finderu / mailu), ne cestu."""
        path = self._abs_path(att)
        if path is None or not path.exists():
            QMessageBox.warning(self, "Kopírovat", f"Soubor neexistuje:\n{path}")
            return
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(str(path))])
        mime.setText(str(path))  # fallback (cesta jako text)
        QApplication.clipboard().setMimeData(mime)

    def _export_file(self, att: Attachment) -> None:
        path = self._abs_path(att)
        if path is None or not path.exists():
            QMessageBox.warning(self, "Exportovat", f"Soubor neexistuje:\n{path}")
            return
        target, _ = QFileDialog.getSaveFileName(
            self, "Exportovat soubor", str(Path.home() / path.name)
        )
        if not target:
            return
        try:
            shutil.copy2(path, target)
        except OSError as exc:
            QMessageBox.critical(self, "Exportovat", f"Nepodařilo se uložit:\n{exc}")
            return

    def _email_file(self, att: Attachment) -> None:
        path = self._abs_path(att)
        if path is None or not path.exists():
            QMessageBox.warning(self, "Odeslat mailem", f"Soubor neexistuje:\n{path}")
            return
        if self.profile_manager is None or self.profile_manager.active is None:
            QMessageBox.information(
                self, "Odeslat mailem",
                "Odesílání e-mailem vyžaduje aktivní profil s vyplněným e-mailem "
                "(👤 → Nastavení e-mailu).",
            )
            return
        from ..send_file_dialog import SendFileDialog

        SendFileDialog(
            self.profile_manager, path,
            default_subject=f"{att.kind.label} — {path.name}", parent=self,
        ).exec()

    def _reveal_selected(self) -> None:
        if not self.thesis_id:
            return
        idx = self._selected_index()
        if idx is None:
            return
        thesis = self._get_work()
        if thesis is None:
            return
        att = thesis.attachments[idx]
        if not att.is_file:
            QMessageBox.information(
                self, "Ve Finderu", "Odkaz/URL nelze zobrazit ve správci souborů."
            )
            return
        path = self._abs_path(att)
        if path is None or not path.exists():
            QMessageBox.warning(self, "Ve Finderu", f"Soubor neexistuje:\n{path}")
            return
        reveal_in_file_manager(path)

    def _prune_missing(self) -> None:
        if not self.thesis_id:
            return
        confirm = QMessageBox.question(
            self,
            "Odklidit chybějící",
            "Odebrat ze seznamu všechny záznamy, jejichž soubor už na disku "
            "neexistuje?\n\nSmažou se jen záznamy v aplikaci — žádné existující "
            "soubory ani odkazy se nedotkne.",
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        removed = self._prune()
        self.refresh()
        self.changed.emit()
        QMessageBox.information(
            self, "Odklidit chybějící", f"Odebráno záznamů: {removed}."
        )
