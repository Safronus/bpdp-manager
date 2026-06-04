from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...models import Attachment, AttachmentKind
from ...services import ThesisService
from ...services.file_naming import guess_kind_from_filename


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

        # tabulka — 5 sloupců (přidán Verze)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["Typ", "Verze", "Popis / soubor", "Zdroj", "Cesta / URL"]
        )
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table.doubleClicked.connect(self._open_selected)
        layout.addWidget(self.table)

        # Toggle pro starší verze (defaultně schované)
        self.chk_show_old = QCheckBox("Zobrazit starší verze (superseded)")
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

        row.addStretch()

        self.btn_open = QPushButton("Otevřít")
        self.btn_open.clicked.connect(self._open_selected)
        row.addWidget(self.btn_open)

        self.btn_remove = QPushButton("Odebrat")
        self.btn_remove.clicked.connect(self._remove_selected)
        row.addWidget(self.btn_remove)

        layout.addLayout(row)

    # --- veřejné API ---------------------------------------------------------

    def set_thesis_id(self, thesis_id: str | None) -> None:
        self.thesis_id = thesis_id
        # Při přepnutí na jinou práci resetujeme „uživatel si vybral typ",
        # aby heuristika v rámci nové práce mohla zase navrhovat.
        self._user_changed_kind = False
        self.refresh()

    def refresh(self) -> None:
        self.table.setRowCount(0)
        if not self.thesis_id:
            return
        thesis = self.service.get_thesis(self.thesis_id)
        if thesis is None:
            return

        # Filtruj a setřiď:
        # - default (chk_show_old=False): jen is_current=True
        # - se zaškrtnutým chk_show_old: všechny, řadit kind asc → version desc
        show_old = self.chk_show_old.isChecked()
        rows: list[tuple[int, "Attachment"]] = list(enumerate(thesis.attachments))
        if not show_old:
            rows = [(i, a) for i, a in rows if a.is_current]
        # Sort: kind label asc, current first, version desc
        rows.sort(
            key=lambda pair: (
                pair[1].kind.label.lower(),
                0 if pair[1].is_current else 1,
                -pair[1].version,
            )
        )

        # Spočti počet superseded per kind pro hint v záhlaví current řádku
        superseded_per_kind: dict[AttachmentKind, int] = {}
        for _, att in enumerate(thesis.attachments):
            if not att.is_current:
                superseded_per_kind[att.kind] = (
                    superseded_per_kind.get(att.kind, 0) + 1
                )

        gray_fg = QBrush(QColor("#888"))
        for vis_row, (real_idx, att) in enumerate(rows):
            self.table.insertRow(vis_row)
            # Sloupec 0 = Typ
            kind_item = QTableWidgetItem(att.kind.label)
            f: QFont = kind_item.font()
            f.setBold(att.is_current)
            kind_item.setFont(f)
            kind_item.setData(Qt.ItemDataRole.UserRole, real_idx)
            self.table.setItem(vis_row, 0, kind_item)

            # Sloupec 1 = Verze (např. "v3 ✓ current" nebo "v1 (superseded)")
            if att.is_current:
                older = superseded_per_kind.get(att.kind, 0)
                version_text = (
                    f"v{att.version} ✓"
                    + (f"   (+{older} starší)" if older and not show_old else "")
                )
            else:
                version_text = f"v{att.version}"
            ver_item = QTableWidgetItem(version_text)
            if not att.is_current:
                ver_item.setForeground(gray_fg)
            self.table.setItem(vis_row, 1, ver_item)

            # Sloupec 2 = Popis
            label_item = QTableWidgetItem(att.label)
            if not att.is_current:
                label_item.setForeground(gray_fg)
                lf = label_item.font()
                lf.setItalic(True)
                label_item.setFont(lf)
            self.table.setItem(vis_row, 2, label_item)

            # Sloupec 3 = Zdroj
            source_item = QTableWidgetItem("📄 soubor" if att.is_file else "🔗 odkaz")
            if not att.is_current:
                source_item.setForeground(gray_fg)
            self.table.setItem(vis_row, 3, source_item)

            # Sloupec 4 = Cesta / URL
            path_item = QTableWidgetItem(att.url_or_path)
            if not att.is_current:
                path_item.setForeground(gray_fg)
            self.table.setItem(vis_row, 4, path_item)

    # --- akce ----------------------------------------------------------------

    def _selected_index(self) -> int | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

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
        try:
            self.service.attach_document(
                self.thesis_id,
                Path(path_str),
                kind=kind,
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

    def _open_selected(self) -> None:
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
            target = str(path)
        else:
            target = att.url_or_path

        if sys.platform == "darwin":
            subprocess.run(["open", target], check=False)
        elif sys.platform.startswith("linux"):
            subprocess.run(["xdg-open", target], check=False)
        elif sys.platform == "win32":
            try:
                os.startfile(target)  # type: ignore[attr-defined]
            except OSError as exc:
                QMessageBox.warning(self, "Otevřít", f"Nelze otevřít:\n{exc}")
