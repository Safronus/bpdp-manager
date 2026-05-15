"""Dialogy pro správu seznamů (studenti, oponenti, obory)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..models import Opponent, Student, Thesis
from ..models.enums import OpponentKind, ThesisStatus, ThesisType
from ..services import ThesisService
from .opponent_dialog import OpponentDialog
from .student_dialog import StudentDialog

# Stavy, ve kterých má student „aktivní" práci
_ACTIVE_STATES = {
    ThesisStatus.RESERVED,
    ThesisStatus.LISTED,
    ThesisStatus.ASSIGNED,
    ThesisStatus.IN_PROGRESS,
}


class StudentsManageDialog(QDialog):
    """Správa studentů — grupování podle typu práce (BP/DP) → obor, řazení dle příjmení.

    - Checkbox *Skrýt dokončené studenty* odfiltruje studenty s obhájenou prací.
    - Studenti se barevně odlišují podle stavu/roku jejich aktuální práce:
      modře = běží v aktuálním ak. roce, tyrkysově = budoucí rok / zájemce,
      šedě kurzívou = dokončeno, červeně kurzívou = nedokončeno.
    """

    def __init__(self, service: ThesisService, parent=None) -> None:
        super().__init__(parent)
        self.service = service
        self.setWindowTitle("Studenti")
        self.setMinimumSize(760, 560)

        layout = QVBoxLayout(self)

        # ── horní lišta s filtrem ───────────────────────────────────────────
        top_row = QHBoxLayout()
        self.chk_hide_defended = QCheckBox("Skrýt dokončené studenty")
        self.chk_hide_defended.toggled.connect(self._refresh)
        top_row.addWidget(self.chk_hide_defended)
        top_row.addStretch()
        self.lbl_info = QLabel("")
        self.lbl_info.setStyleSheet("color: #888; font-size: 11px;")
        top_row.addWidget(self.lbl_info)
        layout.addLayout(top_row)

        # ── strom ──────────────────────────────────────────────────────────
        self.tree = QTreeWidget()
        self.tree.setColumnCount(3)
        self.tree.setHeaderLabels(["Příjmení, Jméno", "Osobní č.", "Stav (rok)"])
        self.tree.setAlternatingRowColors(True)
        self.tree.setRootIsDecorated(True)
        self.tree.itemDoubleClicked.connect(self._edit)
        h = self.tree.header()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        h.setStretchLastSection(False)
        layout.addWidget(self.tree, stretch=1)

        # ── tlačítka ────────────────────────────────────────────────────────
        row = QHBoxLayout()
        btn_new = QPushButton("Nový…")
        btn_edit = QPushButton("Upravit…")
        btn_delete = QPushButton("Smazat")
        btn_close = QPushButton("Zavřít")
        btn_new.clicked.connect(self._new)
        btn_edit.clicked.connect(self._edit)
        btn_delete.clicked.connect(self._delete)
        btn_close.clicked.connect(self.accept)
        row.addWidget(btn_new)
        row.addWidget(btn_edit)
        row.addWidget(btn_delete)
        row.addStretch()
        row.addWidget(btn_close)
        layout.addLayout(row)

        # vysvětlivka barev
        legend = QLabel(
            '<span style="color:#1565c0">●</span> aktuální rok &nbsp;&nbsp; '
            '<span style="color:#00897b">●</span> budoucí rok &nbsp;&nbsp; '
            '<span style="color:#888">●</span> dokončeno &nbsp;&nbsp; '
            '<span style="color:#c62828">●</span> nedokončeno'
        )
        legend.setStyleSheet("font-size: 11px; padding: 4px 0;")
        layout.addWidget(legend)

        self._refresh()

    # --- načítání + grupování -----------------------------------------------

    def _refresh(self) -> None:
        selected_id = self._selected_student_id()
        self.tree.clear()

        current_year = ThesisService.current_academic_year()
        hide_defended = self.chk_hide_defended.isChecked()

        # group: type_code -> obor -> [(student, primary_thesis)]
        groups: dict[str, dict[str, list[tuple[Student, Thesis]]]] = {}
        no_thesis: list[Student] = []
        hidden_count = 0
        total = 0

        for student in self.service.list_students():
            total += 1
            primary = self._primary_thesis(student.id)
            if primary is None:
                no_thesis.append(student)
                continue
            if hide_defended and primary.status == ThesisStatus.DEFENDED:
                hidden_count += 1
                continue
            type_code = primary.type.value
            obor_key = student.obor or "(bez oboru)"
            groups.setdefault(type_code, {}).setdefault(obor_key, []).append(
                (student, primary)
            )

        # DP první (typicky novější/větší práce), pak BP
        for type_code in ("DP", "BP"):
            if type_code not in groups:
                continue
            type_label = ThesisType(type_code).label
            type_count = sum(len(v) for v in groups[type_code].values())
            type_item = QTreeWidgetItem([f"📚 {type_label}  ({type_count})", "", ""])
            type_item.setFirstColumnSpanned(True)
            f = type_item.font(0)
            f.setBold(True)
            f.setPointSize(f.pointSize() + 1)
            type_item.setFont(0, f)
            self.tree.addTopLevelItem(type_item)

            for obor in sorted(groups[type_code].keys()):
                students_in_obor = sorted(
                    groups[type_code][obor],
                    key=lambda sp: (
                        sp[0].last_name.lower(),
                        sp[0].first_name.lower(),
                    ),
                )
                obor_item = QTreeWidgetItem(
                    [f"  {obor}  ({len(students_in_obor)})", "", ""]
                )
                obor_item.setFirstColumnSpanned(True)
                of = obor_item.font(0)
                of.setItalic(True)
                obor_item.setFont(0, of)
                type_item.addChild(obor_item)

                for student, primary in students_in_obor:
                    leaf = self._make_student_row(student, primary, current_year)
                    obor_item.addChild(leaf)
                obor_item.setExpanded(True)
            type_item.setExpanded(True)

        if no_thesis:
            no_thesis.sort(key=lambda s: (s.last_name.lower(), s.first_name.lower()))
            nt_item = QTreeWidgetItem(
                [f"Bez přiřazené práce  ({len(no_thesis)})", "", ""]
            )
            nt_item.setFirstColumnSpanned(True)
            nt_item.setForeground(0, QBrush(QColor("#888")))
            self.tree.addTopLevelItem(nt_item)
            for student in no_thesis:
                leaf = self._make_student_row(student, None, current_year)
                nt_item.addChild(leaf)
            nt_item.setExpanded(True)

        # info
        shown = total - hidden_count if hide_defended else total
        info = f"Zobrazeno: {shown} / {total}"
        if hide_defended and hidden_count:
            info += f"   (skryto dokončených: {hidden_count})"
        self.lbl_info.setText(info)

        if selected_id:
            self._select_student(selected_id)

    def _make_student_row(
        self,
        student: Student,
        primary: Thesis | None,
        current_year: str,
    ) -> QTreeWidgetItem:
        name = f"{student.last_name}, {student.first_name}"
        uni_id = student.university_id or ""
        if primary:
            year = primary.academic_year or ""
            status_text = f"  {primary.status.label}  "
            if year:
                status_text = f"  {primary.status.label}  ·  {year}  "
        else:
            status_text = "—"

        leaf = QTreeWidgetItem([name, uni_id, status_text])
        leaf.setData(0, Qt.ItemDataRole.UserRole, student)

        # Barva podle stavu/roku
        category = _category_for(primary, current_year)
        color = _CATEGORY_COLORS.get(category)
        italic = category in ("defended", "cancelled", "no_thesis")

        if color is not None:
            leaf.setForeground(0, QBrush(QColor(color)))
            leaf.setForeground(1, QBrush(QColor(color)))
        if italic:
            f = leaf.font(0)
            f.setItalic(True)
            leaf.setFont(0, f)
            leaf.setFont(1, f)

        if category == "current":
            f = leaf.font(0)
            f.setBold(True)
            leaf.setFont(0, f)

        # Status badge (sloupec 2) má barevné pozadí ze status.color
        if primary:
            status_color = QColor(primary.status.color)
            leaf.setBackground(2, QBrush(status_color))
            leaf.setForeground(2, QBrush(QColor("white")))
            sf = leaf.font(2)
            sf.setBold(True)
            leaf.setFont(2, sf)
            leaf.setTextAlignment(
                2, Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
            )

        # Tooltip se shrnutím všech prací studenta
        all_theses = sorted(
            [t for t in self.service.list_theses() if t.student_id == student.id],
            key=lambda t: t.academic_year or "",
            reverse=True,
        )
        if all_theses:
            tip_lines = [f"{student.full_name}", ""]
            for t in all_theses:
                tip_lines.append(
                    f"{t.type.value} {t.academic_year or '?'} — "
                    f"{t.status.label} — {t.display_title}"
                )
            leaf.setToolTip(0, "\n".join(tip_lines))

        return leaf

    def _primary_thesis(self, student_id: str) -> Thesis | None:
        """Vrátí 'aktuální' práci studenta dle priority stavů a roků."""
        theses = [
            t for t in self.service.list_theses() if t.student_id == student_id
        ]
        if not theses:
            return None
        return min(theses, key=_thesis_priority)

    # --- výběr a akce -------------------------------------------------------

    def _selected_student_id(self) -> str | None:
        student = self._current_student()
        return student.id if student else None

    def _current_student(self) -> Student | None:
        item = self.tree.currentItem()
        if item is None:
            return None
        data = item.data(0, Qt.ItemDataRole.UserRole)
        return data if isinstance(data, Student) else None

    def _select_student(self, student_id: str) -> bool:
        stack = [self.tree.topLevelItem(i) for i in range(self.tree.topLevelItemCount())]
        while stack:
            item = stack.pop()
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if isinstance(data, Student) and data.id == student_id:
                self.tree.setCurrentItem(item)
                return True
            for i in range(item.childCount()):
                stack.append(item.child(i))
        return False

    def _new(self) -> None:
        dlg = StudentDialog(self.service, parent=self)
        if dlg.exec():
            self._refresh()

    def _edit(self) -> None:
        s = self._current_student()
        if s is None:
            return
        dlg = StudentDialog(self.service, s, parent=self)
        if dlg.exec():
            self._refresh()

    def _delete(self) -> None:
        s = self._current_student()
        if s is None:
            return
        confirm = QMessageBox.question(
            self,
            "Smazat studenta",
            f'Opravdu smazat „{s.full_name}"? Práce, které ho mají přiřazeného, '
            f"zůstanou (bez studenta).",
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.service.delete_student(s.id)
            self._refresh()


# --- pomocné funkce mimo třídu -----------------------------------------------


def _thesis_priority(t: Thesis) -> tuple[int, int]:
    """Klíč pro řazení prací — nejnižší tuple = nejaktuálnější."""
    if t.status in _ACTIVE_STATES:
        tier = 0
    elif t.status == ThesisStatus.INTERESTED:
        tier = 1
    elif t.status == ThesisStatus.DEFENDED:
        tier = 2
    else:  # CANCELLED
        tier = 3
    try:
        year_part = int((t.academic_year or "0/0").split("/")[0])
    except (ValueError, IndexError):
        year_part = 0
    return (tier, -year_part)


def _category_for(thesis: Thesis | None, current_year: str) -> str:
    """Vrátí kategorii pro barevné odlišení."""
    if thesis is None:
        return "no_thesis"
    if thesis.status == ThesisStatus.DEFENDED:
        return "defended"
    if thesis.status == ThesisStatus.CANCELLED:
        return "cancelled"
    if thesis.status == ThesisStatus.INTERESTED:
        return "future"
    # active state
    if thesis.academic_year == current_year:
        return "current"
    if thesis.academic_year and thesis.academic_year > current_year:
        return "future"
    return "current"  # běžící práce z minulého roku — pořád aktivní


_CATEGORY_COLORS: dict[str, str | None] = {
    "current": "#1565c0",   # modrá — aktuální rok
    "future": "#00897b",    # tyrkysová — budoucí rok / zájemce
    "defended": "#888888",  # šedá — obhájeno
    "cancelled": "#c62828", # červená — nedokončeno
    "no_thesis": "#9e9e9e", # šedá — bez práce
}


class OpponentsManageDialog(QDialog):
    """Správa oponentů — odděleně interní a externí."""

    def __init__(self, service: ThesisService, parent=None) -> None:
        super().__init__(parent)
        self.service = service
        self.setWindowTitle("Oponenti")
        self.setMinimumSize(640, 520)

        layout = QVBoxLayout(self)

        self.tabs = QTabWidget()
        self.list_internal = self._build_list_tab(OpponentKind.INTERNAL)
        self.list_external = self._build_list_tab(OpponentKind.EXTERNAL)
        self.tabs.addTab(self.list_internal, "Interní (UTB)")
        self.tabs.addTab(self.list_external, "Externí")
        layout.addWidget(self.tabs)

        row = QHBoxLayout()
        btn_new = QPushButton("Nový…")
        btn_edit = QPushButton("Upravit…")
        btn_delete = QPushButton("Smazat")
        btn_close = QPushButton("Zavřít")
        btn_new.clicked.connect(self._new)
        btn_edit.clicked.connect(self._edit)
        btn_delete.clicked.connect(self._delete)
        btn_close.clicked.connect(self.accept)
        row.addWidget(btn_new)
        row.addWidget(btn_edit)
        row.addWidget(btn_delete)
        row.addStretch()
        row.addWidget(btn_close)
        layout.addLayout(row)

        self._refresh()

    def _build_list_tab(self, kind: OpponentKind) -> QListWidget:
        lw = QListWidget()
        lw.itemDoubleClicked.connect(self._edit)
        lw.setProperty("opponent_kind", kind.value)
        return lw

    def _current_list(self) -> QListWidget:
        return self.tabs.currentWidget()  # type: ignore[return-value]

    def _current_kind(self) -> OpponentKind:
        return OpponentKind(self._current_list().property("opponent_kind"))

    def _refresh(self) -> None:
        for lw, kind in (
            (self.list_internal, OpponentKind.INTERNAL),
            (self.list_external, OpponentKind.EXTERNAL),
        ):
            lw.clear()
            for o in self.service.list_opponents(kind=kind):
                parts = [o.name]
                if o.affiliation:
                    parts.append(f"({o.affiliation})")
                if o.email:
                    parts.append(f"✉ {o.email}")
                if o.phone and kind == OpponentKind.EXTERNAL:
                    parts.append(f"☎ {o.phone}")
                item = QListWidgetItem(" ".join(parts))
                item.setData(Qt.ItemDataRole.UserRole, o)
                lw.addItem(item)

    def _current_opp(self) -> Opponent | None:
        lw = self._current_list()
        item = lw.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _new(self) -> None:
        dlg = OpponentDialog(self.service, default_kind=self._current_kind(), parent=self)
        if dlg.exec():
            self._refresh()

    def _edit(self) -> None:
        o = self._current_opp()
        if o is None:
            return
        dlg = OpponentDialog(self.service, o, parent=self)
        if dlg.exec():
            self._refresh()

    def _delete(self) -> None:
        o = self._current_opp()
        if o is None:
            return
        confirm = QMessageBox.question(
            self,
            "Smazat oponenta",
            f"Opravdu smazat „{o.name}“? Práce, které ho mají přiřazeného, zůstanou (bez oponenta).",
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.service.delete_opponent(o.id)
            self._refresh()


class OboryManageDialog(QDialog):
    """Správa číselníku studijních oborů."""

    def __init__(self, service: ThesisService, parent=None) -> None:
        super().__init__(parent)
        self.service = service
        self.setWindowTitle("Studijní obory")
        self.setMinimumSize(480, 480)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Seznam studijních oborů (např. NSWI-P, NKYB-K)"))

        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self._rename)
        layout.addWidget(self.list_widget)

        self.lbl_info = QLabel("")
        self.lbl_info.setStyleSheet("color: #888;")
        layout.addWidget(self.lbl_info)

        row = QHBoxLayout()
        btn_new = QPushButton("+ Přidat…")
        btn_rename = QPushButton("Přejmenovat…")
        btn_delete = QPushButton("Smazat")
        btn_close = QPushButton("Zavřít")
        btn_new.clicked.connect(self._new)
        btn_rename.clicked.connect(self._rename)
        btn_delete.clicked.connect(self._delete)
        btn_close.clicked.connect(self.accept)
        row.addWidget(btn_new)
        row.addWidget(btn_rename)
        row.addWidget(btn_delete)
        row.addStretch()
        row.addWidget(btn_close)
        layout.addLayout(row)

        self.list_widget.currentRowChanged.connect(self._update_info)
        self._refresh()

    def _refresh(self) -> None:
        self.list_widget.clear()
        for name in self.service.list_obory():
            count = self.service.obor_usage_count(name)
            label = f"{name}    (studentů: {count})"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, name)
            self.list_widget.addItem(item)
        self._update_info(self.list_widget.currentRow())

    def _current(self) -> str | None:
        item = self.list_widget.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _update_info(self, _row: int) -> None:
        name = self._current()
        if not name:
            self.lbl_info.setText("")
            return
        count = self.service.obor_usage_count(name)
        if count == 0:
            self.lbl_info.setText(f"Obor „{name}“ není přiřazen žádnému studentovi.")
        else:
            self.lbl_info.setText(f"Obor „{name}“ je přiřazen u {count} studentů.")

    def _new(self) -> None:
        text, ok = QInputDialog.getText(self, "Nový obor", "Zkratka oboru (např. NSWI-P):")
        if ok and text.strip():
            self.service.add_obor(text.strip())
            self._refresh()

    def _rename(self) -> None:
        current = self._current()
        if current is None:
            return
        text, ok = QInputDialog.getText(
            self,
            "Přejmenovat obor",
            f"Nový název pro „{current}“:",
            text=current,
        )
        if not ok or not text.strip() or text.strip() == current:
            return
        count = self.service.rename_obor(current, text.strip())
        QMessageBox.information(
            self,
            "Hotovo",
            f"Obor přejmenován. Aktualizováno studentů: {count}.",
        )
        self._refresh()

    def _delete(self) -> None:
        current = self._current()
        if current is None:
            return
        count = self.service.obor_usage_count(current)
        msg = f"Opravdu smazat obor „{current}“?"
        if count:
            msg += f"\n\nU {count} studentů bude pole „obor“ vyprázdněno."
        confirm = QMessageBox.question(self, "Smazat obor", msg)
        if confirm == QMessageBox.StandardButton.Yes:
            self.service.remove_obor(current)
            self._refresh()
