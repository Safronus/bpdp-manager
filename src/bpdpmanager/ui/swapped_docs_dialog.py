"""Náprava prohozeného textu práce a přílohy.

STAG soubory v sekci „elektronická podoba" se dřív rozlišovaly jen pořadím, takže
když přišel zip dřív než PDF, uložil se **archiv jako Text práce** a **PDF jako
Příloha**. Tento dialog najde takové jednoznačné prohozy, v náhledu ukáže, co se
přeřadí, a po potvrzení druhy prohodí (a soubory přejmenuje/přesune).
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
)

from ..services import ThesisService

_ROLE_SWAP = Qt.ItemDataRole.UserRole + 1


class SwappedDocsDialog(QDialog):
    """Náhled prohozených dokumentů (text ↔ příloha) + oprava vybraných."""

    data_changed = Signal()

    def __init__(self, service: ThesisService, parent=None,
                 *, profile_manager=None) -> None:
        super().__init__(parent)
        self.service = service
        self.profile_manager = profile_manager
        self.setWindowTitle("Náprava prohozeného textu a přílohy")
        self.setMinimumSize(760, 460)
        self._swaps = service.find_swapped_documents()

        outer = QVBoxLayout(self)
        intro = QLabel(
            "U těchto prací je <b>archiv (zip…) veden jako Text práce</b> a "
            "<b>PDF jako Příloha</b> — typický pozůstatek staršího stahování ze "
            "STAG, kde se pořadí souborů prohodilo. Oprava <b>prohodí druh</b> a "
            "soubory <b>přejmenuje/přesune</b> do správné složky (obsah se nemění). "
            "Před zápisem se vytvoří záloha."
        )
        intro.setWordWrap(True)
        outer.addWidget(intro)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Práce / dokument", "Nyní", "Bude"])
        self.tree.setColumnWidth(0, 420)
        outer.addWidget(self.tree, stretch=1)
        self._populate()

        if self._swaps:
            row = QHBoxLayout()
            btn_all = QPushButton("Vybrat vše")
            btn_none = QPushButton("Zrušit vše")
            btn_all.clicked.connect(lambda: self._set_all(True))
            btn_none.clicked.connect(lambda: self._set_all(False))
            row.addWidget(btn_all)
            row.addWidget(btn_none)
            row.addStretch(1)
            outer.addLayout(row)

        self.status = QLabel("")
        self.status.setWordWrap(True)
        outer.addWidget(self.status)

        buttons = QDialogButtonBox()
        self.btn_fix = buttons.addButton(
            "🔧 Opravit vybrané", QDialogButtonBox.ButtonRole.AcceptRole
        )
        buttons.addButton(QDialogButtonBox.StandardButton.Close).clicked.connect(
            self.reject
        )
        self.btn_fix.clicked.connect(self._repair)
        self.btn_fix.setEnabled(bool(self._swaps))
        outer.addWidget(buttons)

    # ── náhled ─────────────────────────────────────────────────────────────
    def _populate(self) -> None:
        self.tree.clear()
        if not self._swaps:
            empty = QTreeWidgetItem(["✓ Žádné prohozené dokumenty nenalezeny.", "", ""])
            empty.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.tree.addTopLevelItem(empty)
            return
        for sw in self._swaps:
            group = QTreeWidgetItem([sw.work_label, "", ""])
            group.setFlags(group.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            group.setCheckState(0, Qt.CheckState.Checked)
            group.setData(0, _ROLE_SWAP, sw)
            f = group.font(0)
            f.setBold(True)
            group.setFont(0, f)
            self.tree.addTopLevelItem(group)
            child_pdf = QTreeWidgetItem([
                f"📄 {sw.appendix_label}", "Příloha", "Text práce"
            ])
            child_zip = QTreeWidgetItem([
                f"🗜 {sw.text_label}", "Text práce", "Příloha"
            ])
            for ch in (child_pdf, child_zip):
                ch.setFlags(Qt.ItemFlag.ItemIsEnabled)
                group.addChild(ch)
            group.setExpanded(True)

    def _iter_groups(self):
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            grp = root.child(i)
            if grp.flags() & Qt.ItemFlag.ItemIsUserCheckable:
                yield grp

    def _set_all(self, checked: bool) -> None:
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        for grp in self._iter_groups():
            grp.setCheckState(0, state)

    def _make_backup(self) -> None:
        """Záchranná záloha db.json před přeřazením (přejmenovává soubory)."""
        if not (self.profile_manager and self.profile_manager.active):
            return
        try:
            from ..services.backup_manager import BackupManager

            data_dir = self.profile_manager.active_data_dir()
            BackupManager(data_dir).create_backup(
                data_dir / "db.json", suffix="before-swap-repair", dedupe=False
            )
        except Exception:
            pass

    def _repair(self) -> None:
        items = []
        for grp in self._iter_groups():
            if grp.checkState(0) == Qt.CheckState.Checked:
                sw = grp.data(0, _ROLE_SWAP)
                items.append((sw.work_id, sw.is_opposing, sw.text_url, sw.appendix_url))
        if not items:
            self.status.setText("Nic není vybráno k opravě.")
            return
        self._make_backup()
        repaired = self.service.repair_swapped_documents(items)
        self.data_changed.emit()
        self.status.setText(f"Opraveno {repaired} prací.")
        self._swaps = self.service.find_swapped_documents()
        self._populate()
        self.btn_fix.setEnabled(bool(self._swaps))
