"""Stromový pohled na práce s grupováním (rok → BP/DP) a sloupci tabulky."""

from __future__ import annotations

import locale
import unicodedata

from PySide6.QtCore import QPoint, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QAction, QBrush, QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QMenu,
    QStyle,
    QStyledItemDelegate,
    QTreeWidget,
    QTreeWidgetItem,
)

from ..models import Thesis
from ..models.enums import (
    GRADE_TINTS,
    REVIEW_STATE_LABELS,
    REVIEW_STATE_TINTS,
    AttachmentKind,
    ThesisStatus,
    ThesisType,
    review_sent_badge,
)
from ..services import ThesisService
from ._os_actions import open_path

ROLE_THESIS_ID = Qt.ItemDataRole.UserRole + 1
ROLE_KIND = Qt.ItemDataRole.UserRole + 2  # "year" | "type" | "thesis"
ROLE_GRADES = Qt.ItemDataRole.UserRole + 4  # (grade_supervisor, grade_opponent)
ROLE_REVIEWS = Qt.ItemDataRole.UserRole + 5  # (has_supervisor_review, has_opponent_review)
ROLE_SENT = Qt.ItemDataRole.UserRole + 6     # barva pozadí badge „Odesláno" (nebo None)
ROLE_OBOR = Qt.ItemDataRole.UserRole + 7     # název oboru (pro barevný badge) nebo None
ROLE_STATUS = Qt.ItemDataRole.UserRole + 8   # (label, barva) stavu pro zaoblený badge


def _contrast_text(bg_hex: str) -> str:
    """Vrátí „white"/„black" podle jasu pozadí (čitelný text na badge)."""
    c = QColor(bg_hex)
    lum = 0.299 * c.red() + 0.587 * c.green() + 0.114 * c.blue()
    return "#212121" if lum > 150 else "white"

# Barvy oborů — světlé odstíny (tmavý text čitelný v light i dark theme).
_OBOR_COLORS = {
    "BTSM": "#a5d6a7",   # zelená
    "SWI": "#90caf9",    # modrá
    "NSWI": "#80deea",   # tyrkysová
    "NKYB": "#b39ddb",   # fialová
    "ITA": "#ffcc80",    # oranžová
    "NUI": "#f48fb1",    # růžová
    "IRT": "#fff176",    # žlutá
}
_OBOR_FALLBACK = [
    "#bcaaa4", "#80cbc4", "#c5e1a5", "#9fa8da",
    "#ce93d8", "#ffab91", "#e6ee9c", "#b0bec5",
]


def _obor_program_key(name: str) -> str:
    """Z názvu oboru (např. „NSWI-P-EN") odvodí program (bez formy P/K a EN)."""
    toks = [t for t in name.split("-") if t and t.upper() != "EN"]
    if toks and toks[-1].upper() in ("P", "K"):
        toks = toks[:-1]
    return "-".join(toks).upper()


def obor_badge(name: str) -> tuple[str | None, str | None, bool]:
    """Vrátí ``(popisek, barva, je_anglicky)`` pro barevný badge oboru.

    ``popisek`` je název bez „-EN" (angličtinu indikuje vlaječka). Když není
    obor (prázdné / „—"), vrátí ``(None, None, False)``.
    """
    name = (name or "").strip()
    if not name or name == "—":
        return None, None, False
    is_en = any(t.upper() == "EN" for t in name.split("-"))
    label = "-".join(t for t in name.split("-") if t.upper() != "EN")
    key = _obor_program_key(name)
    color = _OBOR_COLORS.get(key)
    if color is None:
        color = _OBOR_FALLBACK[sum(ord(c) for c in key) % len(_OBOR_FALLBACK)]
    return label, color, is_en

# Sloupec „Posudky": V (vedoucí) / O (oponent) — zelená = k dispozici, červená ne.
_REVIEW_HAS_BG = "#43a047"   # zelená — posudek je
_REVIEW_NONE_BG = "#e53935"  # červená — chybí


def _grade_badges(gs: str, go: str) -> list[str]:
    """Dvojice popisků pro sloupec V/O — prázdná známka jako „–"."""
    return [(gs or "").upper().strip() or "–", (go or "").upper().strip() or "–"]


class GradesDelegate(QStyledItemDelegate):
    """Vykreslí sloupec „V/O" jako dvě barevně podbarvená písmena (V / O).

    Levé písmeno = známka vedoucího, pravé = oponenta; barva dle ECTS stupně
    (zelená A → červená F/FX). Prázdná známka je decentní „–" bez podbarvení.
    """

    _GAP = 8        # mezera mezi dvojicí
    _PAD = 7        # vnitřní okraj v rámečku písmene
    _MIN_W = 22     # minimální šířka rámečku
    _BADGE_H = 18

    def _layout(self, fm, gs: str, go: str) -> tuple[list[str], list[int], int]:
        labels = _grade_badges(gs, go)
        widths = [max(self._MIN_W, fm.horizontalAdvance(lbl) + 2 * self._PAD)
                  for lbl in labels]
        total = sum(widths) + self._GAP
        return labels, widths, total

    def paint(self, painter, option, index) -> None:
        pair = index.data(ROLE_GRADES)
        if not pair:
            super().paint(painter, option, index)
            return
        gs, go = pair
        painter.save()
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
        fm = option.fontMetrics
        labels, widths, total = self._layout(fm, gs, go)
        rect = option.rect
        x = rect.x() + max(0, (rect.width() - total) // 2)
        y = rect.y() + (rect.height() - self._BADGE_H) // 2
        font = painter.font()
        font.setBold(True)
        painter.setFont(font)
        for lbl, w in zip(labels, widths, strict=True):
            br = QRectF(x, y, w, self._BADGE_H)
            if lbl != "–":
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(GRADE_TINTS.get(lbl, "#e0e0e0")))
                painter.drawRoundedRect(br, 4, 4)
                painter.setPen(QColor("#212121"))
            else:
                painter.setPen(QColor("#9e9e9e"))
            painter.drawText(br, Qt.AlignmentFlag.AlignCenter, lbl)
            x += w + self._GAP
        painter.restore()

    def sizeHint(self, option, index) -> QSize:  # noqa: N802 (Qt API)
        pair = index.data(ROLE_GRADES)
        if not pair:
            return super().sizeHint(option, index)
        gs, go = pair
        _, _, total = self._layout(option.fontMetrics, gs, go)
        base = super().sizeHint(option, index)
        return QSize(total + 8, max(base.height(), self._BADGE_H + 6))


class ReviewsBadgeDelegate(QStyledItemDelegate):
    """Sloupec „Posudky": V (vedoucí) / O (oponent) jako barevná písmena —
    zelené pozadí = posudek k dispozici, červené = chybí."""

    _GAP = 8
    _PAD = 7
    _MIN_W = 22
    _BADGE_H = 18

    def _total(self, fm) -> int:
        w = max(self._MIN_W, fm.horizontalAdvance("V") + 2 * self._PAD)
        return 2 * w + self._GAP

    def paint(self, painter, option, index) -> None:
        pair = index.data(ROLE_REVIEWS)
        if pair is None:
            super().paint(painter, option, index)
            return
        has_v, has_o = pair
        painter.save()
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
        fm = option.fontMetrics
        w = max(self._MIN_W, fm.horizontalAdvance("V") + 2 * self._PAD)
        total = 2 * w + self._GAP
        rect = option.rect
        x = rect.x() + max(0, (rect.width() - total) // 2)
        y = rect.y() + (rect.height() - self._BADGE_H) // 2
        font = painter.font()
        font.setBold(True)
        painter.setFont(font)
        for letter, has in (("V", has_v), ("O", has_o)):
            br = QRectF(x, y, w, self._BADGE_H)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(_REVIEW_HAS_BG if has else _REVIEW_NONE_BG))
            painter.drawRoundedRect(br, 4, 4)
            painter.setPen(QColor("white"))
            painter.drawText(br, Qt.AlignmentFlag.AlignCenter, letter)
            x += w + self._GAP
        painter.restore()

    def sizeHint(self, option, index) -> QSize:  # noqa: N802 (Qt API)
        if index.data(ROLE_REVIEWS) is None:
            return super().sizeHint(option, index)
        base = super().sizeHint(option, index)
        return QSize(self._total(option.fontMetrics) + 8,
                     max(base.height(), self._BADGE_H + 6))


class SentBadgeDelegate(QStyledItemDelegate):
    """Sloupec „Odesláno": obálka ✉ v zaobleném barevném čtverečku
    (zelená = odesláno / červená = neodesláno), stejný styl jako známky."""

    _BADGE_H = 18
    _W = 22

    def paint(self, painter, option, index) -> None:
        bg = index.data(ROLE_SENT)
        if not bg:
            super().paint(painter, option, index)
            return
        painter.save()
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
        rect = option.rect
        x = rect.x() + max(0, (rect.width() - self._W) // 2)
        y = rect.y() + (rect.height() - self._BADGE_H) // 2
        br = QRectF(x, y, self._W, self._BADGE_H)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(bg))
        painter.drawRoundedRect(br, 4, 4)
        painter.setPen(QColor("white"))
        painter.drawText(br, Qt.AlignmentFlag.AlignCenter, "✉")
        painter.restore()

    def sizeHint(self, option, index) -> QSize:  # noqa: N802 (Qt API)
        base = super().sizeHint(option, index)
        return QSize(self._W + 10, max(base.height(), self._BADGE_H + 6))


class OborBadgeDelegate(QStyledItemDelegate):
    """Sloupec „Obor": název v zaobleném barevném badge (barva dle programu)
    + 🇬🇧 vlaječka u anglických variant (-EN)."""

    _PAD = 7
    _BADGE_H = 18
    _FLAG = "🇬🇧"

    def paint(self, painter, option, index) -> None:
        name = index.data(ROLE_OBOR)
        label, color, is_en = obor_badge(name) if name else (None, None, False)
        if not label:
            super().paint(painter, option, index)
            return
        painter.save()
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
        fm = option.fontMetrics
        bw = fm.horizontalAdvance(label) + 2 * self._PAD
        flag_w = (fm.horizontalAdvance(self._FLAG) + 6) if is_en else 0
        total = bw + flag_w
        rect = option.rect
        x = rect.x() + max(2, (rect.width() - total) // 2)
        y = rect.y() + (rect.height() - self._BADGE_H) // 2
        br = QRectF(x, y, bw, self._BADGE_H)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(color))
        painter.drawRoundedRect(br, 4, 4)
        painter.setPen(QColor("#212121"))
        painter.drawText(br, Qt.AlignmentFlag.AlignCenter, label)
        if is_en:
            painter.setPen(QColor("#212121"))
            painter.drawText(
                QRectF(x + bw + 6, y, flag_w, self._BADGE_H),
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                self._FLAG,
            )
        painter.restore()

    def sizeHint(self, option, index) -> QSize:  # noqa: N802 (Qt API)
        name = index.data(ROLE_OBOR)
        label, _, is_en = obor_badge(name) if name else (None, None, False)
        if not label:
            return super().sizeHint(option, index)
        fm = option.fontMetrics
        w = fm.horizontalAdvance(label) + 2 * self._PAD
        if is_en:
            w += fm.horizontalAdvance(self._FLAG) + 10
        base = super().sizeHint(option, index)
        return QSize(w + 10, max(base.height(), self._BADGE_H + 6))


class StatusBadgeDelegate(QStyledItemDelegate):
    """Sloupec „Stav": label stavu v zaobleném barevném badge (jako známky),
    barva textu se volí podle jasu pozadí (čitelná na světlém i tmavém)."""

    _PAD = 9
    _BADGE_H = 18

    def paint(self, painter, option, index) -> None:
        data = index.data(ROLE_STATUS)
        if not data:
            super().paint(painter, option, index)
            return
        label, color = data
        painter.save()
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
        fm = option.fontMetrics
        bw = fm.horizontalAdvance(label) + 2 * self._PAD
        rect = option.rect
        x = rect.x() + max(2, (rect.width() - bw) // 2)
        y = rect.y() + (rect.height() - self._BADGE_H) // 2
        br = QRectF(x, y, bw, self._BADGE_H)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(color))
        painter.drawRoundedRect(br, 4, 4)
        f = painter.font()
        f.setBold(True)
        painter.setFont(f)
        painter.setPen(QColor(_contrast_text(color)))
        painter.drawText(br, Qt.AlignmentFlag.AlignCenter, label)
        painter.restore()

    def sizeHint(self, option, index) -> QSize:  # noqa: N802 (Qt API)
        data = index.data(ROLE_STATUS)
        if not data:
            return super().sizeHint(option, index)
        label, _ = data
        w = option.fontMetrics.horizontalAdvance(label) + 2 * self._PAD
        base = super().sizeHint(option, index)
        return QSize(w + 10, max(base.height(), self._BADGE_H + 6))

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

    HEADERS = [
        "Student / Skupina", "Téma", "Stav", "Známky V/O",
        "Posudky", "Odesláno", "Oponent", "Obor",
    ]
    COL_STUDENT = 0
    COL_TITLE = 1
    COL_STATUS = 2
    COL_GRADES = 3
    COL_REVIEWS = 4
    COL_SENT = 5
    COL_OPPONENT = 6
    COL_OBOR = 7

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
        h.setSectionResizeMode(self.COL_GRADES, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(self.COL_REVIEWS, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(self.COL_SENT, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(self.COL_OPPONENT, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(self.COL_OBOR, QHeaderView.ResizeMode.ResizeToContents)
        h.setStretchLastSection(False)

        # Sloupec V/O vykresluje barevné dvojice písmen (delegát).
        self._grades_delegate = GradesDelegate(self)
        self.setItemDelegateForColumn(self.COL_GRADES, self._grades_delegate)
        # Sloupec Posudky — V/O badge (zelená k dispozici / červená chybí).
        self._reviews_delegate = ReviewsBadgeDelegate(self)
        self.setItemDelegateForColumn(self.COL_REVIEWS, self._reviews_delegate)
        # Sloupec Odesláno — obálka v zaobleném barevném badge.
        self._sent_delegate = SentBadgeDelegate(self)
        self.setItemDelegateForColumn(self.COL_SENT, self._sent_delegate)
        # Sloupec Obor — barevný badge dle programu (+ 🇬🇧 u anglických).
        self._obor_delegate = OborBadgeDelegate(self)
        self.setItemDelegateForColumn(self.COL_OBOR, self._obor_delegate)
        # Sloupec Stav — zaoblený barevný badge s labelem stavu.
        self._status_delegate = StatusBadgeDelegate(self)
        self.setItemDelegateForColumn(self.COL_STATUS, self._status_delegate)

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
        # Repetent — vazba řádný ↔ opravný pokus.
        if thesis.related_thesis_id:
            title = f"🔁 {title}"
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
        # Posudky kreslí ReviewsBadgeDelegate z dat ROLE_REVIEWS; text prázdný.
        reviews_text = ""
        # Odeslání posudku vedoucího sekretářce — vlastní sloupec „Odesláno"
        # (jednotná indikace jako u oponentur). Jen u prací „V řešení"
        # s hotovým posudkem.
        sent_at = thesis.supervisor_review_sent_at
        review_ready = thesis.supervisor_review_state == "done"
        sent_prepared = thesis.status == ThesisStatus.IN_PROGRESS and review_ready
        _, sent_bg, sent_tip = review_sent_badge(sent_prepared, sent_at)

        # Známky vedoucí (V) / oponent (O) — kreslí je delegát (barevné dvojice
        # písmen). Když chybí obě, necháme decentní „—" jako prostý text.
        gs = (thesis.grade_supervisor or "").strip()
        go = (thesis.grade_opponent or "").strip()
        grades_text = "" if (gs or go) else "—"

        leaf = QTreeWidgetItem(
            [
                student_name,
                title,
                "",            # Stav — kreslí StatusBadgeDelegate
                grades_text,
                reviews_text,
                "",            # Odesláno — kreslí SentBadgeDelegate
                opponent_name,
                obor,
            ]
        )
        leaf.setData(
            self.COL_STATUS, ROLE_STATUS,
            (thesis.status.label, thesis.status.color),
        )
        leaf.setTextAlignment(
            self.COL_GRADES, Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
        )
        if gs or go:
            leaf.setData(self.COL_GRADES, ROLE_GRADES, (gs, go))
            leaf.setToolTip(
                self.COL_GRADES,
                f"Vedoucí: {gs or '—'}  ·  Oponent: {go or '—'}",
            )
        if sent_bg:
            leaf.setData(self.COL_SENT, ROLE_SENT, sent_bg)
        if sent_tip:
            leaf.setToolTip(self.COL_SENT, sent_tip)

        # Posudky V/O badge (zelená k dispozici / červená chybí) + tooltip.
        leaf.setData(
            self.COL_REVIEWS, ROLE_REVIEWS,
            (has_supervisor_review, has_opponent_review),
        )
        tip_v = "✓ k dispozici" if has_supervisor_review else "chybí"
        tip_o = "✓ k dispozici" if has_opponent_review else "chybí"
        leaf.setToolTip(
            self.COL_REVIEWS,
            f"V = posudek vedoucího: {tip_v}\nO = posudek oponenta: {tip_o}",
        )
        leaf.setTextAlignment(
            self.COL_REVIEWS, Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
        )
        leaf.setData(0, ROLE_KIND, "thesis")
        leaf.setData(0, ROLE_THESIS_ID, thesis.id)
        leaf.setData(self.COL_OBOR, ROLE_OBOR, obor if obor != "—" else None)
        if thesis.related_thesis_id:
            leaf.setToolTip(
                self.COL_TITLE,
                "🔁 Repetent — tato práce souvisí s druhým pokusem téhož "
                "studenta (řádný + opravný).",
            )

        # Stav kreslí StatusBadgeDelegate z dat ROLE_STATUS (zaoblený badge).

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
        thesis = self.service.get_thesis(thesis_id)
        if thesis is None:
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

        # Otevřít posudek OPONENTA, pokud je u vedené práce k dispozici.
        opp_att = next(
            (a for a in thesis.attachments
             if a.kind == AttachmentKind.OPPONENT_REVIEW and a.is_file and a.is_current),
            None,
        )
        opp_path = (
            self.service.document_absolute_path(thesis_id, opp_att)
            if opp_att is not None else None
        )
        act_open_opp = QAction("📕 Otevřít posudek oponenta", self)
        act_open_opp.setEnabled(opp_path is not None and opp_path.exists())
        if act_open_opp.isEnabled():
            act_open_opp.triggered.connect(
                lambda _c=False, p=opp_path: open_path(p)
            )
        menu.addAction(act_open_opp)

        # Otevřít TEXT práce (plný text), pokud je k dispozici.
        text_att = next(
            (a for a in thesis.attachments
             if a.kind == AttachmentKind.THESIS_TEXT and a.is_file and a.is_current),
            None,
        )
        text_path = (
            self.service.document_absolute_path(thesis_id, text_att)
            if text_att is not None else None
        )
        act_open_text = QAction("📄 Otevřít text práce", self)
        act_open_text.setEnabled(text_path is not None and text_path.exists())
        if act_open_text.isEnabled():
            act_open_text.triggered.connect(lambda _c=False, p=text_path: open_path(p))
        menu.addAction(act_open_text)

        # Označení posudku za odeslaný — jen u prací „V řešení" s hotovým posudkem.
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
