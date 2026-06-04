"""Dialogy pro správu seznamů (studenti, oponenti, obory)."""

from __future__ import annotations

import re

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

# Akademické tituly, které ignorujeme při řazení abecedně.
_TITLE_PREFIX_RE = re.compile(
    r"^(?:(?:doc\.|prof\.|MgA\.|MUDr\.|RNDr\.|JUDr\.|PhDr\.|PaedDr\.|"
    r"Bc\.|Mgr\.|Ing\.|DiS\.|Ph\.D\.|CSc\.|DSc\.|Th\.D\.)\s+)+",
    re.IGNORECASE,
)


def _opponent_sort_key(name: str | None) -> str:
    """Vrátí klíč pro abecední řazení oponenta — ignoruje akademické tituly."""
    if not name:
        return ""
    stripped = _TITLE_PREFIX_RE.sub("", name).strip()
    return stripped.lower()

from ..models import Obor, Opponent, Student, Supervisor, Thesis
from ..models.enums import OpponentKind, ThesisStatus, ThesisType
from ..services import ThesisService
from .obor_dialog import OborDialog
from .opponent_dialog import OpponentDialog
from .student_dialog import StudentDialog
from .supervisor_dialog import SupervisorDialog

# Stavy, ve kterých má student „aktivní" práci.
# (Aktuální + Budoucí buckety dohromady, viz ``models.enums``.)
_ACTIVE_STATES = {
    ThesisStatus.RESERVED,
    ThesisStatus.LISTED,
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
    """Správa oponentů — jeden strom s grupováním Interní / Externí.

    Sloupce: Jméno | Pracoviště | Email | Telefon. Uvnitř každé skupiny
    abecedně podle jména (s ignorováním akademických titulů typu
    ``doc.``, ``Ing.``, ``Mgr.``, …).
    """

    def __init__(self, service: ThesisService, parent=None) -> None:
        super().__init__(parent)
        self.service = service
        self.setWindowTitle("Oponenti")
        self.setMinimumSize(820, 560)

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "Seznam oponentů — Interní (UTB) a Externí. "
                "Dvojklik upraví detail."
            )
        )

        self.tree = QTreeWidget()
        self.tree.setColumnCount(4)
        self.tree.setHeaderLabels(["Jméno", "Pracoviště", "Email", "Telefon"])
        self.tree.setAlternatingRowColors(True)
        self.tree.setRootIsDecorated(True)
        self.tree.itemDoubleClicked.connect(self._edit)
        h = self.tree.header()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        h.setStretchLastSection(False)
        layout.addWidget(self.tree, stretch=1)

        self.lbl_info = QLabel("")
        self.lbl_info.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(self.lbl_info)

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

        self.tree.currentItemChanged.connect(lambda *_: self._update_info())
        self._refresh()

    # --- načítání + grupování ----------------------------------------------

    def _refresh(self) -> None:
        selected_id = self._selected_opponent_id()
        self.tree.clear()

        for kind, icon in (
            (OpponentKind.INTERNAL, "📍"),
            (OpponentKind.EXTERNAL, "🏢"),
        ):
            opps = sorted(
                self.service.list_opponents(kind=kind),
                key=lambda o: _opponent_sort_key(o.name),
            )
            group = QTreeWidgetItem(
                [f"{icon}  {kind.label}  ({len(opps)})", "", "", ""]
            )
            group.setFirstColumnSpanned(True)
            f = group.font(0)
            f.setBold(True)
            f.setPointSize(f.pointSize() + 1)
            group.setFont(0, f)
            self.tree.addTopLevelItem(group)

            for o in opps:
                phone = o.phone if (o.phone and kind == OpponentKind.EXTERNAL) else ""
                leaf = QTreeWidgetItem(
                    [
                        o.name,
                        o.affiliation or "",
                        o.email or "",
                        phone,
                    ]
                )
                leaf.setData(0, Qt.ItemDataRole.UserRole, o)
                # tooltip s adresou (jen externí)
                if kind == OpponentKind.EXTERNAL and o.address:
                    leaf.setToolTip(0, f"{o.name}\n{o.address}")
                group.addChild(leaf)

            group.setExpanded(True)

        total_int = len(self.service.list_opponents(kind=OpponentKind.INTERNAL))
        total_ext = len(self.service.list_opponents(kind=OpponentKind.EXTERNAL))
        self.lbl_info.setText(
            f"Interní: {total_int}    ·    Externí: {total_ext}    ·    "
            f"Celkem: {total_int + total_ext}"
        )

        if selected_id:
            self._select_opponent(selected_id)

    # --- helper akce -------------------------------------------------------

    def _current_opp(self) -> Opponent | None:
        item = self.tree.currentItem()
        if item is None:
            return None
        data = item.data(0, Qt.ItemDataRole.UserRole)
        return data if isinstance(data, Opponent) else None

    def _selected_opponent_id(self) -> str | None:
        o = self._current_opp()
        return o.id if o else None

    def _select_opponent(self, opp_id: str) -> bool:
        for i in range(self.tree.topLevelItemCount()):
            group = self.tree.topLevelItem(i)
            for j in range(group.childCount()):
                leaf = group.child(j)
                data = leaf.data(0, Qt.ItemDataRole.UserRole)
                if isinstance(data, Opponent) and data.id == opp_id:
                    self.tree.setCurrentItem(leaf)
                    return True
        return False

    def _current_kind_for_new(self) -> OpponentKind:
        """Pokud je vybraná položka uvnitř Externí skupiny, použij default Externí."""
        item = self.tree.currentItem()
        while item is not None and item.parent() is not None:
            item = item.parent()
        if item is None:
            return OpponentKind.INTERNAL
        idx = self.tree.indexOfTopLevelItem(item)
        return OpponentKind.INTERNAL if idx == 0 else OpponentKind.EXTERNAL

    def _update_info(self) -> None:
        # placeholder pro budoucí kontextové info (zatím prázdné)
        pass

    def _new(self) -> None:
        dlg = OpponentDialog(
            self.service,
            default_kind=self._current_kind_for_new(),
            parent=self,
        )
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
            f'Opravdu smazat „{o.name}"? Práce, které ho mají přiřazeného, '
            f"zůstanou (bez oponenta).",
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.service.delete_opponent(o.id)
            self._refresh()


class OboryManageDialog(QDialog):
    """Správa číselníku studijních oborů — agregováno podle sekretářky.

    Tree má dvě úrovně:
    - **parent** = skupina podle sekretářky (jméno + email + telefon).
      Obory bez sekretářky padají do skupiny „— bez sekretářky —" na konci.
    - **child** = jednotlivý obor (jméno, STAG zkratka, počet studentů).
    """

    def __init__(self, service: ThesisService, parent=None) -> None:
        super().__init__(parent)
        self.service = service
        self.setWindowTitle("Studijní obory")
        self.setMinimumSize(820, 540)

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "Seznam studijních oborů (např. NSWI-P, NKYB-K). U každého lze evidovat "
                "STAG zkratku pro import (např. <code>knIT-KYB</code>) a sekretářku oboru. "
                "Položky jsou agregovány podle sekretářky — dvojklik na obor upraví detail.",
                textFormat=Qt.TextFormat.RichText,
            )
        )

        self.tree = QTreeWidget()
        self.tree.setColumnCount(4)
        self.tree.setHeaderLabels(
            ["Obor / Sekretářka", "STAG zkratka", "Studentů", "Kontakt"]
        )
        self.tree.setRootIsDecorated(True)
        self.tree.setAlternatingRowColors(True)
        self.tree.setUniformRowHeights(False)
        self.tree.itemDoubleClicked.connect(self._edit)
        h = self.tree.header()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.tree, stretch=1)

        self.lbl_info = QLabel("")
        self.lbl_info.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(self.lbl_info)

        row = QHBoxLayout()
        btn_new = QPushButton("+ Přidat…")
        btn_edit = QPushButton("Upravit…")
        btn_delete = QPushButton("Smazat")
        btn_expand = QPushButton("↕ Sbalit / rozbalit vše")
        btn_close = QPushButton("Zavřít")
        btn_new.clicked.connect(self._new)
        btn_edit.clicked.connect(self._edit)
        btn_delete.clicked.connect(self._delete)
        btn_expand.clicked.connect(self._toggle_expand)
        btn_close.clicked.connect(self.accept)
        row.addWidget(btn_new)
        row.addWidget(btn_edit)
        row.addWidget(btn_delete)
        row.addWidget(btn_expand)
        row.addStretch()
        row.addWidget(btn_close)
        layout.addLayout(row)

        self.tree.currentItemChanged.connect(lambda *_: self._update_info())
        self._refresh()

    # --- načtení / akce -----------------------------------------------------

    @staticmethod
    def _secretary_group_key(obor: Obor) -> tuple[str, str, str]:
        """Klíč pro seskupení podle sekretářky (jméno + email + telefon).

        Prázdné/None hodnoty se normalizují na prázdný string, aby všechny
        obory „bez sekretářky" padly do jedné skupiny.
        """
        return (
            (obor.secretary_name or "").strip(),
            (obor.secretary_email or "").strip(),
            (obor.secretary_phone or "").strip(),
        )

    @staticmethod
    def _secretary_contact_label(name: str, email: str, phone: str) -> str:
        parts = []
        if email:
            parts.append(f"✉ {email}")
        if phone:
            parts.append(f"☎ {phone}")
        return "   ".join(parts)

    @staticmethod
    def _cs_plural(count: int, one: str, few: str, many: str) -> str:
        """Česká plurál: 1 → ``one``, 2-4 → ``few``, 0 nebo 5+ → ``many``."""
        if count == 1:
            return one
        if 2 <= count <= 4:
            return few
        return many

    def _refresh(self) -> None:
        selected_name = self._current_name()
        self.tree.clear()

        # 1) Seskup obory podle sekretářky
        groups: dict[tuple[str, str, str], list[Obor]] = {}
        for obor in self.service.list_obor_objects():
            key = self._secretary_group_key(obor)
            groups.setdefault(key, []).append(obor)

        # 2) Seřaď klíče: nejdřív skupiny s vyplněnou sekretářkou (abecedně
        #    podle jména), na konci skupina „bez sekretářky".
        def _group_sort_key(k: tuple[str, str, str]) -> tuple[int, str]:
            name = k[0]
            return (1, "") if not name else (0, name.lower())

        empty_indicator = ("", "", "")
        for key in sorted(groups.keys(), key=_group_sort_key):
            obory = sorted(groups[key], key=lambda o: o.name.lower())
            sec_name, sec_email, sec_phone = key
            total_count = sum(
                self.service.obor_usage_count(o.name) for o in obory
            )
            if key == empty_indicator:
                header_label = "— bez sekretářky —"
                contact_label = ""
            else:
                header_label = f"👤 {sec_name}"
                contact_label = self._secretary_contact_label(
                    sec_name, sec_email, sec_phone
                )
            count_label = (
                f"{len(obory)} {self._cs_plural(len(obory), 'obor', 'obory', 'oborů')} · "
                f"{total_count} "
                f"{self._cs_plural(total_count, 'student', 'studenti', 'studentů')}"
            )
            parent = QTreeWidgetItem(
                [header_label, "", count_label, contact_label or "—"]
            )
            # Vizuálně odliš parent — bold + světle šedé pozadí na 0. sloupci
            font = parent.font(0)
            font.setBold(True)
            for col in range(self.tree.columnCount()):
                parent.setFont(col, font)
            parent.setData(0, Qt.ItemDataRole.UserRole, ("__group__", key))
            self.tree.addTopLevelItem(parent)

            for obor in obory:
                count = self.service.obor_usage_count(obor.name)
                stag = obor.stag_code or "—"
                child = QTreeWidgetItem(
                    [obor.name, stag, str(count), ""]
                )
                child.setData(0, Qt.ItemDataRole.UserRole, obor)
                # STAG kód v monospace pro lepší čitelnost
                stag_font = child.font(1)
                stag_font.setFamily("Menlo, Monaco, Courier New, monospace")
                child.setFont(1, stag_font)
                parent.addChild(child)

            parent.setExpanded(True)

        if selected_name:
            self._select_by_name(selected_name)
        self._update_info()

    def _current_obor(self) -> Obor | None:
        item = self.tree.currentItem()
        if item is None:
            return None
        data = item.data(0, Qt.ItemDataRole.UserRole)
        return data if isinstance(data, Obor) else None

    def _current_name(self) -> str | None:
        obor = self._current_obor()
        return obor.name if obor else None

    def _select_by_name(self, name: str) -> None:
        for i in range(self.tree.topLevelItemCount()):
            parent = self.tree.topLevelItem(i)
            for j in range(parent.childCount()):
                child = parent.child(j)
                obor = child.data(0, Qt.ItemDataRole.UserRole)
                if isinstance(obor, Obor) and obor.name == name:
                    self.tree.setCurrentItem(child)
                    parent.setExpanded(True)
                    return

    def _update_info(self) -> None:
        obor = self._current_obor()
        if obor is None:
            self.lbl_info.setText("")
            return
        count = self.service.obor_usage_count(obor.name)
        parts = []
        if count == 0:
            parts.append(f"Obor „{obor.name}\" není přiřazen žádnému studentovi.")
        else:
            parts.append(f"Obor „{obor.name}\" je přiřazen u {count} studentů.")
        if obor.stag_code:
            parts.append(f"STAG: {obor.stag_code}")
        if obor.has_secretary:
            parts.append("Sekretářka evidovaná.")
        else:
            parts.append("Sekretářka neuvedena.")
        self.lbl_info.setText("   ·   ".join(parts))

    def _toggle_expand(self) -> None:
        """Sbal / rozbal všechny skupiny najednou."""
        # Pokud je aspoň jeden parent rozbalený, vše sbal; jinak vše rozbal.
        any_expanded = False
        for i in range(self.tree.topLevelItemCount()):
            if self.tree.topLevelItem(i).isExpanded():
                any_expanded = True
                break
        new_state = not any_expanded
        for i in range(self.tree.topLevelItemCount()):
            self.tree.topLevelItem(i).setExpanded(new_state)

    def _new(self) -> None:
        dlg = OborDialog(self.service, parent=self)
        if dlg.exec():
            self._refresh()

    def _edit(self) -> None:
        obor = self._current_obor()
        if obor is None:
            return
        dlg = OborDialog(self.service, obor, parent=self)
        if dlg.exec():
            self._refresh()

    def _delete(self) -> None:
        obor = self._current_obor()
        if obor is None:
            return
        count = self.service.obor_usage_count(obor.name)
        msg = f"Opravdu smazat obor „{obor.name}\"?"
        if count:
            msg += f"\n\nU {count} studentů bude pole „obor\" vyprázdněno."
        confirm = QMessageBox.question(self, "Smazat obor", msg)
        if confirm == QMessageBox.StandardButton.Yes:
            self.service.remove_obor(obor.name)
            self._refresh()


class SupervisorsManageDialog(QDialog):
    """Správa registru vedoucích (pro oponentské posudky).

    Sloupce: Jméno | Pracoviště | Email | Telefon. Řazeno česky podle
    příjmení (ignoruje akademické tituly).
    """

    def __init__(self, service: ThesisService, parent=None) -> None:
        super().__init__(parent)
        self.service = service
        self.setWindowTitle("Vedoucí (pro oponentské posudky)")
        self.setMinimumSize(820, 520)

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "Registr vedoucích cizích BP/DP. Používá se pro našeptávání "
                "při vyplňování oponentských posudků. Dvojklik upraví detail."
            )
        )

        self.tree = QTreeWidget()
        self.tree.setColumnCount(4)
        self.tree.setHeaderLabels(["Jméno", "Pracoviště", "Email", "Telefon"])
        self.tree.setAlternatingRowColors(True)
        self.tree.setRootIsDecorated(False)
        self.tree.itemDoubleClicked.connect(self._edit)
        h = self.tree.header()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        h.setStretchLastSection(False)
        layout.addWidget(self.tree, stretch=1)

        self.lbl_info = QLabel("")
        self.lbl_info.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(self.lbl_info)

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

    def _refresh(self) -> None:
        selected_id = self._selected_id()
        self.tree.clear()
        sups = sorted(
            self.service.list_supervisors(),
            key=lambda s: _opponent_sort_key(s.name),
        )
        for sup in sups:
            item = QTreeWidgetItem(
                [
                    sup.name,
                    sup.affiliation or "",
                    sup.email or "",
                    sup.phone or "",
                ]
            )
            item.setData(0, Qt.ItemDataRole.UserRole, sup)
            self.tree.addTopLevelItem(item)
        self.lbl_info.setText(f"Vedoucích celkem: {len(sups)}")
        if selected_id:
            self._select_id(selected_id)

    def _current(self) -> Supervisor | None:
        item = self.tree.currentItem()
        if item is None:
            return None
        data = item.data(0, Qt.ItemDataRole.UserRole)
        return data if isinstance(data, Supervisor) else None

    def _selected_id(self) -> str | None:
        s = self._current()
        return s.id if s else None

    def _select_id(self, sup_id: str) -> bool:
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if isinstance(data, Supervisor) and data.id == sup_id:
                self.tree.setCurrentItem(item)
                return True
        return False

    def _new(self) -> None:
        dlg = SupervisorDialog(self.service, parent=self)
        if dlg.exec():
            self._refresh()

    def _edit(self) -> None:
        s = self._current()
        if s is None:
            return
        dlg = SupervisorDialog(self.service, s, parent=self)
        if dlg.exec():
            self._refresh()

    def _delete(self) -> None:
        s = self._current()
        if s is None:
            return
        confirm = QMessageBox.question(
            self,
            "Smazat vedoucího",
            f'Opravdu smazat „{s.name}"? Oponentské posudky, které ho odkazují, '
            f"si jeho jméno + email zachovají (jsou kopií, ne FK).",
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.service.delete_supervisor(s.id)
            self._refresh()
