"""Úklid duplicitních příloh — náhled + výběr + smazání.

Najde přílohy (a *Jiné*) se shodným obsahem v rámci jedné práce (typicky
opětovné stažení téhož souboru ze STAG → duplikát) a nabídne jejich smazání.
Náhled ukazuje, co a proč se smaže (zůstane jedna kopie). Text práce a posudky
se neřeší.
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
from .widgets.documents_widget import _human_size

_ROLE_DUP = Qt.ItemDataRole.UserRole + 1


class AppendixCleanupDialog(QDialog):
    """Náhled duplicitních příloh + smazání vybraných."""

    data_changed = Signal()

    def __init__(self, service: ThesisService, parent=None) -> None:
        super().__init__(parent)
        self.service = service
        self.setWindowTitle("Úklid duplicitních příloh")
        self.setMinimumSize(720, 460)
        self._dups = service.find_duplicate_appendices()

        outer = QVBoxLayout(self)
        intro = QLabel(
            "Tyto přílohy mají <b>shodný obsah</b> jako jiná příloha téže práce "
            "(typicky opětovné stažení ze STAG). Zaškrtnuté se <b>smažou</b> "
            "(soubor i evidence); u každé je uvedeno, která kopie zůstane. "
            "Text práce ani posudky se neřeší."
        )
        intro.setWordWrap(True)
        outer.addWidget(intro)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Práce / soubor ke smazání", "Velikost", "Zůstane"])
        self.tree.setColumnWidth(0, 380)
        outer.addWidget(self.tree, stretch=1)
        self._populate()

        if self._dups:
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
        self.btn_delete = buttons.addButton(
            "🗑 Smazat vybrané", QDialogButtonBox.ButtonRole.AcceptRole
        )
        buttons.addButton(QDialogButtonBox.StandardButton.Close).clicked.connect(
            self.reject
        )
        self.btn_delete.clicked.connect(self._delete)
        self.btn_delete.setEnabled(bool(self._dups))
        outer.addWidget(buttons)

    # ── náhled ─────────────────────────────────────────────────────────────
    def _populate(self) -> None:
        self.tree.clear()
        if not self._dups:
            self.tree.addTopLevelItem(
                QTreeWidgetItem(["✓ Žádné duplicitní přílohy nenalezeny.", "", ""])
            )
            return
        by_work: dict[str, list] = {}
        for d in self._dups:
            by_work.setdefault(d.work_label, []).append(d)
        for work_label, dups in by_work.items():
            label = f"{work_label}  ({len(dups)} ks)"
            group = QTreeWidgetItem([label, "", ""])
            group.setFlags(group.flags() & ~Qt.ItemFlag.ItemIsUserCheckable)
            f = group.font(0)
            f.setBold(True)
            group.setFont(0, f)
            self.tree.addTopLevelItem(group)
            for d in dups:
                leaf = QTreeWidgetItem([
                    d.del_label, _human_size(d.size), f"→ {d.keep_label}"
                ])
                leaf.setFlags(
                    Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable
                )
                leaf.setCheckState(0, Qt.CheckState.Checked)
                leaf.setData(0, _ROLE_DUP, d)
                group.addChild(leaf)
            group.setExpanded(True)

    def _iter_leaves(self):
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            grp = root.child(i)
            for j in range(grp.childCount()):
                leaf = grp.child(j)
                if leaf.flags() & Qt.ItemFlag.ItemIsUserCheckable:
                    yield leaf

    def _set_all(self, checked: bool) -> None:
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        for leaf in self._iter_leaves():
            leaf.setCheckState(0, state)

    def _delete(self) -> None:
        items = []
        for leaf in self._iter_leaves():
            if leaf.checkState(0) == Qt.CheckState.Checked:
                d = leaf.data(0, _ROLE_DUP)
                items.append((d.work_id, d.is_opposing, d.del_url))
        if not items:
            self.status.setText("Nic není vybráno ke smazání.")
            return
        removed = self.service.delete_appendix_duplicates(items)
        self.data_changed.emit()
        self.status.setText(f"Smazáno {removed} duplicitních příloh.")
        # přenačti zbylé duplikáty (typicky už žádné)
        self._dups = self.service.find_duplicate_appendices()
        self._populate()
        self.btn_delete.setEnabled(bool(self._dups))
