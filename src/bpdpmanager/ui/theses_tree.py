"""Stromový pohled na práce s grupováním (rok → BP/DP) a sloupci tabulky."""

from __future__ import annotations

import locale
import unicodedata

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QAction, QBrush, QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QMenu,
    QTreeWidget,
    QTreeWidgetItem,
)

from ..models import Thesis
from ..models.enums import (
    REVIEW_STATE_LABELS,
    REVIEW_STATE_TINTS,
    AttachmentKind,
    ThesisStatus,
    ThesisType,
    review_sent_indicator,
)
from ..services import ThesisService

ROLE_THESIS_ID = Qt.ItemDataRole.UserRole + 1
ROLE_KIND = Qt.ItemDataRole.UserRole + 2  # "year" | "type" | "thesis"

# ── České abecední řazení ────────────────────────────────────────────────────
_HAS_CZECH_LOCALE = False
for _loc in ("cs_CZ.UTF-8", "cs_CZ.utf8", "cs_CZ", "Czech_Czech Republic.1250"):
    try:
        locale.setlocale(locale.LC_COLLATE, _loc)
        _HAS_CZECH_LOCALE = True
        break
    except locale.Error:
        continue


def _ascii_fold(s: str) -> str:
    """NFD-rozložení a vyhození diakritiky — fallback pro chybějící cs locale."""
    nfd = unicodedata.normalize("NFD", s)
    return "".join(c for c in nfd if not unicodedata.combining(c)).casefold()


def _czech_key(s: str) -> str:
    """Klíč pro abecední řazení češtiny (s diakritikou).

    Pokud je v systému locale ``cs_CZ.UTF-8``, použije ``locale.strxfrm``
    (správně řadí: c < č, h < ch < i, ť, ř atd.). Jinak ASCII fold —
    diakritika se ignoruje, ale alespoň case-insensitive.
    """
    if not s:
        return ""
    if _HAS_CZECH_LOCALE:
        return locale.strxfrm(s.casefold())
    return _ascii_fold(s)


def _thesis_sort_key(
    thesis: Thesis, service: ThesisService
) -> tuple[int, str, str]:
    """Klíč pro řazení prací uvnitř (rok, BP/DP) skupiny.

    Pořadí: práce se studentem podle příjmení (česky), pak křestního jména.
    Práce bez studenta jdou na konec.
    """
    student = service.get_student(thesis.student_id) if thesis.student_id else None
    if student is None:
        return (1, "", "")
    return (0, _czech_key(student.last_name), _czech_key(student.first_name))


class ThesesTreeWidget(QTreeWidget):
    """Strom prací: Akademický rok → BP/DP → jednotlivé práce.

    Sloupce u prací: Student | Téma | Stav | Oponent | Obor.
    Stav má barevné pozadí podle ``ThesisStatus.color``.
    Sekční řádky (rok, typ) overspan přes celou šířku.
    """

    thesis_selected = Signal(str)
    # Vyžádané smazání práce přes kontextové menu — connect z _ThesesTab
    rollback_requested = Signal(str)
    # Vyžádané generování posudku z šablony — connect z _ThesesTab
    generate_review_requested = Signal(str)
    # Vyžádaný export práce do ZIP — connect z _ThesesTab
    export_thesis_requested = Signal(str)
    # Ruční přepnutí příznaku odeslání posudku sekretářce (thesis_id, sent)
    mark_review_sent_requested = Signal(str, bool)

    HEADERS = ["Student / Skupina", "Téma", "Stav", "Posudky", "Odesláno", "Oponent", "Obor"]
    COL_STUDENT = 0
    COL_TITLE = 1
    COL_STATUS = 2
    COL_REVIEWS = 3
    COL_SENT = 4
    COL_OPPONENT = 5
    COL_OBOR = 6

    def __init__(self, service: ThesisService, parent=None) -> None:
        super().__init__(parent)
        self.service = service
        self._filter_predicate = lambda t: True

        self.setColumnCount(len(self.HEADERS))
        self.setHeaderLabels(self.HEADERS)
        self.setRootIsDecorated(True)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSortingEnabled(False)

        h = self.header()
        h.setSectionResizeMode(self.COL_STUDENT, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(self.COL_TITLE, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(self.COL_STATUS, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(self.COL_REVIEWS, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(self.COL_SENT, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(self.COL_OPPONENT, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(self.COL_OBOR, QHeaderView.ResizeMode.ResizeToContents)
        h.setStretchLastSection(False)

        self.itemSelectionChanged.connect(self._on_selection)

        # Kontextové menu (pravý klik na práci → Roll-back)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._on_context_menu)

    # --- veřejné API ---------------------------------------------------------

    def set_filter(self, predicate) -> None:
        self._filter_predicate = predicate
        self.refresh()

    def refresh(self) -> None:
        selected_id = self.selected_thesis_id()
        # zapamatuj si rozbalené roky (po refresh chceme zachovat stav)
        expanded_years = self._snapshot_expanded()

        # Blokuj VŠECHNY signály po celou dobu rebuild + re-select. Jinak by
        # clear() / addTopLevelItem / setCurrentItem mohly emitovat
        # itemSelectionChanged a vyvolat set_thesis na detailu (→ skok kurzoru
        # i přepnutí tabu zpět na Souhrn během psaní).
        self.blockSignals(True)
        try:
            self.clear()

            groups: dict[str, dict[str, list[Thesis]]] = {}
            for thesis in self.service.list_theses():
                if not self._filter_predicate(thesis):
                    continue
                year = thesis.academic_year or "(bez roku)"
                groups.setdefault(year, {"BP": [], "DP": []})
                groups[year][thesis.type.value].append(thesis)

            for year in sorted(groups.keys(), reverse=True):
                total = sum(len(v) for v in groups[year].values())
                year_item = QTreeWidgetItem(
                    [f"📅 {year}    ({total})", "", "", "", ""]
                )
                year_item.setData(0, ROLE_KIND, "year")
                year_item.setData(0, Qt.ItemDataRole.UserRole + 3, year)
                font = year_item.font(0)
                font.setBold(True)
                font.setPointSize(font.pointSize() + 1)
                year_item.setFont(0, font)
                year_item.setFirstColumnSpanned(True)
                self.addTopLevelItem(year_item)

                for type_code in ("BP", "DP"):
                    theses = groups[year][type_code]
                    if not theses:
                        continue
                    # Řazení uvnitř skupiny: česky abecedně podle příjmení
                    # (sekundárně podle jména); bez studenta na konci.
                    theses.sort(key=lambda t: _thesis_sort_key(t, self.service))

                    type_label = ThesisType(type_code).label
                    type_item = QTreeWidgetItem(
                        [f"  {type_label}  ({len(theses)})", "", "", "", ""]
                    )
                    type_item.setData(0, ROLE_KIND, "type")
                    type_font = type_item.font(0)
                    type_font.setItalic(True)
                    type_item.setFont(0, type_font)
                    type_item.setFirstColumnSpanned(True)
                    year_item.addChild(type_item)

                    for thesis in theses:
                        self._add_thesis_row(type_item, thesis)

                    type_item.setExpanded(True)

                year_item.setExpanded(expanded_years.get(year, True))

            if selected_id:
                self.select_thesis(selected_id)
        finally:
            self.blockSignals(False)

    def select_thesis(self, thesis_id: str) -> bool:
        for i in range(self.topLevelItemCount()):
            year_item = self.topLevelItem(i)
            for j in range(year_item.childCount()):
                type_item = year_item.child(j)
                for k in range(type_item.childCount()):
                    leaf = type_item.child(k)
                    if leaf.data(0, ROLE_THESIS_ID) == thesis_id:
                        self.setCurrentItem(leaf)
                        self.scrollToItem(
                            leaf, QAbstractItemView.ScrollHint.PositionAtCenter
                        )
                        return True
        return False

    def selected_thesis_id(self) -> str | None:
        item = self.currentItem()
        if item is None:
            return None
        return item.data(0, ROLE_THESIS_ID)

    # --- privátní ------------------------------------------------------------

    def _snapshot_expanded(self) -> dict[str, bool]:
        out: dict[str, bool] = {}
        for i in range(self.topLevelItemCount()):
            year_item = self.topLevelItem(i)
            year_key = year_item.data(0, Qt.ItemDataRole.UserRole + 3)
            if year_key:
                out[year_key] = year_item.isExpanded()
        return out

    def _add_thesis_row(self, parent: QTreeWidgetItem, thesis: Thesis) -> None:
        student = self.service.get_student(thesis.student_id) if thesis.student_id else None
        opponent = self.service.get_opponent(thesis.opponent_id) if thesis.opponent_id else None

        student_name = student.full_name if student else "—"
        title = thesis.display_title
        # Stav posudku vedoucího jako barevný puntík v názvu — viditelný i když
        # je řádek vybraný (na rozdíl od pozadí buňky, které výběr překryje).
        if thesis.status == ThesisStatus.IN_PROGRESS:
            dot = {"done": "🟢", "draft": "🟡", "none": "🔴"}.get(
                thesis.supervisor_review_state, ""
            )
            if dot:
                title = f"{dot} {title}"
        opponent_name = opponent.display_name if opponent else "—"
        obor = student.obor if student and student.obor else "—"

        # Posudky — máme nahrány?
        # Stačí *jakákoli* příloha daného kind (i ne-current), uživatel obvykle
        # zajímá, jestli existuje. Stejné kritérium používá Souhrn pro shrnutí.
        has_supervisor_review = any(
            a.kind == AttachmentKind.SUPERVISOR_REVIEW for a in thesis.attachments
        )
        has_opponent_review = any(
            a.kind == AttachmentKind.OPPONENT_REVIEW for a in thesis.attachments
        )
        if has_supervisor_review and has_opponent_review:
            reviews_text = "📘 V · 📕 O"
        elif has_supervisor_review:
            reviews_text = "📘 V"
        elif has_opponent_review:
            reviews_text = "📕 O"
        else:
            reviews_text = "—"
        # Odeslání posudku vedoucího sekretářce — vlastní sloupec „Odesláno"
        # (jednotná indikace jako u oponentur). Jen u prací „V řešení"
        # s hotovým posudkem.
        sent_at = thesis.supervisor_review_sent_at
        review_ready = thesis.supervisor_review_state == "done"
        sent_prepared = thesis.status == ThesisStatus.IN_PROGRESS and review_ready
        sent_text, sent_tip = review_sent_indicator(sent_prepared, sent_at)

        leaf = QTreeWidgetItem(
            [
                student_name,
                title,
                f"  {thesis.status.label}  ",
                reviews_text,
                sent_text,
                opponent_name,
                obor,
            ]
        )
        leaf.setTextAlignment(
            self.COL_SENT, Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
        )
        if sent_tip:
            leaf.setToolTip(self.COL_SENT, sent_tip)

        # Tooltip vysvětlující ikony
        if has_supervisor_review or has_opponent_review:
            parts = []
            if has_supervisor_review:
                n = sum(
                    1 for a in thesis.attachments
                    if a.kind == AttachmentKind.SUPERVISOR_REVIEW
                )
                parts.append(f"📘 Posudek vedoucího ({n}×)")
            if has_opponent_review:
                n = sum(
                    1 for a in thesis.attachments
                    if a.kind == AttachmentKind.OPPONENT_REVIEW
                )
                parts.append(f"📕 Posudek oponenta ({n}×)")
            leaf.setToolTip(self.COL_REVIEWS, "\n".join(parts))
        else:
            leaf.setToolTip(self.COL_REVIEWS, "Žádný posudek zatím nahrán")
        leaf.setTextAlignment(
            self.COL_REVIEWS, Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
        )
        leaf.setData(0, ROLE_KIND, "thesis")
        leaf.setData(0, ROLE_THESIS_ID, thesis.id)

        # Barevný stav: pozadí + bílý bold text, centrováno
        status_color = QColor(thesis.status.color)
        leaf.setBackground(self.COL_STATUS, QBrush(status_color))
        leaf.setForeground(self.COL_STATUS, QBrush(QColor("white")))
        font = leaf.font(self.COL_STATUS)
        font.setBold(True)
        leaf.setFont(self.COL_STATUS, font)
        leaf.setTextAlignment(
            self.COL_STATUS, Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
        )

        # Posudek vedoucího — podbarvi buňku NÁZVU práce (jen u prací „V řešení",
        # kde má smysl sledovat, co ještě jako vedoucí musím posoudit):
        #   🟢 hotový soubor · 🟡 jen rozpracovaná data · 🔴 nic
        if thesis.status == ThesisStatus.IN_PROGRESS:
            state = thesis.supervisor_review_state
            tint = REVIEW_STATE_TINTS.get(state)
            if tint:
                leaf.setBackground(self.COL_TITLE, QBrush(QColor(tint)))
                leaf.setForeground(self.COL_TITLE, QBrush(QColor("#212121")))
                leaf.setToolTip(
                    self.COL_TITLE,
                    f"Posudek vedoucího: {REVIEW_STATE_LABELS.get(state, '')}",
                )

        # Tooltipy
        if student:
            tip = student.full_name
            if student.university_id:
                tip += f"\nOs. č.: {student.university_id}"
            if student.form:
                tip += f"\nForma: {student.form.label}"
            leaf.setToolTip(self.COL_STUDENT, tip)
        else:
            leaf.setToolTip(self.COL_STUDENT, "(bez studenta)")

        leaf.setToolTip(self.COL_TITLE, title)

        if opponent:
            tip = opponent.name
            if opponent.affiliation:
                tip += f"\n{opponent.affiliation}"
            tip += f"\n({opponent.kind.label})"
            leaf.setToolTip(self.COL_OPPONENT, tip)

        parent.addChild(leaf)

    def _on_selection(self) -> None:
        tid = self.selected_thesis_id()
        if tid:
            self.thesis_selected.emit(tid)

    def _on_context_menu(self, pos: QPoint) -> None:
        """Kontextové menu nad práci — Roll-back / kompletní smazání.

        Sekční řádky (rok, typ) menu nemají — jen list reprezentující práci.
        """
        item = self.itemAt(pos)
        if item is None:
            return
        kind = item.data(0, ROLE_KIND)
        if kind != "thesis":
            return
        thesis_id = item.data(0, ROLE_THESIS_ID)
        if not thesis_id:
            return

        menu = QMenu(self)

        act_generate = QAction("📝 Generovat posudek z šablony…", self)
        act_generate.setToolTip(
            "Vybere se šablona z knihovny, vyplní se daty z této práce "
            "a připojí se jako příloha."
        )
        act_generate.triggered.connect(
            lambda _checked=False, tid=thesis_id: self.generate_review_requested.emit(tid)
        )
        menu.addAction(act_generate)

        # Označení posudku za odeslaný — jen u prací „V řešení" s hotovým posudkem.
        thesis = self.service.get_thesis(thesis_id)
        if (
            thesis is not None
            and thesis.status == ThesisStatus.IN_PROGRESS
            and thesis.supervisor_review_state == "done"
        ):
            if thesis.supervisor_review_sent_at:
                act_unsent = QAction("✉ Zrušit označení odeslání posudku", self)
                act_unsent.triggered.connect(
                    lambda _c=False, tid=thesis_id:
                    self.mark_review_sent_requested.emit(tid, False)
                )
                menu.addAction(act_unsent)
            else:
                act_sent = QAction("✉ Označit posudek za odeslaný sekretářce", self)
                act_sent.triggered.connect(
                    lambda _c=False, tid=thesis_id:
                    self.mark_review_sent_requested.emit(tid, True)
                )
                menu.addAction(act_sent)
            menu.addSeparator()

        act_export = QAction("📦 Exportovat práci do ZIP…", self)
        act_export.setToolTip(
            "Uloží kompletní balík práce (data, stav, posudky, soubory) do ZIPu "
            "— lze importovat na jiném zařízení / v jiném profilu."
        )
        act_export.triggered.connect(
            lambda _checked=False, tid=thesis_id: self.export_thesis_requested.emit(tid)
        )
        menu.addAction(act_export)

        menu.addSeparator()

        act_rollback = QAction("🗑 Roll-back — smazat kompletně…", self)
        act_rollback.setToolTip(
            "Nenávratně smaže záznam práce z databáze a všechny její soubory. "
            "Vhodné po chybném importu nebo omylu při zakládání."
        )
        act_rollback.triggered.connect(
            lambda _checked=False, tid=thesis_id: self.rollback_requested.emit(tid)
        )
        menu.addAction(act_rollback)

        menu.exec(self.viewport().mapToGlobal(pos))
