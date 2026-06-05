from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
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
from .._os_actions import open_path, reveal_in_file_manager


class DocumentsWidget(QWidget):
    """Widget pro správu dokumentů a odkazů u jedné práce.

    Akce (nahrání souboru, odebrání, smazání ze složky) se promítají
    do služby okamžitě, aby data nedopadla rozhozená.
    """

    changed = Signal()

    def __init__(self, service: ThesisService, parent=None) -> None:
        super().__init__(parent)
        self.service = service
        self.thesis_id: str | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Strom — agregace podle typu souboru (AttachmentKind → soubory).
        self.tree = QTreeWidget()
        self.tree.setColumnCount(4)
        self.tree.setHeaderLabels(["Typ / soubor", "Verze", "Zdroj", "Cesta / URL"])
        self.tree.setRootIsDecorated(True)
        self.tree.setAlternatingRowColors(True)
        h = self.tree.header()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.tree.itemDoubleClicked.connect(self._open_selected)
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
        self.thesis_id = thesis_id
        # Při přepnutí na jinou práci resetujeme „uživatel si vybral typ",
        # aby heuristika v rámci nové práce mohla zase navrhovat.
        self._user_changed_kind = False
        self.refresh()

    def refresh(self) -> None:
        self.tree.clear()
        if not self.thesis_id:
            return
        thesis = self.service.get_thesis(self.thesis_id)
        if thesis is None:
            return

        show_old = self.chk_show_old.isChecked()

        # Seskup přílohy podle AttachmentKind. Pořadí skupin podle pořadí
        # v enumu AttachmentKind (Text práce, Přílohy, Deník, Zadání,
        # Posudky, Prezentace, STAG export, Jiné).
        by_kind: dict[AttachmentKind, list[tuple[int, "Attachment"]]] = {}
        for idx, att in enumerate(thesis.attachments):
            by_kind.setdefault(att.kind, []).append((idx, att))

        gray_fg = QBrush(QColor("#888"))
        red_fg = QBrush(QColor("#c62828"))
        kind_order = list(AttachmentKind)

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
            group_label = kind.label
            count_visible = len(visible)
            extra = ""
            if superseded_count and not show_old:
                extra = f"  (+{superseded_count} starší verze)"
            group_item = QTreeWidgetItem([f"{group_label}  ·  {count_visible}×{extra}", "", "", ""])
            gf = group_item.font(0)
            gf.setBold(True)
            group_item.setFont(0, gf)
            # group nemá UserRole index → není „vybíratelný" jako příloha
            self.tree.addTopLevelItem(group_item)

            for real_idx, att in visible:
                version_text = f"v{att.version}" + (" ✓" if att.is_current else "")
                # Soubor smazaný mimo aplikaci (např. ručně ve Finderu) → indikuj.
                is_missing = att.is_file and self._is_missing(att)
                source_text = (
                    ("⚠ chybí soubor" if is_missing else "📄 soubor")
                    if att.is_file else "🔗 odkaz"
                )
                leaf = QTreeWidgetItem([
                    att.label,
                    version_text,
                    source_text,
                    att.url_or_path,
                ])
                leaf.setData(0, Qt.ItemDataRole.UserRole, real_idx)
                if is_missing:
                    for c in range(4):
                        leaf.setForeground(c, red_fg)
                elif not att.is_current:
                    for c in range(4):
                        leaf.setForeground(c, gray_fg)
                    lf = leaf.font(0)
                    lf.setItalic(True)
                    leaf.setFont(0, lf)
                group_item.addChild(leaf)

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
        path = self.service.document_absolute_path(self.thesis_id, att)
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
            self.service.attach_document(
                self.thesis_id,
                Path(path_str),
                kind=kind,
                delete_source=delete_source,
            )
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
        thesis = self.service.get_thesis(self.thesis_id)
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
        self.service.upsert_thesis(thesis)
        self.refresh()
        self.changed.emit()

    def _remove_selected(self) -> None:
        if not self.thesis_id:
            return
        idx = self._selected_index()
        if idx is None:
            return
        thesis = self.service.get_thesis(self.thesis_id)
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
        self.service.remove_document(self.thesis_id, idx, delete_file=delete_file)
        self.refresh()
        self.changed.emit()

    def _open_selected(self, *_args) -> None:
        if not self.thesis_id:
            return
        idx = self._selected_index()
        if idx is None:
            return
        thesis = self.service.get_thesis(self.thesis_id)
        if thesis is None:
            return
        att = thesis.attachments[idx]

        if att.is_file:
            path = self.service.document_absolute_path(self.thesis_id, att)
            if path is None or not path.exists():
                QMessageBox.warning(self, "Otevřít", f"Soubor neexistuje:\n{path}")
                return
            open_path(path)
        else:
            open_path(att.url_or_path)

    def _reveal_selected(self) -> None:
        if not self.thesis_id:
            return
        idx = self._selected_index()
        if idx is None:
            return
        thesis = self.service.get_thesis(self.thesis_id)
        if thesis is None:
            return
        att = thesis.attachments[idx]
        if not att.is_file:
            QMessageBox.information(
                self, "Ve Finderu", "Odkaz/URL nelze zobrazit ve správci souborů."
            )
            return
        path = self.service.document_absolute_path(self.thesis_id, att)
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
        removed = self.service.prune_missing_documents(self.thesis_id)
        self.refresh()
        self.changed.emit()
        QMessageBox.information(
            self, "Odklidit chybějící", f"Odebráno záznamů: {removed}."
        )
