"""Náprava zařazení textu práce a příloh.

Řeší dva pozůstatky staršího stahování ze STAG (kde se druh souboru v sekci
„elektronická podoba" odvozoval jen pořadím):

1. **Prohození** — archiv (zip) uložený jako *Text práce* a PDF jako *Příloha*.
   Oprava druhy prohodí.
2. **Balík** — archiv jako *Text práce*, ke kterému není žádné samostatné PDF
   (text + přílohy jsou v jednom zipu). Přeřadí se na *Text práce + přílohy*.

Náhled ukáže, co se přeřadí; obsah souborů se nemění, před zápisem je záloha.
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

_ROLE_FIX = Qt.ItemDataRole.UserRole + 1  # ("swap", SwappedDocs) | ("bundle", TextBundle)


class SwappedDocsDialog(QDialog):
    """Náhled chybně zařazených dokumentů (prohození / balík) + oprava vybraných."""

    data_changed = Signal()

    def __init__(self, service: ThesisService, parent=None,
                 *, profile_manager=None) -> None:
        super().__init__(parent)
        self.service = service
        self.profile_manager = profile_manager
        self.setWindowTitle("Náprava zařazení textu a příloh")
        self.setMinimumSize(780, 480)
        self._reload()

        outer = QVBoxLayout(self)
        intro = QLabel(
            "Náprava staršího zařazení souborů ze STAG. <b>Prohození</b>: archiv "
            "(zip) je veden jako <i>Text práce</i> a PDF jako <i>Příloha</i> — "
            "oprava druh prohodí. <b>Balík</b>: archiv jako <i>Text práce</i> bez "
            "samostatného PDF (text i přílohy v jednom zipu) — přeřadí se na "
            "<i>Text práce + přílohy</i>. Obsah souborů se nemění; před zápisem se "
            "vytvoří záloha."
        )
        intro.setWordWrap(True)
        outer.addWidget(intro)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Práce / dokument", "Nyní", "Bude"])
        self.tree.setColumnWidth(0, 440)
        outer.addWidget(self.tree, stretch=1)
        self._populate()

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
        self.btn_fix.setEnabled(self._has_any)
        outer.addWidget(buttons)

    # ── data ───────────────────────────────────────────────────────────────
    def _reload(self) -> None:
        self._swaps = self.service.find_swapped_documents()
        self._bundles = self.service.find_text_bundles()

    @property
    def _has_any(self) -> bool:
        return bool(self._swaps or self._bundles)

    # ── náhled ─────────────────────────────────────────────────────────────
    def _add_group(self, label: str, fix) -> QTreeWidgetItem:
        group = QTreeWidgetItem([label, "", ""])
        group.setFlags(group.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        group.setCheckState(0, Qt.CheckState.Checked)
        group.setData(0, _ROLE_FIX, fix)
        f = group.font(0)
        f.setBold(True)
        group.setFont(0, f)
        self.tree.addTopLevelItem(group)
        return group

    def _populate(self) -> None:
        self.tree.clear()
        if not self._has_any:
            empty = QTreeWidgetItem(["✓ Žádné chybně zařazené dokumenty nenalezeny.", "", ""])
            empty.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.tree.addTopLevelItem(empty)
            return
        for sw in self._swaps:
            group = self._add_group(f"↔ {sw.work_label}", ("swap", sw))
            child_pdf = QTreeWidgetItem([f"📄 {sw.appendix_label}", "Příloha", "Text práce"])
            child_zip = QTreeWidgetItem([f"🗜 {sw.text_label}", "Text práce", "Příloha"])
            for ch in (child_pdf, child_zip):
                ch.setFlags(Qt.ItemFlag.ItemIsEnabled)
                group.addChild(ch)
            group.setExpanded(True)
        for bd in self._bundles:
            group = self._add_group(f"📦 {bd.work_label}", ("bundle", bd))
            child = QTreeWidgetItem([
                f"🗜 {bd.label}", "Text práce", "Text práce + přílohy"
            ])
            child.setFlags(Qt.ItemFlag.ItemIsEnabled)
            group.addChild(child)
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
                data_dir / "db.json", suffix="before-doc-repair", dedupe=False
            )
        except Exception:
            pass

    def _repair(self) -> None:
        swap_items, bundle_items = [], []
        for grp in self._iter_groups():
            if grp.checkState(0) != Qt.CheckState.Checked:
                continue
            tag, fix = grp.data(0, _ROLE_FIX)
            if tag == "swap":
                swap_items.append((fix.work_id, fix.is_opposing, fix.text_url, fix.appendix_url))
            else:
                bundle_items.append((fix.work_id, fix.is_opposing, fix.url))
        if not swap_items and not bundle_items:
            self.status.setText("Nic není vybráno k opravě.")
            return
        self._make_backup()
        n_swap = self.service.repair_swapped_documents(swap_items) if swap_items else 0
        n_bundle = self.service.reclassify_text_bundles(bundle_items) if bundle_items else 0
        self.data_changed.emit()
        parts = []
        if n_swap:
            parts.append(f"prohození: {n_swap}")
        if n_bundle:
            parts.append(f"balíky: {n_bundle}")
        self.status.setText("Opraveno — " + ", ".join(parts) + "." if parts else "Nic neopraveno.")
        self._reload()
        self._populate()
        self.btn_fix.setEnabled(self._has_any)
