"""Dialogy pro přenos jedné práce přes ZIP balík.

- :class:`ThesisExportDialog` — před exportem nabídne výběr „co zahrnout"
  (data práce s náhledem + navázané entity + soubory po kategoriích, lze
  odznačit i jednotlivý soubor). Vše je defaultně zaškrtnuté.
- :class:`ThesisImportDialog` — po výběru ZIPu pozná, zda práce už existuje
  (podle ID z balíku, fallback student + typ + rok). Když existuje, nabídne
  „vytvořit novou" / „aktualizovat existující"; u aktualizace si uživatel
  zvolí, co se přepíše (stejný výběr jako u exportu).
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
)

from ..i18n import tr
from ..models.enums import ATTACHMENT_KIND_LABELS, ThesisStatus
from ..services.thesis_export import (
    ExportFileItem,
    ThesisContents,
    ThesisExportSelection,
    ThesisUpdateSelection,
    ThesisZipContents,
    gather_thesis_contents,
    read_thesis_zip,
)

# Role pro identifikaci položek ve stromu.
_ROLE_NODE = Qt.ItemDataRole.UserRole + 1  # typ uzlu (str)
_ROLE_RELPATH = Qt.ItemDataRole.UserRole + 2  # relpath souboru (str)

_NODE_DATA = "data"
_NODE_STUDENT = "student"
_NODE_OPPONENT = "opponent"
_NODE_OBOR = "obor"
_NODE_CATEGORY = "category"
_NODE_FILE = "file"


def _fmt_size(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n / 1024:.0f} kB"
    return f"{n / (1024 * 1024):.1f} MB"


def _checkable(item: QTreeWidgetItem, checked: bool = True) -> QTreeWidgetItem:
    item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
    item.setCheckState(
        0, Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
    )
    return item


def _group_files_by_category(files: list[ExportFileItem]) -> list[tuple]:
    """Seskupí soubory dle kategorie se zachováním pořadí (kind, label, items)."""
    groups: dict = {}
    for f in files:
        groups.setdefault(f.kind, []).append(f)
    out = []
    for kind, items in groups.items():
        label = ATTACHMENT_KIND_LABELS.get(kind, kind.value)
        out.append((kind, label, items))
    return out


class _CheckTreeMixin:
    """Strom s checkboxy a propagací rodič ↔ potomci (tri-state)."""

    def _init_check_tree(self) -> None:
        self._updating = False
        self.tree.itemChanged.connect(self._on_item_changed)

    def _on_item_changed(self, item: QTreeWidgetItem, _col: int) -> None:
        if self._updating:
            return
        self._updating = True
        self.tree.blockSignals(True)
        # rodič -> potomci
        state = item.checkState(0)
        if state != Qt.CheckState.PartiallyChecked and item.childCount():
            for i in range(item.childCount()):
                item.child(i).setCheckState(0, state)
        # potomek -> rodiče
        parent = item.parent()
        while parent is not None:
            states = [
                parent.child(i).checkState(0) for i in range(parent.childCount())
            ]
            if all(s == Qt.CheckState.Checked for s in states):
                new = Qt.CheckState.Checked
            elif all(s == Qt.CheckState.Unchecked for s in states):
                new = Qt.CheckState.Unchecked
            else:
                new = Qt.CheckState.PartiallyChecked
            parent.setCheckState(0, new)
            parent = parent.parent()
        self.tree.blockSignals(False)
        self._updating = False

    def _set_all(self, checked: bool) -> None:
        self._updating = True
        self.tree.blockSignals(True)

        def _walk(item: QTreeWidgetItem) -> None:
            if item.flags() & Qt.ItemFlag.ItemIsUserCheckable:
                item.setCheckState(
                    0, Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
                )
            for i in range(item.childCount()):
                _walk(item.child(i))

        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            _walk(root.child(i))
        self.tree.blockSignals(False)
        self._updating = False

    def _add_entity_nodes(
        self, contents, *, include_data: bool
    ) -> None:
        """Naplní strom: (volitelně Data práce) + navázané entity + soubory."""
        if include_data:
            data_item = QTreeWidgetItem(["📄 Data práce (stav, téma, posudky, známky…)"])
            data_item.setData(0, _ROLE_NODE, _NODE_DATA)
            _checkable(data_item)
            self.tree.addTopLevelItem(data_item)

        entities = QTreeWidgetItem(["🔗 Navázané entity"])
        entities.setData(0, _ROLE_NODE, "entities_group")
        _checkable(entities)
        if contents.student is not None:
            it = QTreeWidgetItem([f"Student: {contents.student.full_name}"])
            it.setData(0, _ROLE_NODE, _NODE_STUDENT)
            _checkable(it)
            entities.addChild(it)
        if contents.opponent is not None:
            it = QTreeWidgetItem([f"Oponent: {contents.opponent.display_name}"])
            it.setData(0, _ROLE_NODE, _NODE_OPPONENT)
            _checkable(it)
            entities.addChild(it)
        if contents.obor is not None:
            it = QTreeWidgetItem([f"Obor: {contents.obor.name}"])
            it.setData(0, _ROLE_NODE, _NODE_OBOR)
            _checkable(it)
            entities.addChild(it)
        if entities.childCount():
            self.tree.addTopLevelItem(entities)
            entities.setExpanded(True)

        for _kind, label, items in _group_files_by_category(contents.files):
            cat = QTreeWidgetItem([f"📎 {label}  ({len(items)})"])
            cat.setData(0, _ROLE_NODE, _NODE_CATEGORY)
            _checkable(cat)
            for f in items:
                leaf = QTreeWidgetItem([f"{f.label}  ·  {_fmt_size(f.size)}"])
                leaf.setData(0, _ROLE_NODE, _NODE_FILE)
                leaf.setData(0, _ROLE_RELPATH, f.relpath)
                leaf.setToolTip(0, f.relpath)
                _checkable(leaf)
                cat.addChild(leaf)
            self.tree.addTopLevelItem(cat)
            cat.setExpanded(True)

    def _collect(self) -> tuple[dict, set[str]]:
        """Posbírá zaškrtnuté uzly → (flagy entit/data, množina relpathů souborů)."""
        flags = {
            _NODE_DATA: False,
            _NODE_STUDENT: False,
            _NODE_OPPONENT: False,
            _NODE_OBOR: False,
        }
        relpaths: set[str] = set()

        def _walk(item: QTreeWidgetItem) -> None:
            node = item.data(0, _ROLE_NODE)
            checked = item.checkState(0) == Qt.CheckState.Checked
            if node in flags and checked:
                flags[node] = True
            if node == _NODE_FILE and checked:
                relpaths.add(item.data(0, _ROLE_RELPATH))
            for i in range(item.childCount()):
                _walk(item.child(i))

        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            _walk(root.child(i))
        return flags, relpaths


class ThesisExportDialog(QDialog, _CheckTreeMixin):
    """Výběr „co zahrnout" před exportem práce do ZIP."""

    def __init__(self, service, thesis_id: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Export práce do ZIP — co zahrnout"))
        self.resize(560, 560)
        self.contents: ThesisContents = gather_thesis_contents(service, thesis_id)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(self._preview_text()))

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        layout.addWidget(self.tree, 1)
        self._init_check_tree()
        self._add_entity_nodes(self.contents, include_data=False)

        row = QHBoxLayout()
        b_all = QPushButton(tr("Vybrat vše"))
        b_none = QPushButton(tr("Zrušit vše"))
        b_all.clicked.connect(lambda: self._set_all(True))
        b_none.clicked.connect(lambda: self._set_all(False))
        row.addWidget(b_all)
        row.addWidget(b_none)
        row.addStretch(1)
        layout.addLayout(row)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(tr("Exportovat"))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _preview_text(self) -> str:
        t = self.contents.thesis
        n_reviews = len(t.reviews)
        grades = []
        if t.grade_supervisor:
            grades.append(f"V: {t.grade_supervisor}")
        if t.grade_opponent:
            grades.append(f"O: {t.grade_opponent}")
        grade_str = ", ".join(grades) if grades else "—"
        try:
            status_lbl = t.status.label
        except Exception:
            status_lbl = t.status.value if isinstance(t.status, ThesisStatus) else str(t.status)
        return (
            f"<b>{t.type.value} · {t.display_title}</b><br>"
            f"Stav: {status_lbl} &nbsp;·&nbsp; Známky: {grade_str} &nbsp;·&nbsp; "
            f"Posudků: {n_reviews} &nbsp;·&nbsp; Rok: {t.academic_year}<br>"
            f"<i>Data práce se exportují vždy; níže vyber entity a soubory.</i>"
        )

    def selection(self) -> ThesisExportSelection:
        flags, relpaths = self._collect()
        return ThesisExportSelection(
            include_student=flags[_NODE_STUDENT],
            include_opponent=flags[_NODE_OPPONENT],
            include_obor=flags[_NODE_OBOR],
            file_relpaths=relpaths,
        )


class ThesisImportDialog(QDialog, _CheckTreeMixin):
    """Náhled balíku + volba nová/aktualizace a výběr „co aktualizovat"."""

    MODE_NEW = "new"
    MODE_UPDATE = "update"

    def __init__(self, service, source_zip, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Import práce ze ZIP"))
        self.resize(560, 600)
        self.service = service
        self.contents: ThesisZipContents = read_thesis_zip(source_zip, service=service)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(self._header_text()))

        self.rb_new = QRadioButton(tr("Vytvořit novou práci"))
        self.rb_update = QRadioButton(tr("Aktualizovat existující práci"))
        self._group = QButtonGroup(self)
        self._group.addButton(self.rb_new)
        self._group.addButton(self.rb_update)

        existing = self.contents.existing
        if existing is not None:
            layout.addWidget(QLabel(
                f"<b>Nalezena existující práce</b> ({self.contents.match_reason}):<br>"
                f"{existing.display_title}"
            ))
            self.rb_update.setChecked(True)
            layout.addWidget(self.rb_new)
            layout.addWidget(self.rb_update)
            layout.addWidget(QLabel(tr("<i>Co aktualizovat (přepsat z balíku):</i>")))
        else:
            layout.addWidget(QLabel(
                tr("<i>V databázi není odpovídající práce — bude vytvořena nová.</i>")
            ))
            self.rb_new.setChecked(True)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        layout.addWidget(self.tree, 1)
        self._init_check_tree()
        if existing is not None:
            self._add_entity_nodes(self.contents, include_data=True)
        else:
            self.tree.setVisible(False)

        row = QHBoxLayout()
        b_all = QPushButton(tr("Vybrat vše"))
        b_none = QPushButton(tr("Zrušit vše"))
        b_all.clicked.connect(lambda: self._set_all(True))
        b_none.clicked.connect(lambda: self._set_all(False))
        row.addWidget(b_all)
        row.addWidget(b_none)
        row.addStretch(1)
        layout.addLayout(row)

        self.rb_new.toggled.connect(self._sync_tree_enabled)
        self._sync_tree_enabled()

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(tr("Importovat"))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _header_text(self) -> str:
        m = self.contents.manifest
        return (
            f"<b>{m.get('thesis_type', '')} · {m.get('title', '(bez názvu)')}</b><br>"
            f"Student: {m.get('student', '') or '—'} &nbsp;·&nbsp; "
            f"Rok: {m.get('academic_year', '') or '—'}"
        )

    def _sync_tree_enabled(self) -> None:
        is_update = self.rb_update.isChecked() and self.contents.existing is not None
        self.tree.setEnabled(is_update)

    def mode(self) -> str:
        if self.contents.existing is not None and self.rb_update.isChecked():
            return self.MODE_UPDATE
        return self.MODE_NEW

    def target_id(self) -> str | None:
        if self.mode() == self.MODE_UPDATE and self.contents.existing is not None:
            return self.contents.existing.id
        return None

    def update_selection(self) -> ThesisUpdateSelection:
        flags, relpaths = self._collect()
        return ThesisUpdateSelection(
            update_data=flags[_NODE_DATA],
            update_student=flags[_NODE_STUDENT],
            update_opponent=flags[_NODE_OPPONENT],
            update_obor=flags[_NODE_OBOR],
            file_relpaths=relpaths,
        )
